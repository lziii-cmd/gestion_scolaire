from rest_framework import serializers
from .models import PeriodeEvaluation, Note, ModificationNote


class PeriodeEvaluationSerializer(serializers.ModelSerializer):
    type_periode_display = serializers.ReadOnlyField(source='get_type_periode_display')

    class Meta:
        model = PeriodeEvaluation
        fields = [
            'id', 'etablissement', 'annee_scolaire', 'type_periode', 'type_periode_display',
            'numero', 'libelle', 'date_debut', 'date_fin', 'saisie_fermee',
        ]


class NoteSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.ReadOnlyField(source='inscription.eleve.nom_complet')
    matiere_nom = serializers.ReadOnlyField(source='matiere_classe.matiere.nom')
    periode_libelle = serializers.ReadOnlyField(source='periode.libelle')

    class Meta:
        model = Note
        fields = [
            'id', 'inscription', 'eleve_nom', 'matiere_classe', 'matiere_nom',
            'periode', 'periode_libelle', 'valeur', 'absence_justifiee',
            'statut', 'saisi_par', 'date_saisie',
        ]
        read_only_fields = ['statut', 'saisi_par', 'date_saisie']


class NoteSaisieSerializer(serializers.ModelSerializer):
    """Utilisé pour la saisie initiale d'une note."""
    class Meta:
        model = Note
        fields = ['inscription', 'matiere_classe', 'periode', 'valeur', 'absence_justifiee']

    def validate_valeur(self, value):
        if value is not None and (value < 0 or value > 20):
            raise serializers.ValidationError("La note doit être entre 0 et 20.")
        return value


class ModificationNoteSerializer(serializers.ModelSerializer):
    note_info = NoteSerializer(source='note', read_only=True)
    modifie_par_nom = serializers.ReadOnlyField(source='modifie_par.nom_complet')
    valide_par_nom = serializers.ReadOnlyField(source='valide_par.nom_complet')

    class Meta:
        model = ModificationNote
        fields = [
            'id', 'note', 'note_info', 'ancienne_valeur', 'nouvelle_valeur',
            'statut', 'modifie_par', 'modifie_par_nom', 'role_modificateur',
            'valide_par', 'valide_par_nom', 'date_modification', 'date_validation',
            'motif', 'motif_rejet',
        ]
        read_only_fields = [
            'ancienne_valeur', 'statut', 'modifie_par', 'role_modificateur',
            'valide_par', 'date_modification', 'date_validation', 'motif_rejet',
        ]
