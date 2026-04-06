from rest_framework import serializers
from django.db.models import Sum
from .models import TypeFrais, Frais, Paiement, Recu, ClotureCaisse


class TypeFraisSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeFrais
        fields = ['id', 'etablissement', 'libelle', 'montant_defaut', 'niveau', 'annee_scolaire', 'is_active']


class FraisSerializer(serializers.ModelSerializer):
    solde = serializers.ReadOnlyField()
    type_frais_libelle = serializers.ReadOnlyField(source='type_frais.libelle')
    eleve_nom = serializers.ReadOnlyField(source='inscription.eleve.nom_complet')

    class Meta:
        model = Frais
        fields = [
            'id', 'inscription', 'eleve_nom', 'type_frais', 'type_frais_libelle',
            'montant', 'solde', 'motif_reduction', 'created_at',
        ]
        read_only_fields = ['created_at']


class PaiementSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.ReadOnlyField(source='inscription.eleve.nom_complet')
    caissier_nom = serializers.ReadOnlyField(source='caissier.nom_complet')
    recu_numero = serializers.ReadOnlyField(source='recu.numero')

    class Meta:
        model = Paiement
        fields = [
            'id', 'inscription', 'eleve_nom', 'frais', 'montant',
            'date_paiement', 'caissier', 'caissier_nom', 'observation', 'recu_numero',
        ]
        read_only_fields = ['date_paiement', 'caissier']

    def validate_montant(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être positif.")
        return value


class RecuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recu
        fields = ['id', 'paiement', 'numero', 'date_generation', 'pdf']


class ClotureCaisseSerializer(serializers.ModelSerializer):
    caissier_nom = serializers.ReadOnlyField(source='caissier.nom_complet')

    class Meta:
        model = ClotureCaisse
        fields = [
            'id', 'etablissement', 'date', 'total_encaisse', 'total_paie_professeurs',
            'montant_physique', 'ecart', 'caissier', 'caissier_nom',
            'statut', 'created_at', 'cloture_at',
        ]
        read_only_fields = ['total_encaisse', 'total_paie_professeurs', 'ecart', 'caissier', 'statut', 'created_at']


class SituationFinanciereSerializer(serializers.Serializer):
    """Vue synthétique de la situation financière d'un élève."""
    inscription_id = serializers.IntegerField()
    eleve_nom = serializers.CharField()
    total_du = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_paye = serializers.DecimalField(max_digits=12, decimal_places=2)
    solde = serializers.DecimalField(max_digits=12, decimal_places=2)
    details = FraisSerializer(many=True)
