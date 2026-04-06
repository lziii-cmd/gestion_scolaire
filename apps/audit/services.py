from .models import JournalAudit, ActionAudit, ModuleAudit


def journaliser(
    utilisateur,
    action,
    module,
    table_concernee='',
    enregistrement_id='',
    anciennes_valeurs=None,
    nouvelles_valeurs=None,
    request=None,
    etablissement_id=None,
):
    """
    Enregistre une action dans le journal d'audit.
    Appeler depuis n'importe quel endroit du code métier.
    """
    ip = None
    user_agent = ''
    role = ''
    email = ''

    if utilisateur and utilisateur.is_authenticated:
        email = utilisateur.email
        roles = list(utilisateur.roles.filter(is_active=True).values_list('role', flat=True))
        role = roles[0] if roles else ''

    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

    JournalAudit.objects.create(
        utilisateur=utilisateur if utilisateur and utilisateur.is_authenticated else None,
        utilisateur_email=email,
        role_au_moment=role,
        etablissement_id_au_moment=etablissement_id,
        action=action,
        module=module,
        table_concernee=table_concernee,
        enregistrement_id=str(enregistrement_id),
        anciennes_valeurs=anciennes_valeurs,
        nouvelles_valeurs=nouvelles_valeurs,
        ip_address=ip,
        user_agent=user_agent,
    )
