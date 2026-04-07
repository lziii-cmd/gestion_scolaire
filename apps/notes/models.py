from django.db import models
from apps.etablissements.models import Etablissement, AnneeScolaire


class TypePeriode(models.TextChoices):
    CONTROLE = 'CONTROLE', 'Contrôle'
    COMPOSITION = 'COMPOSITION', 'Composition'
    MENSUEL = 'MENSUEL', 'Mensuel'
    SEMESTRIEL = 'SEMESTRIEL', 'Semestriel'


class PeriodeEvaluation(models.Model):
    etablissement = models.ForeignKey(
        Etablissement, on_delete=models.CASCADE, related_name='periodes'
    )
    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.CASCADE, related_name='periodes'
    )
    type_periode = models.CharField(max_length=20, choices=TypePeriode.choices)
    numero = models.PositiveSmallIntegerField()  # 1, 2, 3 pour contrôles/compos
    libelle = models.CharField(max_length=100)   # ex: "1er Contrôle", "Janvier 2025"
    date_debut = models.DateField()
    date_fin = models.DateField()
    saisie_fermee = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Période d\'évaluation'
        unique_together = ('etablissement', 'annee_scolaire', 'type_periode', 'numero')
        ordering = ['date_debut']

    def __str__(self):
        return f"{self.libelle} — {self.annee_scolaire.libelle}"


class StatutNote(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    EN_ATTENTE = 'EN_ATTENTE', 'En attente de validation'


class Note(models.Model):
    inscription = models.ForeignKey(
        'scolarite.Inscription', on_delete=models.CASCADE, related_name='notes'
    )
    matiere_classe = models.ForeignKey(
        'matieres.MatiereClasse', on_delete=models.CASCADE, related_name='notes'
    )
    periode = models.ForeignKey(
        PeriodeEvaluation, on_delete=models.CASCADE, related_name='notes'
    )
    valeur = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    absence_justifiee = models.BooleanField(
        default=False, help_text="Si True, note exclue du calcul de la moyenne CC"
    )
    statut = models.CharField(
        max_length=20, choices=StatutNote.choices, default=StatutNote.ACTIVE
    )
    saisi_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True,
        related_name='notes_saisies'
    )
    delegue_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='notes_deleguees',
        help_text="Renseigné si un professeur a délégué la saisie à un surveillant"
    )
    date_saisie = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Note'
        unique_together = ('inscription', 'matiere_classe', 'periode')
        ordering = ['periode__date_debut']

    def __str__(self):
        return f"{self.inscription.eleve.nom_complet} — {self.matiere_classe.matiere.nom} — {self.valeur}"


class StatutModification(models.TextChoices):
    EN_ATTENTE = 'EN_ATTENTE', 'En attente'
    VALIDEE = 'VALIDEE', 'Validée'
    REJETEE = 'REJETEE', 'Rejetée'


class ModificationNote(models.Model):
    """
    Toute modification d'une note existante passe par ce workflow.
    L'ancienne valeur reste active jusqu'à validation.
    """
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='modifications')
    ancienne_valeur = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    nouvelle_valeur = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    statut = models.CharField(
        max_length=20, choices=StatutModification.choices, default=StatutModification.EN_ATTENTE
    )
    modifie_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True,
        related_name='modifications_notes'
    )
    role_modificateur = models.CharField(max_length=30, blank=True)
    valide_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='validations_notes'
    )
    date_modification = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    motif = models.TextField(blank=True)
    motif_rejet = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = 'Modification de note'
        ordering = ['-date_modification']

    def __str__(self):
        return f"Modif note {self.note_id}: {self.ancienne_valeur} → {self.nouvelle_valeur} [{self.statut}]"
