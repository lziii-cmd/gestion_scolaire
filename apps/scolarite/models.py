import uuid
from django.db import models
from django.utils import timezone

from apps.etablissements.models import Etablissement, Niveau, AnneeScolaire, Serie


def generer_matricule():
    annee = timezone.now().year
    uid = str(uuid.uuid4()).replace('-', '').upper()[:5]
    return f"SGS-{annee}-{uid}"


def generer_code_identification():
    return str(uuid.uuid4()).replace('-', '').upper()[:8]


class TypeEleve(models.TextChoices):
    ORDINAIRE = 'ORDINAIRE', 'Ordinaire'
    BOURSIER  = 'BOURSIER',  'Boursier'
    AUDITEUR  = 'AUDITEUR',  'Auditeur libre'


class StatutInscription(models.TextChoices):
    EN_ATTENTE  = 'EN_ATTENTE',  'En attente de validation'
    ACTIF       = 'ACTIF',       'Actif'
    REJETE      = 'REJETE',      'Rejeté'
    TRANSFERE   = 'TRANSFERE',   'Transféré'
    SORTI       = 'SORTI',       'Sorti'
    ADMIS       = 'ADMIS',       'Admis (fin d\'année)'
    REDOUBLANT  = 'REDOUBLANT',  'Redoublant'


class Eleve(models.Model):
    matricule = models.CharField(max_length=20, unique=True, default=generer_matricule)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=200)
    date_naissance = models.DateField(null=True, blank=True)
    lieu_naissance = models.CharField(max_length=100, blank=True)
    sexe = models.CharField(max_length=1, choices=[('M', 'Masculin'), ('F', 'Féminin')])
    type_eleve = models.CharField(
        max_length=20, choices=TypeEleve.choices, default=TypeEleve.ORDINAIRE
    )
    photo = models.ImageField(upload_to='eleves/photos/', blank=True, null=True)

    # Compte utilisateur lié (peut être null si pas encore activé)
    user = models.OneToOneField(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='eleve'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Élève'
        ordering = ['nom', 'prenom']

    def __str__(self):
        return f"{self.matricule} — {self.prenom} {self.nom}"

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"


class Classe(models.Model):
    etablissement = models.ForeignKey(
        Etablissement, on_delete=models.CASCADE, related_name='classes'
    )
    niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE, related_name='classes')
    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.CASCADE, related_name='classes'
    )
    nom = models.CharField(max_length=50)  # ex: CM2 A, 3ème B
    effectif_max = models.PositiveSmallIntegerField(default=40)

    class Meta:
        verbose_name = 'Classe'
        unique_together = ('etablissement', 'annee_scolaire', 'nom')
        ordering = ['niveau__ordre', 'nom']

    def __str__(self):
        return f"{self.nom} — {self.annee_scolaire.libelle}"


class Inscription(models.Model):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='inscriptions')
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='inscriptions')
    annee_scolaire = models.ForeignKey(
        AnneeScolaire, on_delete=models.CASCADE, related_name='inscriptions'
    )
    etablissement = models.ForeignKey(
        Etablissement, on_delete=models.CASCADE, related_name='inscriptions'
    )
    serie = models.ForeignKey(
        Serie, on_delete=models.SET_NULL, null=True, blank=True
    )
    date_inscription = models.DateField(auto_now_add=True)
    statut = models.CharField(
        max_length=20, choices=StatutInscription.choices, default=StatutInscription.ACTIF
    )
    code_identification = models.CharField(
        max_length=8, default=generer_code_identification, unique=True
    )
    email_genere = models.EmailField(blank=True)

    # Traçabilité de la création / validation
    inscrit_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='inscriptions_creees'
    )
    valide_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='inscriptions_validees'
    )
    date_validation = models.DateTimeField(null=True, blank=True)
    motif_rejet = models.TextField(blank=True)

    # Décision de fin d'année
    decision_passage = models.CharField(
        max_length=20,
        choices=[('ADMIS', 'Admis'), ('REDOUBLANT', 'Redoublant')],
        blank=True
    )
    motif_decision = models.TextField(blank=True)
    decision_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='decisions_passage'
    )

    class Meta:
        verbose_name = 'Inscription'
        unique_together = ('eleve', 'annee_scolaire', 'etablissement')
        ordering = ['-date_inscription']

    def __str__(self):
        return f"{self.eleve.nom_complet} — {self.classe.nom} ({self.annee_scolaire.libelle})"

    def save(self, *args, **kwargs):
        if not self.email_genere:
            self.email_genere = self._generer_email()
        super().save(*args, **kwargs)

    def _generer_email(self):
        prenoms = self.eleve.prenom.lower().replace(' ', '')
        nom = self.eleve.nom.lower().replace(' ', '')
        sigle = self.etablissement.sigle.lower()
        base = f"{prenoms}{nom}@{sigle}.sn"
        from apps.accounts.models import User
        if not User.objects.filter(email=base).exists():
            return base
        # Gestion des doublons
        i = 2
        while User.objects.filter(email=f"{prenoms}{nom}{i}@{sigle}.sn").exists():
            i += 1
        return f"{prenoms}{nom}{i}@{sigle}.sn"


class LienParentEleve(models.Model):
    parent = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='enfants'
    )
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='parents')
    lien = models.CharField(
        max_length=30,
        choices=[('PERE', 'Père'), ('MERE', 'Mère'), ('TUTEUR', 'Tuteur')],
        default='TUTEUR'
    )
    verifie = models.BooleanField(default=False)
    date_liaison = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('parent', 'eleve')

    def __str__(self):
        return f"{self.parent.nom_complet} → {self.eleve.nom_complet}"


class StatutTransfert(models.TextChoices):
    EN_ATTENTE = 'EN_ATTENTE', 'En attente'
    CONFIRME = 'CONFIRME', 'Confirmé'
    REFUSE = 'REFUSE', 'Refusé'


class Transfert(models.Model):
    inscription_origine = models.OneToOneField(
        Inscription, on_delete=models.CASCADE, related_name='transfert_sortant'
    )
    etablissement_destination = models.ForeignKey(
        Etablissement, on_delete=models.CASCADE, related_name='transferts_entrants'
    )
    motif = models.TextField()
    date_effective = models.DateField()
    statut = models.CharField(
        max_length=20, choices=StatutTransfert.choices, default=StatutTransfert.EN_ATTENTE
    )
    initie_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, related_name='transferts_inities'
    )
    confirme_par = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='transferts_confirmes'
    )
    inscription_destination = models.OneToOneField(
        Inscription, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='transfert_entrant'
    )
    date_demande = models.DateTimeField(auto_now_add=True)
    date_confirmation = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Transfert'

    def __str__(self):
        return f"Transfert {self.inscription_origine.eleve.nom_complet} → {self.etablissement_destination.sigle}"
