from django.db import models


class TypeCycle(models.TextChoices):
    PRESCOLAIRE = 'PRESCOLAIRE', 'Préscolaire'
    ELEMENTAIRE = 'ELEMENTAIRE', 'Élémentaire'
    COLLEGE = 'COLLEGE', 'Collège'
    LYCEE = 'LYCEE', 'Lycée'


class Etablissement(models.Model):
    sigle = models.CharField(max_length=20, unique=True)  # gsep, isft, gssp
    nom = models.CharField(max_length=200)
    adresse = models.TextField(blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to='etablissements/logos/', blank=True, null=True)
    signature_directeur = models.ImageField(upload_to='etablissements/signatures/', blank=True, null=True)
    devise = models.CharField(max_length=10, default='FCFA')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Établissement'
        verbose_name_plural = 'Établissements'
        ordering = ['nom']

    def __str__(self):
        return f"{self.sigle.upper()} — {self.nom}"


class Cycle(models.Model):
    etablissement = models.ForeignKey(
        Etablissement, on_delete=models.CASCADE, related_name='cycles'
    )
    type_cycle = models.CharField(max_length=20, choices=TypeCycle.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Cycle'
        unique_together = ('etablissement', 'type_cycle')

    def __str__(self):
        return f"{self.etablissement.sigle} — {self.get_type_cycle_display()}"

    @property
    def has_notes(self):
        return self.type_cycle != TypeCycle.PRESCOLAIRE

    @property
    def has_bulletins(self):
        return self.type_cycle != TypeCycle.PRESCOLAIRE


class Niveau(models.Model):
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='niveaux')
    nom = models.CharField(max_length=50)  # CI, CP, CE1, 6ème, etc.
    ordre = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Niveau'
        ordering = ['cycle', 'ordre']
        unique_together = ('cycle', 'nom')

    def __str__(self):
        return f"{self.cycle} — {self.nom}"


class Serie(models.Model):
    """Séries du Lycée : S, L, STEG, etc."""
    nom = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'Série'

    def __str__(self):
        return self.nom


class AnneeScolaire(models.Model):
    etablissement = models.ForeignKey(
        Etablissement, on_delete=models.CASCADE, related_name='annees_scolaires'
    )
    libelle = models.CharField(max_length=20)  # ex: 2024-2025
    date_debut = models.DateField()
    date_fin = models.DateField()
    is_active = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Année scolaire'
        verbose_name_plural = 'Années scolaires'
        unique_together = ('etablissement', 'libelle')
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.etablissement.sigle} — {self.libelle}"

    def save(self, *args, **kwargs):
        if self.is_active:
            # S'assurer qu'une seule année est active par établissement
            AnneeScolaire.objects.filter(
                etablissement=self.etablissement, is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class JourFerie(models.Model):
    etablissement = models.ForeignKey(
        Etablissement, on_delete=models.CASCADE, related_name='jours_feries'
    )
    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.CASCADE, related_name='jours_feries'
    )
    date = models.DateField()
    libelle = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Jour férié'
        unique_together = ('etablissement', 'annee_scolaire', 'date')

    def __str__(self):
        return f"{self.libelle} — {self.date}"


class RegimePedagogique(models.Model):
    """Paramétrage du régime pédagogique par cycle."""
    cycle = models.OneToOneField(Cycle, on_delete=models.CASCADE, related_name='regime')
    nb_controles_par_an = models.PositiveSmallIntegerField(default=3)
    nb_compositions_par_an = models.PositiveSmallIntegerField(default=3)
    seuil_passage = models.DecimalField(max_digits=4, decimal_places=2, default=10.00)

    class Meta:
        verbose_name = 'Régime pédagogique'

    def __str__(self):
        return f"Régime {self.cycle}"
