from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import (
    Affectation, EmploiDuTemps, Seance, Emargement,
    FicheDePaie, PaiementProfesseur, StatutFicheDePaie, StatutEmargement
)
from .serializers import (
    AffectationSerializer, EmploiDuTempsSerializer,
    EmargementSerializer, FicheDePaieSerializer,
)
from apps.accounts.permissions import IsComptable, IsCaissier, IsSurveillant, IsDirecteur


class AffectationListCreateView(generics.ListCreateAPIView):
    serializer_class = AffectationSerializer
    permission_classes = [IsAuthenticated, IsDirecteur]

    def get_queryset(self):
        qs = Affectation.objects.select_related(
            'professeur', 'matiere_classe__matiere', 'matiere_classe__classe'
        )
        etablissement_pk = self.kwargs.get('etablissement_pk')
        annee_id = self.request.query_params.get('annee')
        if etablissement_pk:
            qs = qs.filter(etablissement_id=etablissement_pk)
        if annee_id:
            qs = qs.filter(annee_scolaire_id=annee_id)
        return qs


class EmploiDuTempsListCreateView(generics.ListCreateAPIView):
    serializer_class = EmploiDuTempsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = EmploiDuTemps.objects.select_related(
            'affectation__professeur',
            'affectation__matiere_classe__matiere',
            'affectation__matiere_classe__classe',
        )
        classe_id = self.request.query_params.get('classe')
        professeur_id = self.request.query_params.get('professeur')
        if classe_id:
            qs = qs.filter(affectation__matiere_classe__classe_id=classe_id)
        if professeur_id:
            qs = qs.filter(affectation__professeur_id=professeur_id)
        return qs


class EmargementJourView(APIView):
    """
    Le Surveillant consulte et saisit les émargements du jour.
    """
    permission_classes = [IsAuthenticated, IsSurveillant]

    def get(self, request, etablissement_pk):
        from datetime import date
        today = date.today()
        seances = Seance.objects.filter(
            affectation__etablissement_id=etablissement_pk,
            date=today,
        ).select_related(
            'affectation__professeur',
            'affectation__matiere_classe__matiere',
            'affectation__matiere_classe__classe',
        ).prefetch_related('emargement')

        data = []
        for s in seances:
            emarg = getattr(s, 'emargement', None)
            data.append({
                'seance_id': s.pk,
                'professeur': s.affectation.professeur.nom_complet,
                'matiere': s.affectation.matiere_classe.matiere.nom,
                'classe': s.affectation.matiere_classe.classe.nom,
                'statut': emarg.statut if emarg else None,
                'emarge': emarg is not None,
            })
        return Response(data)

    def post(self, request, etablissement_pk):
        seance_id = request.data.get('seance_id')
        statut = request.data.get('statut')
        heure_debut = request.data.get('heure_debut_reelle')
        heure_fin = request.data.get('heure_fin_reelle')
        observation = request.data.get('observation', '')

        if statut not in [s.value for s in StatutEmargement]:
            return Response({'detail': 'Statut invalide.'}, status=400)

        try:
            seance = Seance.objects.get(pk=seance_id, affectation__etablissement_id=etablissement_pk)
        except Seance.DoesNotExist:
            return Response({'detail': 'Séance introuvable.'}, status=404)

        # Calculer durée
        duree = 0
        if heure_debut and heure_fin:
            from datetime import datetime
            fmt = '%H:%M'
            try:
                d = datetime.strptime(heure_fin, fmt) - datetime.strptime(heure_debut, fmt)
                duree = max(0, int(d.total_seconds() // 60))
            except ValueError:
                pass

        emarg, _ = Emargement.objects.update_or_create(
            seance=seance,
            defaults={
                'statut': statut,
                'heure_debut_reelle': heure_debut,
                'heure_fin_reelle': heure_fin,
                'duree_minutes': duree,
                'observation': observation,
                'emarge_par': request.user,
            }
        )
        return Response(EmargementSerializer(emarg).data)


class FicheDePaieListView(generics.ListAPIView):
    serializer_class = FicheDePaieSerializer
    permission_classes = [IsAuthenticated, IsComptable]

    def get_queryset(self):
        qs = FicheDePaie.objects.select_related('professeur', 'etablissement').prefetch_related('lignes')
        etablissement_pk = self.kwargs.get('etablissement_pk')
        mois = self.request.query_params.get('mois')
        statut = self.request.query_params.get('statut')
        if etablissement_pk:
            qs = qs.filter(etablissement_id=etablissement_pk)
        if mois:
            qs = qs.filter(mois=mois)
        if statut:
            qs = qs.filter(statut=statut)
        return qs


class ValiderFicheDePaieView(APIView):
    permission_classes = [IsAuthenticated, IsComptable]

    def post(self, request, fiche_pk):
        try:
            fiche = FicheDePaie.objects.get(pk=fiche_pk, statut=StatutFicheDePaie.PROVISOIRE)
        except FicheDePaie.DoesNotExist:
            return Response({'detail': 'Fiche introuvable ou déjà validée.'}, status=404)

        fiche.statut = StatutFicheDePaie.VALIDEE
        fiche.valide_par = request.user
        fiche.date_validation = timezone.now()
        fiche.save()

        from apps.notifications.services import notifier_fiche_paie_validee
        notifier_fiche_paie_validee(fiche)

        return Response({'detail': 'Fiche de paie validée.'})


class PayerFicheDePaieView(APIView):
    """Le Caissier enregistre le paiement du professeur."""
    permission_classes = [IsAuthenticated, IsCaissier]

    def post(self, request, fiche_pk):
        try:
            fiche = FicheDePaie.objects.get(pk=fiche_pk, statut=StatutFicheDePaie.VALIDEE)
        except FicheDePaie.DoesNotExist:
            return Response({'detail': 'Fiche introuvable ou non validée.'}, status=404)

        PaiementProfesseur.objects.create(
            fiche=fiche,
            etablissement=fiche.etablissement,
            montant=fiche.montant_total,
            caissier=request.user,
        )
        fiche.statut = StatutFicheDePaie.PAYEE
        fiche.paye_par = request.user
        fiche.date_paiement_fiche = timezone.now()
        fiche.save()

        from apps.notifications.services import notifier_paiement_professeur
        notifier_paiement_professeur(fiche)

        return Response({'detail': 'Professeur payé.'})
