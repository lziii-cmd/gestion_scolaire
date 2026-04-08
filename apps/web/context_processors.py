from apps.etablissements.models import Etablissement
from apps.accounts.models import RoleChoices
from apps.finances.models import ModificationPaiement, StatutDemande
from apps.scolarite.models import Inscription, StatutInscription

# Groupes de rôles pour les permissions d'affichage
_ROLES_ELEVES = {
    RoleChoices.ADMIN_GROUPE, RoleChoices.DIRECTEUR, RoleChoices.PREFET,
    RoleChoices.SURVEILLANT, RoleChoices.PROFESSEUR,
    RoleChoices.PRESIDENT_GROUPE, RoleChoices.DIRIGEANT_GROUPE,
}
_ROLES_PEDAGOGIE = {
    RoleChoices.ADMIN_GROUPE, RoleChoices.DIRECTEUR, RoleChoices.PREFET,
    RoleChoices.SURVEILLANT, RoleChoices.PROFESSEUR,
    RoleChoices.PRESIDENT_GROUPE, RoleChoices.DIRIGEANT_GROUPE,
}
_ROLES_FINANCES = {
    RoleChoices.ADMIN_GROUPE, RoleChoices.DIRECTEUR,
    RoleChoices.COMPTABLE, RoleChoices.CAISSIER,
    RoleChoices.TRESORIER_GROUPE, RoleChoices.PRESIDENT_GROUPE,
    RoleChoices.DIRIGEANT_GROUPE,
}
_ROLES_GESTION = {
    RoleChoices.ADMIN_GROUPE, RoleChoices.DIRECTEUR,
}


def sidebar_context(request):
    """Injecte les permissions et données nécessaires à la sidebar/topbar."""
    if not request.user.is_authenticated:
        return {}

    ctx = {}

    # Superuser = développeur technique : accès système uniquement, pas aux données métier
    if request.user.is_superuser:
        ctx['perm_eleves']      = False
        ctx['perm_pedagogie']   = False
        ctx['perm_finances']    = False
        ctx['perm_gestion']     = False
        ctx['perm_technique']   = True   # accès Django Admin, paramètres, extra-usage
        ctx['is_admin']         = False
        ctx['is_directeur']     = False
        ctx['is_professeur']    = False
        ctx['is_finances_only'] = False
        return ctx

    user_roles = set(
        request.user.roles.filter(is_active=True).values_list('role', flat=True)
    )

    # ADMIN_GROUPE → sélecteur multi-établissements
    if RoleChoices.ADMIN_GROUPE in user_roles:
        ctx['tous_etablissements'] = list(
            Etablissement.objects.filter(is_active=True).order_by('nom')
        )

    ctx['perm_eleves']    = bool(user_roles & _ROLES_ELEVES)
    ctx['perm_pedagogie'] = bool(user_roles & _ROLES_PEDAGOGIE)
    ctx['perm_finances']  = bool(user_roles & _ROLES_FINANCES)
    ctx['perm_gestion']   = bool(user_roles & _ROLES_GESTION)

    # Compteur de demandes de modification paiement en attente (directeur / préfet)
    _roles_validateurs = {
        RoleChoices.DIRECTEUR, RoleChoices.PREFET,
        RoleChoices.ADMIN_GROUPE, RoleChoices.PRESIDENT_GROUPE, RoleChoices.DIRIGEANT_GROUPE,
    }
    if user_roles & _roles_validateurs:
        etab_id = request.session.get('etablissement_id')
        qs_modif = ModificationPaiement.objects.filter(statut=StatutDemande.EN_ATTENTE)
        qs_insc  = Inscription.objects.filter(statut=StatutInscription.EN_ATTENTE)
        if etab_id:
            qs_modif = qs_modif.filter(paiement__inscription__etablissement_id=etab_id)
            qs_insc  = qs_insc.filter(etablissement_id=etab_id)
        ctx['nb_demandes_paiement_attente'] = qs_modif.count()
        ctx['nb_inscriptions_attente']      = qs_insc.count()
    else:
        ctx['nb_demandes_paiement_attente'] = 0
        ctx['nb_inscriptions_attente']      = 0

    # Flags de rôle individuels utilisés dans les templates pour affiner l'affichage
    _roles_admin = {RoleChoices.ADMIN_GROUPE, RoleChoices.PRESIDENT_GROUPE, RoleChoices.DIRIGEANT_GROUPE}
    ctx['is_admin']      = bool(user_roles & _roles_admin)
    ctx['is_directeur']  = RoleChoices.DIRECTEUR in user_roles
    ctx['is_professeur'] = (
        RoleChoices.PROFESSEUR in user_roles
        and not (user_roles & (_roles_admin | {RoleChoices.DIRECTEUR}))
    )
    # Vrai si l'utilisateur n'a que des rôles financiers (pas pédagogiques)
    ctx['is_finances_only'] = (
        bool(user_roles & {RoleChoices.CAISSIER, RoleChoices.COMPTABLE, RoleChoices.TRESORIER_GROUPE})
        and not bool(user_roles & (_ROLES_ELEVES | _roles_admin | {RoleChoices.DIRECTEUR}))
    )

    return ctx
