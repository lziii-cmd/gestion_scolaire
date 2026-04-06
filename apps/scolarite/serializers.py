from rest_framework import serializers
from .models import Eleve, Classe, Inscription, LienParentEleve, Transfert


class EleveSerializer(serializers.ModelSerializer):
    nom_complet = serializers.ReadOnlyField()

    class Meta:
        model = Eleve
        fields = [
            'id', 'matricule', 'nom', 'prenom', 'nom_complet',
            'date_naissance', 'lieu_naissance', 'sexe', 'photo',
        ]
        read_only_fields = ['matricule']


class ClasseSerializer(serializers.ModelSerializer):
    niveau_nom = serializers.ReadOnlyField(source='niveau.nom')
    cycle_type = serializers.ReadOnlyField(source='niveau.cycle.type_cycle')
    effectif = serializers.SerializerMethodField()

    class Meta:
        model = Classe
        fields = [
            'id', 'etablissement', 'niveau', 'niveau_nom', 'cycle_type',
            'annee_scolaire', 'nom', 'effectif_max', 'effectif',
        ]

    def get_effectif(self, obj):
        return obj.inscriptions.filter(statut='ACTIF').count()


class InscriptionSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.ReadOnlyField(source='eleve.nom_complet')
    classe_nom = serializers.ReadOnlyField(source='classe.nom')

    class Meta:
        model = Inscription
        fields = [
            'id', 'eleve', 'eleve_nom', 'classe', 'classe_nom',
            'annee_scolaire', 'etablissement', 'serie',
            'date_inscription', 'statut', 'code_identification',
            'email_genere', 'decision_passage', 'motif_decision',
        ]
        read_only_fields = ['date_inscription', 'code_identification', 'email_genere']


class InscriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inscription
        fields = ['eleve', 'classe', 'annee_scolaire', 'etablissement', 'serie']

    def validate(self, data):
        # Vérifier qu'il n'y a pas déjà une inscription active
        if Inscription.objects.filter(
            eleve=data['eleve'],
            annee_scolaire=data['annee_scolaire'],
            etablissement=data['etablissement'],
        ).exists():
            raise serializers.ValidationError(
                "Cet élève est déjà inscrit dans cet établissement pour cette année scolaire."
            )
        # Vérifier la cohérence classe/établissement
        if data['classe'].etablissement != data['etablissement']:
            raise serializers.ValidationError("La classe n'appartient pas à cet établissement.")
        return data


class LienParentEleveSerializer(serializers.ModelSerializer):
    class Meta:
        model = LienParentEleve
        fields = ['id', 'parent', 'eleve', 'lien', 'verifie', 'date_liaison']
        read_only_fields = ['verifie', 'date_liaison']


class TransfertSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.ReadOnlyField(source='inscription_origine.eleve.nom_complet')
    etablissement_origine_sigle = serializers.ReadOnlyField(
        source='inscription_origine.etablissement.sigle'
    )
    etablissement_destination_sigle = serializers.ReadOnlyField(
        source='etablissement_destination.sigle'
    )

    class Meta:
        model = Transfert
        fields = [
            'id', 'inscription_origine', 'eleve_nom',
            'etablissement_origine_sigle', 'etablissement_destination',
            'etablissement_destination_sigle', 'motif', 'date_effective',
            'statut', 'date_demande', 'date_confirmation',
        ]
        read_only_fields = ['statut', 'date_demande', 'date_confirmation', 'confirme_par']
