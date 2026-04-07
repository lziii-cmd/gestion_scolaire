from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class RoleChoices(models.TextChoices):
    # ── Niveau groupe (tous établissements) ──────────────────────────────
    ADMIN_GROUPE       = 'ADMIN_GROUPE',       'Administrateur du Groupe'
    PRESIDENT_GROUPE   = 'PRESIDENT_GROUPE',   'Président du Groupe'
    TRESORIER_GROUPE   = 'TRESORIER_GROUPE',   'Trésorier du Groupe'
    DIRIGEANT_GROUPE   = 'DIRIGEANT_GROUPE',   'Dirigeant Groupe'
    # ── Niveau établissement ─────────────────────────────────────────────
    DIRECTEUR          = 'DIRECTEUR',          'Directeur'
    PREFET             = 'PREFET',             'Préfet'
    SURVEILLANT        = 'SURVEILLANT',        'Surveillant'
    PROFESSEUR         = 'PROFESSEUR',         'Professeur'
    COMPTABLE          = 'COMPTABLE',          'Comptable'
    CAISSIER           = 'CAISSIER',           'Caissier'
    PARENT             = 'PARENT',             'Parent'
    ELEVE              = 'ELEVE',              'Élève'


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='users/photos/', blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    must_change_password = models.BooleanField(default=True)

    # Sécurité: compteur de tentatives de connexion
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom', 'prenom']

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return f"{self.prenom} {self.nom} <{self.email}>"

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    def is_locked(self):
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False


class RoleUtilisateur(models.Model):
    """
    Association utilisateur <-> rôle <-> établissement.
    - Rôles niveau groupe (ADMIN_GROUPE, PRESIDENT_GROUPE, etc.) : etablissement=None
    - Rôles niveau établissement (DIRECTEUR, PREFET, etc.) : etablissement renseigné
    - PREFET : cycle renseigné en plus
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='roles'
    )
    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='roles_utilisateurs'
    )
    role = models.CharField(max_length=30, choices=RoleChoices.choices)
    cycle = models.ForeignKey(
        'etablissements.Cycle',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='prefets'
    )
    is_active = models.BooleanField(default=True)
    date_affectation = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Rôle utilisateur'
        verbose_name_plural = 'Rôles utilisateurs'
        unique_together = ('user', 'etablissement', 'role')

    def __str__(self):
        etab = self.etablissement.sigle if self.etablissement else 'Groupe'
        return f"{self.user.nom_complet} — {self.role} @ {etab}"


class SessionActive(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions_actives')
    token_jti = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Session active'
        ordering = ['-last_activity']

    def __str__(self):
        return f"Session {self.user.email} — {self.ip_address}"
