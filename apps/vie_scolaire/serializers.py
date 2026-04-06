from rest_framework import serializers
from .models import AbsenceEleve, RetardEleve, TypeSanction, Sanction


class AbsenceEleveSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.ReadOnlyField(source='inscription.eleve.nom_complet')

    class Meta:
        model = AbsenceEleve
        fields = [
            'id', 'inscription', 'eleve_nom', 'date', 'seance',
            'justifiee', 'motif', 'enregistre_par', 'created_at',
        ]
        read_only_fields = ['enregistre_par', 'created_at']


class RetardEleveSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.ReadOnlyField(source='inscription.eleve.nom_complet')

    class Meta:
        model = RetardEleve
        fields = [
            'id', 'inscription', 'eleve_nom', 'date',
            'duree_minutes', 'motif', 'enregistre_par', 'created_at',
        ]
        read_only_fields = ['enregistre_par', 'created_at']


class TypeSanctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeSanction
        fields = ['id', 'etablissement', 'libelle', 'gravite', 'apparait_bulletin_defaut']


class SanctionSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.ReadOnlyField(source='inscription.eleve.nom_complet')
    type_libelle = serializers.ReadOnlyField(source='type_sanction.libelle')

    class Meta:
        model = Sanction
        fields = [
            'id', 'inscription', 'eleve_nom', 'type_sanction', 'type_libelle',
            'date', 'motif', 'apparait_bulletin', 'prononce_par', 'created_at',
        ]
        read_only_fields = ['prononce_par', 'created_at']
