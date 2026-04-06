from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import TypeFrais, Frais, Paiement, Recu, ClotureCaisse, StatutCloture
from .serializers import (
    TypeFraisSerializer, FraisSerializer, PaiementSerializer,
    RecuSerializer, ClotureCaisseSerializer,
)
from apps.accounts.permissions import IsComptable, IsCaissier, IsDirecteur


class TypeFraisListCreateView(generics.ListCreateAPIView):
    serializer_class = TypeFraisSerializer
    permission_classes = [IsAuthenticated, IsComptable]

    def get_queryset(self):
        return TypeFrais.objects.filter(
            etablissement_id=self.kwargs['etablissement_pk'],
            is_active=True,
        )


class FraisListCreateView(generics.ListCreateAPIView):
    serializer_class = FraisSerializer
    permission_classes = [IsAuthenticated, IsComptable]

    def get_queryset(self):
        qs = Frais.objects.select_related(
            'inscription__eleve', 'type_frais'
        )
        inscription_id = self.request.query_params.get('inscription')
        classe_id = self.request.query_params.get('classe')
        if inscription_id:
            qs = qs.filter(inscription_id=inscription_id)
        if classe_id:
            qs = qs.filter(inscription__classe_id=classe_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class EncaisserPaiementView(APIView):
    """Seul le Caissier peut encaisser un paiement."""
    permission_classes = [IsAuthenticated, IsCaissier]

    @transaction.atomic
    def post(self, request):
        frais_id = request.data.get('frais')
        montant = request.data.get('montant')
        observation = request.data.get('observation', '')

        try:
            frais = Frais.objects.select_related('inscription').get(pk=frais_id)
        except Frais.DoesNotExist:
            return Response({'detail': 'Frais introuvable.'}, status=404)

        if not montant or float(montant) <= 0:
            return Response({'detail': 'Montant invalide.'}, status=400)

        if float(montant) > float(frais.solde):
            return Response(
                {'detail': f'Montant supérieur au solde dû ({frais.solde}).'},
                status=400
            )

        paiement = Paiement.objects.create(
            inscription=frais.inscription,
            frais=frais,
            montant=montant,
            caissier=request.user,
            observation=observation,
        )
        recu = Recu.objects.create(paiement=paiement)

        # Génération PDF reçu async
        from .tasks import generer_pdf_recu
        generer_pdf_recu.delay(recu.pk)

        return Response({
            'paiement_id': paiement.pk,
            'recu_numero': recu.numero,
        }, status=status.HTTP_201_CREATED)


class SituationFinanciereView(APIView):
    """Résumé des frais d'un élève (tous soldes)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, inscription_pk):
        from apps.scolarite.models import Inscription
        try:
            inscription = Inscription.objects.select_related('eleve').get(pk=inscription_pk)
        except Inscription.DoesNotExist:
            return Response({'detail': 'Inscription introuvable.'}, status=404)

        frais_qs = Frais.objects.filter(inscription=inscription).select_related('type_frais')
        total_du = frais_qs.aggregate(t=Sum('montant'))['t'] or 0
        total_paye = Paiement.objects.filter(inscription=inscription).aggregate(
            t=Sum('montant')
        )['t'] or 0

        return Response({
            'inscription_id': inscription.pk,
            'eleve_nom': inscription.eleve.nom_complet,
            'total_du': total_du,
            'total_paye': total_paye,
            'solde': float(total_du) - float(total_paye),
            'details': FraisSerializer(frais_qs, many=True).data,
        })


class ClotureCaisseListView(generics.ListAPIView):
    serializer_class = ClotureCaisseSerializer
    permission_classes = [IsAuthenticated, IsComptable]

    def get_queryset(self):
        return ClotureCaisse.objects.filter(
            etablissement_id=self.kwargs['etablissement_pk']
        )


class EffectuerClotureCaisseView(APIView):
    """Le Caissier clôture la caisse du jour."""
    permission_classes = [IsAuthenticated, IsCaissier]

    @transaction.atomic
    def post(self, request, etablissement_pk):
        from django.utils.timezone import localdate
        today = localdate()

        # Vérifier si déjà clôturée
        if ClotureCaisse.objects.filter(
            etablissement_id=etablissement_pk,
            date=today,
            statut=StatutCloture.CLOTUREE
        ).exists():
            return Response({'detail': 'Caisse déjà clôturée pour aujourd\'hui.'}, status=400)

        # Calculer total encaissé
        total_encaisse = Paiement.objects.filter(
            inscription__etablissement_id=etablissement_pk,
            date_paiement__date=today,
        ).aggregate(t=Sum('montant'))['t'] or 0

        # Total paie professeurs du jour
        from apps.paie.models import PaiementProfesseur
        total_paie = PaiementProfesseur.objects.filter(
            etablissement_id=etablissement_pk,
            date_paiement__date=today,
        ).aggregate(t=Sum('montant'))['t'] or 0

        montant_physique = request.data.get('montant_physique')
        if montant_physique is None:
            return Response({'detail': 'montant_physique est obligatoire.'}, status=400)

        ecart = float(montant_physique) - float(total_encaisse) + float(total_paie)

        cloture, _ = ClotureCaisse.objects.update_or_create(
            etablissement_id=etablissement_pk,
            date=today,
            defaults={
                'total_encaisse': total_encaisse,
                'total_paie_professeurs': total_paie,
                'montant_physique': montant_physique,
                'ecart': ecart,
                'caissier': request.user,
                'statut': StatutCloture.CLOTUREE,
                'cloture_at': timezone.now(),
            }
        )

        return Response(ClotureCaisseSerializer(cloture).data)


class ForcerClotureCaisseView(APIView):
    """Le Directeur peut forcer une clôture avec motif."""
    permission_classes = [IsAuthenticated, IsDirecteur]

    def post(self, request, etablissement_pk):
        motif = request.data.get('motif')
        if not motif:
            return Response({'detail': 'Le motif est obligatoire.'}, status=400)

        from django.utils.timezone import localdate
        today = localdate()

        cloture, _ = ClotureCaisse.objects.update_or_create(
            etablissement_id=etablissement_pk,
            date=today,
            defaults={
                'force_par': request.user,
                'motif_force': motif,
                'statut': StatutCloture.FORCEE,
                'cloture_at': timezone.now(),
            }
        )
        return Response(ClotureCaisseSerializer(cloture).data)
