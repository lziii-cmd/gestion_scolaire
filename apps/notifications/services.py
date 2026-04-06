"""
Service centralisé de notifications.
Toutes les notifications passent par ce module — le code métier
ne connaît pas les canaux (in-app, push, SMS futur).
"""
from .models import Notification, TypeNotification, TokenFCM
from django.conf import settings


def _creer_notification(destinataire, type_notif, titre, message, objet_type='', objet_id=None):
    notif = Notification.objects.create(
        destinataire=destinataire,
        type_notification=type_notif,
        titre=titre,
        message=message,
        objet_type=objet_type,
        objet_id=objet_id,
    )
    _envoyer_push(destinataire, titre, message)
    return notif


def _envoyer_push(user, titre, message):
    """Envoie une notification push FCM à tous les appareils de l'utilisateur."""
    tokens = TokenFCM.objects.filter(user=user).values_list('token', flat=True)
    if not tokens:
        return
    fcm_key = getattr(settings, 'FCM_SERVER_KEY', '')
    if not fcm_key:
        return
    try:
        import requests
        for token in tokens:
            requests.post(
                'https://fcm.googleapis.com/fcm/send',
                json={
                    'to': token,
                    'notification': {'title': titre, 'body': message},
                },
                headers={'Authorization': f'key={fcm_key}'},
                timeout=5,
            )
    except Exception:
        pass


def notifier_modification_note_soumise(note):
    from apps.accounts.models import RoleUtilisateur, RoleChoices
    etablissement = note.inscription.etablissement
    cycle = note.inscription.classe.niveau.cycle

    destinataires = RoleUtilisateur.objects.filter(
        etablissement=etablissement,
        role__in=[RoleChoices.DIRECTEUR, RoleChoices.PREFET],
        is_active=True,
    ).select_related('user')

    for r in destinataires:
        if r.role == RoleChoices.PREFET and r.cycle and r.cycle != cycle:
            continue
        _creer_notification(
            r.user,
            TypeNotification.MODIFICATION_NOTE_SOUMISE,
            'Modification de note soumise',
            f"Une modification de note pour {note.inscription.eleve.nom_complet} est en attente de validation.",
            objet_type='Note', objet_id=note.pk,
        )


def notifier_modification_note_validee(modif):
    from apps.accounts.models import RoleUtilisateur, RoleChoices
    note = modif.note
    inscription = note.inscription
    etablissement = inscription.etablissement

    destinataires_roles = RoleUtilisateur.objects.filter(
        etablissement=etablissement,
        role__in=[RoleChoices.DIRECTEUR, RoleChoices.PREFET, RoleChoices.SURVEILLANT],
        is_active=True,
    ).select_related('user')

    msg = f"La note de {inscription.eleve.nom_complet} a été modifiée : {modif.ancienne_valeur} → {modif.nouvelle_valeur}."
    for r in destinataires_roles:
        _creer_notification(r.user, TypeNotification.MODIFICATION_NOTE_VALIDEE, 'Note modifiée', msg)

    # Notifier le prof
    if modif.modifie_par:
        _creer_notification(modif.modifie_par, TypeNotification.MODIFICATION_NOTE_VALIDEE, 'Note modifiée', msg)

    # Notifier l'élève
    if inscription.eleve.user:
        _creer_notification(inscription.eleve.user, TypeNotification.MODIFICATION_NOTE_VALIDEE, 'Votre note a été mise à jour', msg)

    # Notifier les parents
    for lien in inscription.eleve.parents.select_related('parent'):
        _creer_notification(lien.parent, TypeNotification.MODIFICATION_NOTE_VALIDEE, 'Note de votre enfant mise à jour', msg)


def notifier_modification_note_rejetee(modif):
    if modif.modifie_par:
        _creer_notification(
            modif.modifie_par,
            TypeNotification.MODIFICATION_NOTE_REJETEE,
            'Modification de note rejetée',
            f"Votre demande de modification a été rejetée. Motif : {modif.motif_rejet}",
        )


def notifier_bulletin_publie(bulletin):
    inscription = bulletin.inscription
    msg = f"Votre bulletin {bulletin.periode.libelle} est disponible."
    if inscription.eleve.user:
        _creer_notification(inscription.eleve.user, TypeNotification.BULLETIN_PUBLIE, 'Bulletin disponible', msg)
    for lien in inscription.eleve.parents.select_related('parent'):
        _creer_notification(lien.parent, TypeNotification.BULLETIN_PUBLIE, 'Bulletin de votre enfant disponible', msg)


def notifier_deblocage_bulletin(bulletin, debloquer_par, motif):
    from apps.accounts.models import RoleChoices
    roles = list(debloquer_par.roles.filter(is_active=True).values_list('role', flat=True))
    inscription = bulletin.inscription
    etablissement = inscription.etablissement

    if RoleChoices.DIRECTEUR in roles:
        from apps.accounts.models import RoleUtilisateur
        comptables = RoleUtilisateur.objects.filter(
            etablissement=etablissement, role=RoleChoices.COMPTABLE, is_active=True
        ).select_related('user')
        for r in comptables:
            _creer_notification(r.user, TypeNotification.ELEVE_DEBLOQUE,
                                'Élève débloqué par le Directeur',
                                f"{inscription.eleve.nom_complet} a été débloqué. Motif : {motif}")
    elif RoleChoices.COMPTABLE in roles:
        from apps.accounts.models import RoleUtilisateur
        directeurs = RoleUtilisateur.objects.filter(
            etablissement=etablissement, role=RoleChoices.DIRECTEUR, is_active=True
        ).select_related('user')
        for r in directeurs:
            _creer_notification(r.user, TypeNotification.ELEVE_DEBLOQUE,
                                'Élève débloqué par le Comptable',
                                f"{inscription.eleve.nom_complet} a été débloqué. Motif : {motif}")


def notifier_fiches_paie_a_valider(etablissement):
    from apps.accounts.models import RoleUtilisateur, RoleChoices
    comptables = RoleUtilisateur.objects.filter(
        etablissement=etablissement, role=RoleChoices.COMPTABLE, is_active=True
    ).select_related('user')
    for r in comptables:
        _creer_notification(r.user, TypeNotification.FICHE_PAIE_A_VALIDER,
                            'Fiches de paie à valider',
                            'Les fiches de paie du mois sont prêtes pour validation.')


def notifier_fiche_paie_validee(fiche):
    from apps.accounts.models import RoleUtilisateur, RoleChoices
    caissiers = RoleUtilisateur.objects.filter(
        etablissement=fiche.etablissement, role=RoleChoices.CAISSIER, is_active=True
    ).select_related('user')
    msg = f"La fiche de paie de {fiche.professeur.nom_complet} est validée et prête au paiement."
    for r in caissiers:
        _creer_notification(r.user, TypeNotification.FICHE_PAIE_VALIDEE, 'Fiche de paie validée', msg)


def notifier_paiement_professeur(fiche):
    _creer_notification(
        fiche.professeur,
        TypeNotification.PAIEMENT_PROFESSEUR,
        'Paiement effectué',
        f"Votre salaire de {fiche.montant_total} FCFA pour {fiche.mois.strftime('%B %Y')} a été versé.",
    )


def notifier_cloture_oubliee(etablissement):
    from apps.accounts.models import RoleUtilisateur, RoleChoices
    destinataires = RoleUtilisateur.objects.filter(
        etablissement=etablissement,
        role__in=[RoleChoices.CAISSIER, RoleChoices.DIRECTEUR],
        is_active=True,
    ).select_related('user')
    for r in destinataires:
        _creer_notification(r.user, TypeNotification.CLOTURE_OUBLIEE,
                            'Clôture de caisse oubliée',
                            'La caisse n\'a pas été clôturée aujourd\'hui.')
