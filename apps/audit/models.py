from django.db import models


class ActionAudit(models.TextChoices):
    CREATE = 'CREATE', 'Création'
    UPDATE = 'UPDATE', 'Modification'
    DELETE = 'DELETE', 'Suppression'
    LOGIN = 'LOGIN', 'Connexion'
    LOGOUT = 'LOGOUT', 'Déconnexion'
    EXPORT = 'EXPORT', 'Export'
    DEBLOCAGE = 'DEBLOCAGE', 'Déblocage élève'
    VALIDATION = 'VALIDATION', 'Validation'
    REJET = 'REJET', 'Rejet'
    TRANSFERT = 'TRANSFERT', 'Transfert'
    CLOTURE = 'CLOTURE', 'Clôture caisse'


class ModuleAudit(models.TextChoices):
    NOTES = 'NOTES', 'Notes'
    PAIEMENTS = 'PAIEMENTS', 'Paiements'
    BULLETINS = 'BULLETINS', 'Bulletins'
    PAIE = 'PAIE', 'Paie'
    ELEVES = 'ELEVES', 'Élèves'
    UTILISATEURS = 'UTILISATEURS', 'Utilisateurs'
    ETABLISSEMENTS = 'ETABLISSEMENTS', 'Établissements'
    CAISSE = 'CAISSE', 'Caisse'
    SANCTIONS = 'SANCTIONS', 'Sanctions'
    TRANSFERTS = 'TRANSFERTS', 'Transferts'
    AUTH = 'AUTH', 'Authentification'


class JournalAudit(models.Model):
    """
    Journal d'audit inaltérable. Aucune entrée n'est jamais supprimée.
    Le Super Admin lui-même ne peut pas modifier ce journal.
    """
    utilisateur = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True,
        related_name='journal_audit'
    )
    utilisateur_email = models.EmailField(blank=True)
    role_au_moment = models.CharField(max_length=30, blank=True)
    etablissement_id_au_moment = models.PositiveIntegerField(null=True, blank=True)

    action = models.CharField(max_length=20, choices=ActionAudit.choices)
    module = models.CharField(max_length=30, choices=ModuleAudit.choices)
    table_concernee = models.CharField(max_length=100, blank=True)
    enregistrement_id = models.CharField(max_length=50, blank=True)

    anciennes_valeurs = models.JSONField(null=True, blank=True)
    nouvelles_valeurs = models.JSONField(null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    date_heure = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Journal d\'audit'
        verbose_name_plural = 'Journal d\'audit'
        ordering = ['-date_heure']
        # Pas de permissions de modification — lecture seule en prod

    def __str__(self):
        return f"[{self.date_heure:%Y-%m-%d %H:%M}] {self.utilisateur_email} — {self.action} {self.module}"

    def save(self, *args, **kwargs):
        # Empêcher toute modification d'une entrée existante
        if self.pk:
            raise PermissionError("Le journal d'audit est inaltérable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Le journal d'audit ne peut pas être supprimé.")
