from django.db import models


class StatutBulletin(models.TextChoices):
    BROUILLON = 'BROUILLON', 'Brouillon'
    VALIDE = 'VALIDE', 'Validé'
    PUBLIE = 'PUBLIE', 'Publié'


class Bulletin(models.Model):
    inscription = models.ForeignKey(
        'scolarite.Inscription', on_delete=models.CASCADE, related_name='bulletins'
    )
    periode = models.ForeignKey(
        'notes.PeriodeEvaluation', on_delete=models.CASCADE, related_name='bulletins'
    )
    statut = models.CharField(
        max_length=20, choices=StatutBulletin.choices, default=StatutBulletin.BROUILLON
    )
    appreciation_generale = models.TextField(blank=True)
    rang_general = models.PositiveSmallIntegerField(null=True, blank=True)
    effectif_classe = models.PositiveSmallIntegerField(null=True, blank=True)
    moyenne_generale = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    mention = models.CharField(max_length=30, blank=True)

    # Absences/retards selon paramètre
    nb_absences = models.PositiveSmallIntegerField(default=0)
    nb_retards = models.PositiveSmallIntegerField(default=0)

    bloque = models.BooleanField(default=False)
    motif_blocage = models.TextField(blank=True)

    valide_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bulletins_valides'
    )
    date_validation = models.DateTimeField(null=True, blank=True)
    publie_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bulletins_publies'
    )
    date_publication = models.DateTimeField(null=True, blank=True)

    pdf = models.FileField(upload_to='bulletins/pdfs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Bulletin'
        unique_together = ('inscription', 'periode')
        ordering = ['periode__date_debut']

    def __str__(self):
        return f"Bulletin {self.inscription.eleve.nom_complet} — {self.periode.libelle}"


class BulletinLigne(models.Model):
    bulletin = models.ForeignKey(Bulletin, on_delete=models.CASCADE, related_name='lignes')
    matiere_classe = models.ForeignKey(
        'matieres.MatiereClasse', on_delete=models.CASCADE
    )
    # Élémentaire / Mensuel
    note = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Semestriel Collège/Lycée
    moyenne_cc = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    note_composition = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    moyenne_matiere = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rang = models.PositiveSmallIntegerField(null=True, blank=True)
    appreciation_prof = models.TextField(blank=True)
    nb_notes_prises_en_compte = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('bulletin', 'matiere_classe')

    def __str__(self):
        return f"Ligne bulletin {self.bulletin_id} — {self.matiere_classe.matiere.nom}"
