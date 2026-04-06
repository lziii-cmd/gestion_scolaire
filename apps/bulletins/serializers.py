from rest_framework import serializers
from .models import Bulletin, BulletinLigne


class BulletinLigneSerializer(serializers.ModelSerializer):
    matiere_nom = serializers.ReadOnlyField(source='matiere_classe.matiere.nom')
    coefficient = serializers.ReadOnlyField(source='matiere_classe.coefficient')

    class Meta:
        model = BulletinLigne
        fields = [
            'id', 'matiere_classe', 'matiere_nom', 'coefficient',
            'note', 'moyenne_cc', 'note_composition', 'moyenne_matiere',
            'rang', 'appreciation_prof', 'nb_notes_prises_en_compte',
        ]


class BulletinSerializer(serializers.ModelSerializer):
    lignes = BulletinLigneSerializer(many=True, read_only=True)
    eleve_nom = serializers.ReadOnlyField(source='inscription.eleve.nom_complet')
    classe_nom = serializers.ReadOnlyField(source='inscription.classe.nom')
    periode_libelle = serializers.ReadOnlyField(source='periode.libelle')

    class Meta:
        model = Bulletin
        fields = [
            'id', 'inscription', 'eleve_nom', 'classe_nom',
            'periode', 'periode_libelle', 'statut', 'appreciation_generale',
            'rang_general', 'effectif_classe', 'moyenne_generale', 'mention',
            'nb_absences', 'nb_retards', 'bloque', 'motif_blocage',
            'valide_par', 'date_validation', 'publie_par', 'date_publication',
            'pdf', 'lignes',
        ]
        read_only_fields = [
            'statut', 'valide_par', 'date_validation', 'publie_par',
            'date_publication', 'bloque', 'pdf',
        ]
