from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import PeriodeEvaluation, Note, ModificationNote, StatutModification
from .serializers import (
    PeriodeEvaluationSerializer, NoteSerializer, NoteSaisieSerializer,
    ModificationNoteSerializer,
)
from apps.accounts.permissions import (
    IsSuperAdmin, IsDirecteur, IsPrefetOrDirecteur, IsSurveillant, IsProfesseur
)
from apps.accounts.models import RoleChoices


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


class PeriodeListCreateView(generics.ListCreateAPIView):
    serializer_class = PeriodeEvaluationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PeriodeEvaluation.objects.filter(
            etablissement_id=self.kwargs.get('etablissement_pk'),
        ).order_by('date_debut')

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsDirecteur()]
        return [IsAuthenticated()]


class NoteListView(generics.ListAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Note.objects.select_related(
            'inscription__eleve', 'matiere_classe__matiere', 'periode'
        )
        classe_id = self.request.query_params.get('classe')
        periode_id = self.request.query_params.get('periode')
        matiere_classe_id = self.request.query_params.get('matiere_classe')
        inscription_id = self.request.query_params.get('inscription')

        if classe_id:
            qs = qs.filter(inscription__classe_id=classe_id)
        if periode_id:
            qs = qs.filter(periode_id=periode_id)
        if matiere_classe_id:
            qs = qs.filter(matiere_classe_id=matiere_classe_id)
        if inscription_id:
            qs = qs.filter(inscription_id=inscription_id)
        return qs


class SaisirNoteView(APIView):
    """
    Saisie d'une note par un Professeur ou un Surveillant.
    - Si la note n'existe pas : création directe.
    - Si elle existe déjà : création d'une ModificationNote en attente.
    """
    permission_classes = [IsAuthenticated, IsProfesseur]

    def post(self, request):
        serializer = NoteSaisieSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Vérifier que la période est ouverte
        periode = data['periode']
        if periode.saisie_fermee:
            return Response(
                {'detail': 'La période de saisie est fermée.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        note, created = Note.objects.get_or_create(
            inscription=data['inscription'],
            matiere_classe=data['matiere_classe'],
            periode=data['periode'],
            defaults={
                'valeur': data.get('valeur'),
                'absence_justifiee': data.get('absence_justifiee', False),
                'saisi_par': request.user,
            }
        )

        if not created:
            # Note existante → workflow de modification
            roles = list(request.user.roles.filter(is_active=True).values_list('role', flat=True))
            role = roles[0] if roles else ''
            ModificationNote.objects.create(
                note=note,
                ancienne_valeur=note.valeur,
                nouvelle_valeur=data.get('valeur'),
                modifie_par=request.user,
                role_modificateur=role,
                motif=request.data.get('motif', ''),
                ip_address=get_client_ip(request),
            )
            # Envoyer notification au directeur/préfet
            from apps.notifications.services import notifier_modification_note_soumise
            notifier_modification_note_soumise(note)
            return Response(
                {'detail': 'Modification soumise pour validation.'},
                status=status.HTTP_202_ACCEPTED
            )

        return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)


class ValiderModificationNoteView(APIView):
    """Directeur ou Préfet valide/rejette une modification de note."""
    permission_classes = [IsAuthenticated, IsPrefetOrDirecteur]

    def post(self, request, modification_pk):
        try:
            modif = ModificationNote.objects.get(
                pk=modification_pk, statut=StatutModification.EN_ATTENTE
            )
        except ModificationNote.DoesNotExist:
            return Response({'detail': 'Modification introuvable.'}, status=404)

        action = request.data.get('action')  # 'valider' ou 'rejeter'
        if action == 'valider':
            modif.statut = StatutModification.VALIDEE
            modif.valide_par = request.user
            modif.date_validation = timezone.now()
            modif.save()

            # Appliquer la nouvelle valeur
            modif.note.valeur = modif.nouvelle_valeur
            modif.note.save(update_fields=['valeur'])

            from apps.notifications.services import notifier_modification_note_validee
            notifier_modification_note_validee(modif)

            return Response({'detail': 'Note modifiée et validée.'})

        elif action == 'rejeter':
            motif_rejet = request.data.get('motif_rejet', '')
            modif.statut = StatutModification.REJETEE
            modif.valide_par = request.user
            modif.date_validation = timezone.now()
            modif.motif_rejet = motif_rejet
            modif.save()

            from apps.notifications.services import notifier_modification_note_rejetee
            notifier_modification_note_rejetee(modif)

            return Response({'detail': 'Modification rejetée.'})

        return Response({'detail': 'Action invalide. Utilisez "valider" ou "rejeter".'}, status=400)


class ModificationNoteListView(generics.ListAPIView):
    serializer_class = ModificationNoteSerializer
    permission_classes = [IsAuthenticated, IsPrefetOrDirecteur]

    def get_queryset(self):
        qs = ModificationNote.objects.select_related('note', 'modifie_par', 'valide_par')
        statut = self.request.query_params.get('statut', 'EN_ATTENTE')
        return qs.filter(statut=statut).order_by('-date_modification')
