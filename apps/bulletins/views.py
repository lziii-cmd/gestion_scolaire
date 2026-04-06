from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import Bulletin, StatutBulletin
from .serializers import BulletinSerializer
from .tasks import generer_bulletins_classe, generer_pdf_bulletin
from apps.accounts.permissions import IsPrefetOrDirecteur, IsDirecteur


class BulletinListView(generics.ListAPIView):
    serializer_class = BulletinSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Bulletin.objects.select_related(
            'inscription__eleve', 'inscription__classe', 'periode'
        ).prefetch_related('lignes')

        inscription_id = self.request.query_params.get('inscription')
        classe_id = self.request.query_params.get('classe')
        periode_id = self.request.query_params.get('periode')
        statut = self.request.query_params.get('statut')

        if inscription_id:
            qs = qs.filter(inscription_id=inscription_id)
        if classe_id:
            qs = qs.filter(inscription__classe_id=classe_id)
        if periode_id:
            qs = qs.filter(periode_id=periode_id)
        if statut:
            qs = qs.filter(statut=statut)

        # Élèves/Parents : bulletins publiés et non bloqués uniquement
        user = self.request.user
        roles = list(user.roles.filter(is_active=True).values_list('role', flat=True))
        if set(roles) & {'ELEVE', 'PARENT'}:
            qs = qs.filter(statut=StatutBulletin.PUBLIE, bloque=False)

        return qs


class BulletinDetailView(generics.RetrieveAPIView):
    serializer_class = BulletinSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Bulletin.objects.prefetch_related('lignes__matiere_classe__matiere')


class GenererBulletinsClasseView(APIView):
    permission_classes = [IsAuthenticated, IsPrefetOrDirecteur]

    def post(self, request, classe_id, periode_id):
        generer_bulletins_classe.delay(classe_id, periode_id)
        return Response({'detail': 'Génération des bulletins lancée en arrière-plan.'})


class ValiderBulletinView(APIView):
    permission_classes = [IsAuthenticated, IsPrefetOrDirecteur]

    def post(self, request, bulletin_pk):
        try:
            bulletin = Bulletin.objects.get(pk=bulletin_pk, statut=StatutBulletin.BROUILLON)
        except Bulletin.DoesNotExist:
            return Response({'detail': 'Bulletin introuvable ou non en brouillon.'}, status=404)

        appreciation = request.data.get('appreciation_generale', '')
        bulletin.appreciation_generale = appreciation
        bulletin.statut = StatutBulletin.VALIDE
        bulletin.valide_par = request.user
        bulletin.date_validation = timezone.now()
        bulletin.save()
        return Response({'detail': 'Bulletin validé.'})


class PublierBulletinView(APIView):
    permission_classes = [IsAuthenticated, IsPrefetOrDirecteur]

    def post(self, request, bulletin_pk):
        try:
            bulletin = Bulletin.objects.get(pk=bulletin_pk, statut=StatutBulletin.VALIDE)
        except Bulletin.DoesNotExist:
            return Response({'detail': 'Bulletin introuvable ou non validé.'}, status=404)

        bulletin.statut = StatutBulletin.PUBLIE
        bulletin.publie_par = request.user
        bulletin.date_publication = timezone.now()
        bulletin.save()

        # Génération PDF async
        generer_pdf_bulletin.delay(bulletin.pk)

        # Notification élève/parent
        from apps.notifications.services import notifier_bulletin_publie
        notifier_bulletin_publie(bulletin)

        return Response({'detail': 'Bulletin publié.'})


class DebloquerBulletinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, bulletin_pk):
        user = request.user
        roles = list(user.roles.filter(is_active=True).values_list('role', flat=True))
        if not any(r in roles for r in ['DIRECTEUR', 'COMPTABLE']):
            return Response({'detail': 'Permission insuffisante.'}, status=403)

        motif = request.data.get('motif')
        if not motif:
            return Response({'detail': 'Le motif est obligatoire.'}, status=400)

        try:
            bulletin = Bulletin.objects.get(pk=bulletin_pk, bloque=True)
        except Bulletin.DoesNotExist:
            return Response({'detail': 'Bulletin introuvable ou non bloqué.'}, status=404)

        bulletin.bloque = False
        bulletin.motif_blocage = ''
        bulletin.save(update_fields=['bloque', 'motif_blocage'])

        # Notifier selon rôle
        from apps.notifications.services import notifier_deblocage_bulletin
        notifier_deblocage_bulletin(bulletin, user, motif)

        return Response({'detail': 'Bulletin débloqué.'})
