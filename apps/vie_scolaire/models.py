from django.db import models
from apps.etablissements.models import Etablissement


class AbsenceEleve(models.Model):
    inscription = models.ForeignKey(
        'scolarite.Inscription', on_delete=models.CASCADE, related_name='absences'
    )
    date = models.DateField()
    seance = models.ForeignKey(
        'paie.Seance', on_delete=models.SET_NULL, null=True, blank=True
    )
    justifiee = models.BooleanField(default=False)
    motif = models.TextField(blank=True)
    enregistre_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True,
        related_name='absences_enregistrees'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Absence élève'
        ordering = ['-date']

    def __str__(self):
        j = 'J' if self.justifiee else 'NJ'
        return f"Absence {self.inscription.eleve.nom_complet} — {self.date} ({j})"


class RetardEleve(models.Model):
    inscription = models.ForeignKey(
        'scolarite.Inscription', on_delete=models.CASCADE, related_name='retards'
    )
    date = models.DateField()
    duree_minutes = models.PositiveSmallIntegerField(default=0)
    motif = models.TextField(blank=True)
    enregistre_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True,
        related_name='retards_enregistres'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Retard élève'
        ordering = ['-date']

    def __str__(self):
        return f"Retard {self.inscription.eleve.nom_complet} — {self.date} ({self.duree_minutes} min)"


class TypeSanction(models.Model):
    etablissement = models.ForeignKey(
        Etablissement, on_delete=models.CASCADE, related_name='types_sanctions'
    )
    libelle = models.CharField(max_length=100)
    gravite = models.PositiveSmallIntegerField(default=1, help_text="1=faible, 5=grave")
    apparait_bulletin_defaut = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Type de sanction'

    def __str__(self):
        return f"{self.libelle} (gravité {self.gravite})"


class Sanction(models.Model):
    inscription = models.ForeignKey(
        'scolarite.Inscription', on_delete=models.CASCADE, related_name='sanctions'
    )
    type_sanction = models.ForeignKey(TypeSanction, on_delete=models.CASCADE)
    date = models.DateField()
    motif = models.TextField()
    apparait_bulletin = models.BooleanField()
    prononce_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True,
        related_name='sanctions_prononcees'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sanction'
        ordering = ['-date']

    def __str__(self):
        return f"Sanction {self.type_sanction.libelle} — {self.inscription.eleve.nom_complet}"
