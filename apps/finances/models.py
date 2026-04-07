import uuid
from django.db import models
from apps.etablissements.models import Etablissement, Niveau, AnneeScolaire


def generer_numero_recu():
    return str(uuid.uuid4()).replace('-', '').upper()[:10]


class TypeFrais(models.Model):
    etablissement = models.ForeignKey(
        Etablissement, on_delete=models.CASCADE, related_name='types_frais'
    )
    libelle = models.CharField(max_length=100)  # Inscription, Scolarité, Cantine, Transport…
    montant_defaut = models.DecimalField(max_digits=12, decimal_places=2)
    niveau = models.ForeignKey(
        Niveau, on_delete=models.SET_NULL, null=True, blank=True
    )
    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Type de frais'
        verbose_name_plural = 'Types de frais'

    def __str__(self):
        return f"{self.libelle} — {self.etablissement.sigle}"


class Frais(models.Model):
    """Frais dus par un élève pour une inscription donnée."""
    inscription = models.ForeignKey(
        'scolarite.Inscription', on_delete=models.CASCADE, related_name='frais'
    )
    type_frais = models.ForeignKey(TypeFrais, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    motif_reduction = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Frais élève'
        unique_together = ('inscription', 'type_frais')

    def __str__(self):
        return f"{self.inscription.eleve.nom_complet} — {self.type_frais.libelle} : {self.montant}"

    @property
    def solde(self):
        paye = self.paiements.aggregate(
            total=models.Sum('montant')
        )['total'] or 0
        return self.montant - paye


class StatutPaiement(models.TextChoices):
    VALIDE  = 'VALIDE',  'Valide'
    ANNULE  = 'ANNULE',  'Annulé'


class Paiement(models.Model):
    inscription = models.ForeignKey(
        'scolarite.Inscription', on_delete=models.CASCADE, related_name='paiements'
    )
    frais = models.ForeignKey(
        Frais, on_delete=models.CASCADE, related_name='paiements'
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    statut = models.CharField(
        max_length=10, choices=StatutPaiement.choices, default=StatutPaiement.VALIDE
    )
    date_paiement = models.DateTimeField(auto_now_add=True)
    caissier = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='paiements_encaisses'
    )
    observation = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Paiement'
        ordering = ['-date_paiement']

    def __str__(self):
        return f"Paiement {self.inscription.eleve.nom_complet} — {self.montant}"


class Recu(models.Model):
    paiement = models.OneToOneField(Paiement, on_delete=models.CASCADE, related_name='recu')
    numero = models.CharField(max_length=20, unique=True, default=generer_numero_recu)
    date_generation = models.DateTimeField(auto_now_add=True)
    pdf = models.FileField(upload_to='recus/pdfs/', blank=True, null=True)

    class Meta:
        verbose_name = 'Reçu'

    def __str__(self):
        return f"Reçu {self.numero}"


class TypeActionPaiement(models.TextChoices):
    MODIFICATION = 'MODIFICATION', 'Modification de montant'
    ANNULATION   = 'ANNULATION',   'Annulation'


class StatutDemande(models.TextChoices):
    EN_ATTENTE = 'EN_ATTENTE', 'En attente'
    APPROUVEE  = 'APPROUVEE',  'Approuvée'
    REJETEE    = 'REJETEE',    'Rejetée'


class ModificationPaiement(models.Model):
    """
    Toute modification ou annulation d'un paiement passe par ce workflow.
    Le caissier soumet une demande ; le directeur ou préfet valide.
    """
    paiement      = models.ForeignKey(Paiement, on_delete=models.CASCADE, related_name='modifications')
    type_action   = models.CharField(max_length=20, choices=TypeActionPaiement.choices)
    motif         = models.TextField()
    nouveau_montant = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    statut        = models.CharField(
        max_length=20, choices=StatutDemande.choices, default=StatutDemande.EN_ATTENTE
    )
    demandeur     = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True,
        related_name='demandes_modif_paiement'
    )
    validateur    = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='validations_modif_paiement'
    )
    date_demande    = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    commentaire_validateur = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Demande de modification de paiement'
        ordering = ['-date_demande']

    def __str__(self):
        return f"{self.type_action} paiement #{self.paiement_id} [{self.statut}]"


class StatutCloture(models.TextChoices):
    OUVERTE = 'OUVERTE', 'Ouverte'
    CLOTUREE = 'CLOTUREE', 'Clôturée'
    FORCEE = 'FORCEE', 'Forcée par Directeur'


class ClotureCaisse(models.Model):
    etablissement = models.ForeignKey(
        Etablissement, on_delete=models.CASCADE, related_name='clotures_caisse'
    )
    date = models.DateField()
    total_encaisse = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_paie_professeurs = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    montant_physique = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    ecart = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    caissier = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='clotures_effectuees'
    )
    force_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='clotures_forcees'
    )
    motif_force = models.TextField(blank=True)
    statut = models.CharField(
        max_length=20, choices=StatutCloture.choices, default=StatutCloture.OUVERTE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    cloture_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Clôture de caisse'
        unique_together = ('etablissement', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"Caisse {self.etablissement.sigle} — {self.date} [{self.statut}]"
