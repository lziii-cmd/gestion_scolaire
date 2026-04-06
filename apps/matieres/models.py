from django.db import models
from apps.scolarite.models import Classe
from apps.etablissements.models import Serie


class Matiere(models.Model):
    """Référentiel commun géré par le Super Admin."""
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Matière'
        ordering = ['nom']

    def __str__(self):
        return f"{self.code} — {self.nom}"


class MatiereClasse(models.Model):
    """
    Association matière <-> classe avec coefficient.
    Pour le lycée, la série est obligatoire.
    """
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, related_name='affectations_classe')
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='matieres')
    serie = models.ForeignKey(
        Serie, on_delete=models.SET_NULL, null=True, blank=True
    )
    coefficient = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    professeur = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='matieres_enseignees'
    )
    # Mode de calcul CC pour le collège/lycée
    MODE_CALCUL_CHOICES = [
        ('TOUTES', 'Toutes les notes'),
        ('N_MEILLEURES', 'N meilleures notes'),
    ]
    mode_calcul_cc = models.CharField(
        max_length=15, choices=MODE_CALCUL_CHOICES, default='TOUTES'
    )
    n_meilleures_notes = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Utilisé uniquement si mode_calcul_cc = N_MEILLEURES"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Matière par classe'
        unique_together = ('matiere', 'classe', 'serie')

    def __str__(self):
        serie_str = f" ({self.serie})" if self.serie else ""
        return f"{self.matiere.nom} — {self.classe.nom}{serie_str} (coef {self.coefficient})"
