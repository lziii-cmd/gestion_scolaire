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


class Paiement(models.Model):
    inscription = models.ForeignKey(
        'scolarite.Inscription', on_delete=models.CASCADE, related_name='paiements'
    )
    frais = models.ForeignKey(
        Frais, on_delete=models.CASCADE, related_name='paiements'
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2)
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
