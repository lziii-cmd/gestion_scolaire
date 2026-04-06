from rest_framework.permissions import BasePermission
from .models import RoleChoices


def get_user_roles(user, etablissement=None):
    """Retourne les rôles actifs d'un utilisateur, filtrés par établissement si fourni."""
    qs = user.roles.filter(is_active=True)
    if etablissement:
        qs = qs.filter(etablissement=etablissement)
    return list(qs.values_list('role', flat=True))


def has_role(user, roles, etablissement=None):
    """Vérifie si l'utilisateur possède au moins un des rôles donnés."""
    if not user or not user.is_authenticated:
        return False
    user_roles = get_user_roles(user, etablissement)
    if isinstance(roles, str):
        roles = [roles]
    return any(r in user_roles for r in roles)


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, RoleChoices.SUPER_ADMIN)


class IsDirigeantGroupe(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, [RoleChoices.SUPER_ADMIN, RoleChoices.DIRIGEANT_GROUPE])


class IsDirecteur(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, [
            RoleChoices.SUPER_ADMIN,
            RoleChoices.DIRIGEANT_GROUPE,
            RoleChoices.DIRECTEUR,
        ])


class IsPrefetOrDirecteur(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, [
            RoleChoices.DIRECTEUR,
            RoleChoices.PREFET,
            RoleChoices.SUPER_ADMIN,
        ])


class IsSurveillant(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, [
            RoleChoices.SURVEILLANT,
            RoleChoices.DIRECTEUR,
            RoleChoices.SUPER_ADMIN,
        ])


class IsProfesseur(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, [RoleChoices.PROFESSEUR, RoleChoices.SURVEILLANT])


class IsComptable(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, [RoleChoices.COMPTABLE, RoleChoices.DIRECTEUR])


class IsCaissier(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, [RoleChoices.CAISSIER])


class IsParentOrEleve(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, [RoleChoices.PARENT, RoleChoices.ELEVE])


class EtablissementScopeMixin:
    """
    Mixin pour les vues : filtre automatiquement les querysets
    sur l'établissement actif de l'utilisateur.
    """
    def get_etablissement(self):
        etablissement_id = self.request.headers.get('X-Etablissement-Id')
        if not etablissement_id:
            return None
        from apps.etablissements.models import Etablissement
        try:
            return Etablissement.objects.get(pk=etablissement_id)
        except Etablissement.DoesNotExist:
            return None
