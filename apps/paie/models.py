from django.db import models
from apps.etablissements.models import Etablissement, AnneeScolaire


class JourSemaine(models.IntegerChoices):
    LUNDI = 0, 'Lundi'
    MARDI = 1, 'Mardi'
    MERCREDI = 2, 'Mercredi'
    JEUDI = 3, 'Jeudi'
    VENDREDI = 4, 'Vendredi'
    SAMEDI = 5, 'Samedi'


class Affectation(models.Model):
    """Lien professeur <-> matière/classe avec taux horaire."""
    professeur = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='affectations'
    )
    matiere_classe = models.ForeignKey(
        'matieres.MatiereClasse', on_delete=models.CASCADE, related_name='affectations'
    )
    etablissement = models.ForeignKey(
        Etablissement, on_delete=models.CASCADE, related_name='affectations'
    )
    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.CASCADE, related_name='affectations'
    )
    taux_horaire = models.DecimalField(max_digits=10, decimal_places=2)
    heures_semaine = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Affectation professeur'
        unique_together = ('professeur', 'matiere_classe', 'annee_scolaire')

    def __str__(self):
        return f"{self.professeur.nom_complet} — {self.matiere_classe} ({self.taux_horaire} FCFA/h)"


class EmploiDuTemps(models.Model):
    """Semaine-type : un créneau récurrent."""
    affectation = models.ForeignKey(
        Affectation, on_delete=models.CASCADE, related_name='creneaux'
    )
    jour = models.IntegerField(choices=JourSemaine.choices)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    salle = models.CharField(max_length=50, blank=True)
    date_effet = models.DateField(help_text="Date à partir de laquelle ce créneau est actif")
    date_fin_effet = models.DateField(
        null=True, blank=True,
        help_text="Laisser vide si créneau toujours actif"
    )

    class Meta:
        verbose_name = 'Emploi du temps'
        verbose_name_plural = 'Emplois du temps'

    def __str__(self):
        return f"{self.affectation.professeur.nom_complet} — {self.get_jour_display()} {self.heure_debut}"


class TypeSeance(models.TextChoices):
    PLANIFIEE = 'PLANIFIEE', 'Planifiée'
    RATTRAPAGE = 'RATTRAPAGE', 'Rattrapage'
    REMPLACEMENT = 'REMPLACEMENT', 'Remplacement'


class StatutEmargement(models.TextChoices):
    PRESENT = 'PRESENT', 'Présent'
    ABSENT = 'ABSENT', 'Absent'
    RETARD = 'RETARD', 'En retard'
    NON_TENUE = 'NON_TENUE', 'Non tenue (jour férié)'


class Seance(models.Model):
    """Instance quotidienne d'un créneau EDT."""
    emploi_du_temps = models.ForeignKey(
        EmploiDuTemps, on_delete=models.CASCADE, related_name='seances',
        null=True, blank=True
    )
    affectation = models.ForeignKey(
        Affectation, on_delete=models.CASCADE, related_name='seances'
    )
    date = models.DateField()
    type_seance = models.CharField(
        max_length=20, choices=TypeSeance.choices, default=TypeSeance.PLANIFIEE
    )

    class Meta:
        verbose_name = 'Séance'
        unique_together = ('emploi_du_temps', 'date')

    def __str__(self):
        return f"Séance {self.affectation.professeur.nom_complet} — {self.date}"


class Emargement(models.Model):
    seance = models.OneToOneField(
        Seance, on_delete=models.CASCADE, related_name='emargement'
    )
    statut = models.CharField(max_length=20, choices=StatutEmargement.choices)
    heure_debut_reelle = models.TimeField(null=True, blank=True)
    heure_fin_reelle = models.TimeField(null=True, blank=True)
    duree_minutes = models.PositiveSmallIntegerField(default=0)
    observation = models.TextField(blank=True)
    emarge_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='emargements_effectues'
    )
    date_emargement = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Émargement'

    def __str__(self):
        return f"Émargement {self.seance} — {self.statut}"


class StatutFicheDePaie(models.TextChoices):
    PROVISOIRE = 'PROVISOIRE', 'Provisoire'
    VALIDEE = 'VALIDEE', 'Validée'
    PAYEE = 'PAYEE', 'Payée'


class FicheDePaie(models.Model):
    professeur = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='fiches_de_paie'
    )
    etablissement = models.ForeignKey(
        Etablissement, on_delete=models.CASCADE, related_name='fiches_de_paie'
    )
    mois = models.DateField(help_text="Premier jour du mois concerné")
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    statut = models.CharField(
        max_length=20, choices=StatutFicheDePaie.choices, default=StatutFicheDePaie.PROVISOIRE
    )
    valide_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fiches_validees'
    )
    date_validation = models.DateTimeField(null=True, blank=True)
    paye_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fiches_payees'
    )
    date_paiement_fiche = models.DateTimeField(null=True, blank=True)
    pdf = models.FileField(upload_to='paie/pdfs/', blank=True, null=True)

    class Meta:
        verbose_name = 'Fiche de paie'
        unique_together = ('professeur', 'etablissement', 'mois')
        ordering = ['-mois']

    def __str__(self):
        return f"Paie {self.professeur.nom_complet} — {self.mois.strftime('%B %Y')} [{self.statut}]"


class LigneFicheDePaie(models.Model):
    fiche = models.ForeignKey(FicheDePaie, on_delete=models.CASCADE, related_name='lignes')
    affectation = models.ForeignKey(Affectation, on_delete=models.CASCADE)
    heures_validees = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    taux_horaire = models.DecimalField(max_digits=10, decimal_places=2)
    montant = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Ligne paie {self.fiche} — {self.affectation.matiere_classe}"


class PaiementProfesseur(models.Model):
    fiche = models.OneToOneField(
        FicheDePaie, on_delete=models.CASCADE, related_name='paiement'
    )
    etablissement = models.ForeignKey(
        Etablissement, on_delete=models.CASCADE, related_name='paiements_professeurs'
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date_paiement = models.DateTimeField(auto_now_add=True)
    caissier = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='paiements_profs_effectues'
    )
    justificatif = models.FileField(upload_to='paie/justificatifs/', blank=True, null=True)

    class Meta:
        verbose_name = 'Paiement professeur'
