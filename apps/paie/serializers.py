from rest_framework import serializers
from .models import Affectation, EmploiDuTemps, Seance, Emargement, FicheDePaie, LigneFicheDePaie


class AffectationSerializer(serializers.ModelSerializer):
    professeur_nom = serializers.ReadOnlyField(source='professeur.nom_complet')
    matiere_nom = serializers.ReadOnlyField(source='matiere_classe.matiere.nom')
    classe_nom = serializers.ReadOnlyField(source='matiere_classe.classe.nom')

    class Meta:
        model = Affectation
        fields = [
            'id', 'professeur', 'professeur_nom', 'matiere_classe',
            'matiere_nom', 'classe_nom', 'etablissement', 'annee_scolaire',
            'taux_horaire', 'heures_semaine', 'is_active',
        ]


class EmploiDuTempsSerializer(serializers.ModelSerializer):
    jour_display = serializers.ReadOnlyField(source='get_jour_display')
    professeur_nom = serializers.ReadOnlyField(source='affectation.professeur.nom_complet')
    matiere_nom = serializers.ReadOnlyField(source='affectation.matiere_classe.matiere.nom')
    classe_nom = serializers.ReadOnlyField(source='affectation.matiere_classe.classe.nom')

    class Meta:
        model = EmploiDuTemps
        fields = [
            'id', 'affectation', 'professeur_nom', 'matiere_nom', 'classe_nom',
            'jour', 'jour_display', 'heure_debut', 'heure_fin', 'salle',
            'date_effet', 'date_fin_effet',
        ]


class EmargementSerializer(serializers.ModelSerializer):
    professeur_nom = serializers.ReadOnlyField(source='seance.affectation.professeur.nom_complet')
    date_seance = serializers.ReadOnlyField(source='seance.date')
    emarge_par_nom = serializers.ReadOnlyField(source='emarge_par.nom_complet')

    class Meta:
        model = Emargement
        fields = [
            'id', 'seance', 'professeur_nom', 'date_seance', 'statut',
            'heure_debut_reelle', 'heure_fin_reelle', 'duree_minutes',
            'observation', 'emarge_par', 'emarge_par_nom', 'date_emargement',
        ]
        read_only_fields = ['emarge_par', 'date_emargement']


class LigneFicheDePaieSerializer(serializers.ModelSerializer):
    matiere_nom = serializers.ReadOnlyField(source='affectation.matiere_classe.matiere.nom')
    classe_nom = serializers.ReadOnlyField(source='affectation.matiere_classe.classe.nom')

    class Meta:
        model = LigneFicheDePaie
        fields = ['id', 'affectation', 'matiere_nom', 'classe_nom', 'heures_validees', 'taux_horaire', 'montant']


class FicheDePaieSerializer(serializers.ModelSerializer):
    professeur_nom = serializers.ReadOnlyField(source='professeur.nom_complet')
    lignes = LigneFicheDePaieSerializer(many=True, read_only=True)

    class Meta:
        model = FicheDePaie
        fields = [
            'id', 'professeur', 'professeur_nom', 'etablissement',
            'mois', 'montant_total', 'statut',
            'valide_par', 'date_validation',
            'paye_par', 'date_paiement_fiche',
            'pdf', 'lignes',
        ]
        read_only_fields = [
            'montant_total', 'statut', 'valide_par', 'date_validation',
            'paye_par', 'date_paiement_fiche', 'pdf',
        ]
