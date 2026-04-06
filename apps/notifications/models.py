from django.db import models


class TypeNotification(models.TextChoices):
    MODIFICATION_NOTE_SOUMISE = 'MODIFICATION_NOTE_SOUMISE', 'Modification de note soumise'
    MODIFICATION_NOTE_VALIDEE = 'MODIFICATION_NOTE_VALIDEE', 'Modification de note validée'
    MODIFICATION_NOTE_REJETEE = 'MODIFICATION_NOTE_REJETEE', 'Modification de note rejetée'
    BULLETIN_PUBLIE = 'BULLETIN_PUBLIE', 'Bulletin publié'
    FICHE_PAIE_A_VALIDER = 'FICHE_PAIE_A_VALIDER', 'Fiche de paie à valider'
    FICHE_PAIE_VALIDEE = 'FICHE_PAIE_VALIDEE', 'Fiche de paie validée'
    PAIEMENT_PROFESSEUR = 'PAIEMENT_PROFESSEUR', 'Paiement professeur effectué'
    ELEVE_DEBLOQUE = 'ELEVE_DEBLOQUE', 'Élève débloqué'
    CLOTURE_OUBLIEE = 'CLOTURE_OUBLIEE', 'Clôture de caisse oubliée'
    TRANSFERT_ENTRANT = 'TRANSFERT_ENTRANT', 'Transfert élève entrant'
    ALERTE_CHUTE_MOYENNE = 'ALERTE_CHUTE_MOYENNE', 'Alerte chute de moyenne'
    ALERTE_ABSENCE_PROF = 'ALERTE_ABSENCE_PROF', 'Alerte taux absence professeur élevé'
    ALERTE_RETARDS_ELEVE = 'ALERTE_RETARDS_ELEVE', 'Alerte retards répétés élève'
    RAPPEL_PAIEMENT = 'RAPPEL_PAIEMENT', 'Rappel paiement parent'
    NOTES_NON_SAISIES = 'NOTES_NON_SAISIES', 'Notes non saisies — rappel prof'


class Notification(models.Model):
    destinataire = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='notifications'
    )
    type_notification = models.CharField(max_length=50, choices=TypeNotification.choices)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    lue = models.BooleanField(default=False)
    date_lecture = models.DateTimeField(null=True, blank=True)
    # Lien optionnel vers l'objet concerné
    objet_type = models.CharField(max_length=50, blank=True)
    objet_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.type_notification}] → {self.destinataire.nom_complet}"


class TokenFCM(models.Model):
    """Token FCM d'un appareil mobile d'un utilisateur."""
    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='tokens_fcm'
    )
    token = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Token FCM'

    def __str__(self):
        return f"FCM {self.user.email}"
