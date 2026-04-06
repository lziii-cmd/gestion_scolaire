from .models import ActionAudit, ModuleAudit


class AuditMiddleware:
    """
    Intercepte les connexions et déconnexions pour les journaliser automatiquement.
    Les actions métier (CREATE, UPDATE, etc.) sont journalisées explicitement
    via services.journaliser() dans les vues concernées.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Journaliser les connexions réussies (endpoint /api/auth/login/)
        if (
            request.path == '/api/auth/login/'
            and request.method == 'POST'
            and response.status_code == 200
            and hasattr(request, 'user')
            and request.user.is_authenticated
        ):
            from .services import journaliser
            journaliser(
                utilisateur=request.user,
                action=ActionAudit.LOGIN,
                module=ModuleAudit.AUTH,
                request=request,
            )

        return response
