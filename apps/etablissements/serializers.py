from rest_framework import serializers
from .models import Etablissement, Cycle, Niveau, Serie, AnneeScolaire, JourFerie, RegimePedagogique


class NiveauSerializer(serializers.ModelSerializer):
    class Meta:
        model = Niveau
        fields = ['id', 'nom', 'ordre', 'is_active']


class RegimePedagogiqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegimePedagogique
        fields = ['nb_controles_par_an', 'nb_compositions_par_an', 'seuil_passage']


class CycleSerializer(serializers.ModelSerializer):
    niveaux = NiveauSerializer(many=True, read_only=True)
    regime = RegimePedagogiqueSerializer(read_only=True)
    type_cycle_display = serializers.ReadOnlyField(source='get_type_cycle_display')

    class Meta:
        model = Cycle
        fields = ['id', 'type_cycle', 'type_cycle_display', 'is_active', 'niveaux', 'regime']


class EtablissementSerializer(serializers.ModelSerializer):
    cycles = CycleSerializer(many=True, read_only=True)

    class Meta:
        model = Etablissement
        fields = [
            'id', 'sigle', 'nom', 'adresse', 'telephone', 'email',
            'logo', 'signature_directeur', 'devise', 'is_active', 'cycles',
        ]


class EtablissementListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Etablissement
        fields = ['id', 'sigle', 'nom', 'is_active']


class AnneeScolaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnneeScolaire
        fields = [
            'id', 'etablissement', 'libelle', 'date_debut', 'date_fin',
            'is_active', 'is_locked',
        ]
        read_only_fields = ['is_locked']


class SerieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Serie
        fields = ['id', 'nom', 'description']


class JourFerieSerializer(serializers.ModelSerializer):
    class Meta:
        model = JourFerie
        fields = ['id', 'etablissement', 'annee_scolaire', 'date', 'libelle']
