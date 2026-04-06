from rest_framework import serializers
from .models import Matiere, MatiereClasse


class MatiereSerializer(serializers.ModelSerializer):
    class Meta:
        model = Matiere
        fields = ['id', 'nom', 'code', 'is_active']


class MatiereClasseSerializer(serializers.ModelSerializer):
    matiere_nom = serializers.ReadOnlyField(source='matiere.nom')
    classe_nom = serializers.ReadOnlyField(source='classe.nom')
    professeur_nom = serializers.ReadOnlyField(source='professeur.nom_complet')
    serie_nom = serializers.ReadOnlyField(source='serie.nom')

    class Meta:
        model = MatiereClasse
        fields = [
            'id', 'matiere', 'matiere_nom', 'classe', 'classe_nom',
            'serie', 'serie_nom', 'coefficient', 'professeur', 'professeur_nom',
            'mode_calcul_cc', 'n_meilleures_notes', 'is_active',
        ]
