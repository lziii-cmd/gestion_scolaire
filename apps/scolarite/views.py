from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import Eleve, Classe, Inscription, LienParentEleve, Transfert, StatutTransfert
from .serializers import (
    EleveSerializer, ClasseSerializer, InscriptionSerializer,
    InscriptionCreateSerializer, LienParentEleveSerializer, TransfertSerializer,
)
from apps.accounts.permissions import IsSuperAdmin, IsDirecteur, IsPrefetOrDirecteur


class EleveListCreateView(generics.ListCreateAPIView):
    serializer_class = EleveSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Eleve.objects.all()
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(nom__icontains=q) | qs.filter(prenom__icontains=q) | qs.filter(matricule__icontains=q)
        return qs.order_by('nom', 'prenom')


class EleveDetailView(generics.RetrieveUpdateAPIView):
    queryset = Eleve.objects.all()
    serializer_class = EleveSerializer
    permission_classes = [IsAuthenticated]


class ClasseListCreateView(generics.ListCreateAPIView):
    serializer_class = ClasseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Classe.objects.filter(
            etablissement_id=self.kwargs['etablissement_pk']
        ).select_related('niveau', 'niveau__cycle', 'annee_scolaire')


class InscriptionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InscriptionCreateSerializer
        return InscriptionSerializer

    def get_queryset(self):
        qs = Inscription.objects.select_related('eleve', 'classe', 'annee_scolaire')
        etablissement_pk = self.kwargs.get('etablissement_pk')
        if etablissement_pk:
            qs = qs.filter(etablissement_id=etablissement_pk)
        classe_id = self.request.query_params.get('classe')
        annee_id = self.request.query_params.get('annee')
        statut = self.request.query_params.get('statut')
        if classe_id:
            qs = qs.filter(classe_id=classe_id)
        if annee_id:
            qs = qs.filter(annee_scolaire_id=annee_id)
        if statut:
            qs = qs.filter(statut=statut)
        return qs


class InscriptionDetailView(generics.RetrieveUpdateAPIView):
    queryset = Inscription.objects.all()
    serializer_class = InscriptionSerializer
    permission_classes = [IsAuthenticated]


class LierParentEleveView(APIView):
    """
    Un parent lie son compte à un élève via code d'identification.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('code_identification')
        lien = request.data.get('lien', 'TUTEUR')
        try:
            inscription = Inscription.objects.get(code_identification=code)
        except Inscription.DoesNotExist:
            return Response({'detail': 'Code invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        obj, created = LienParentEleve.objects.get_or_create(
            parent=request.user,
            eleve=inscription.eleve,
            defaults={'lien': lien, 'verifie': True}
        )
        if not created:
            return Response({'detail': 'Lien déjà existant.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = LienParentEleveSerializer(obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InitierTransfertView(APIView):
    permission_classes = [IsAuthenticated, IsDirecteur]

    def post(self, request, inscription_pk):
        try:
            inscription = Inscription.objects.get(pk=inscription_pk, statut='ACTIF')
        except Inscription.DoesNotExist:
            return Response({'detail': 'Inscription introuvable ou inactive.'}, status=404)

        serializer = TransfertSerializer(data={
            **request.data,
            'inscription_origine': inscription.pk,
        })
        serializer.is_valid(raise_exception=True)
        transfert = serializer.save(initie_par=request.user)

        inscription.statut = 'TRANSFERE'
        inscription.save(update_fields=['statut'])

        return Response(TransfertSerializer(transfert).data, status=status.HTTP_201_CREATED)


class ConfirmerTransfertView(APIView):
    permission_classes = [IsAuthenticated, IsDirecteur]

    def post(self, request, transfert_pk):
        try:
            transfert = Transfert.objects.get(
                pk=transfert_pk,
                statut=StatutTransfert.EN_ATTENTE
            )
        except Transfert.DoesNotExist:
            return Response({'detail': 'Transfert introuvable.'}, status=404)

        transfert.statut = StatutTransfert.CONFIRME
        transfert.confirme_par = request.user
        transfert.date_confirmation = timezone.now()
        transfert.save()

        return Response({'detail': 'Transfert confirmé. Procédez à l\'inscription dans votre établissement.'})
