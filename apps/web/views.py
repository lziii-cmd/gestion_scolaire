import datetime
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q, Prefetch
from django.http import JsonResponse
from django.utils import timezone

from apps.accounts.models import RoleUtilisateur, RoleChoices, User
from apps.etablissements.models import Etablissement, AnneeScolaire, Cycle
from apps.scolarite.models import Inscription, Eleve, Classe, StatutInscription
from apps.finances.models import (
    Paiement, ClotureCaisse, ModificationPaiement,
    TypeActionPaiement, StatutDemande, StatutPaiement,
    TypeFrais, Frais, Recu, TypeCategorieFrais, StatutCloture,
)
from apps.notifications.models import Notification
from apps.notes.models import ModificationNote, Note, PeriodeEvaluation, StatutNote
from apps.bulletins.models import Bulletin, StatutBulletin
from apps.matieres.models import Matiere, MatiereClasse
from apps.vie_scolaire.models import AbsenceEleve


# ─── DÉCORATEUR DE RÔLE ────────────────────────────────────────────────────────

# Groupes de rôles — cohérents avec context_processors.py
_ROLES_ELEVES    = {RoleChoices.ADMIN_GROUPE, RoleChoices.PRESIDENT_GROUPE,
                    RoleChoices.DIRIGEANT_GROUPE, RoleChoices.DIRECTEUR,
                    RoleChoices.PREFET, RoleChoices.SURVEILLANT, RoleChoices.PROFESSEUR}

_ROLES_PEDAGOGIE = {RoleChoices.ADMIN_GROUPE, RoleChoices.PRESIDENT_GROUPE,
                    RoleChoices.DIRIGEANT_GROUPE, RoleChoices.DIRECTEUR,
                    RoleChoices.PREFET, RoleChoices.SURVEILLANT, RoleChoices.PROFESSEUR}

_ROLES_FINANCES  = {RoleChoices.ADMIN_GROUPE, RoleChoices.PRESIDENT_GROUPE,
                    RoleChoices.DIRIGEANT_GROUPE, RoleChoices.TRESORIER_GROUPE,
                    RoleChoices.DIRECTEUR, RoleChoices.COMPTABLE, RoleChoices.CAISSIER}

_ROLES_GESTION   = {RoleChoices.ADMIN_GROUPE, RoleChoices.DIRECTEUR}


def roles_required(*allowed_roles):
    """
    Décorateur qui vérifie que l'utilisateur possède au moins un des rôles autorisés.
    Les superusers (développeurs) n'ont PAS accès aux vues métier — leur périmètre
    est limité aux pages techniques (Django Admin, paramètres).
    Les utilisateurs refusés sont redirigés vers le dashboard avec un message d'erreur.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            # Superuser = technique uniquement, pas d'accès aux données métier
            if request.user.is_superuser:
                messages.error(request, "Accès refusé : le compte technique n'a pas accès aux données opérationnelles.")
                return redirect('dashboard')
            user_roles = set(
                request.user.roles.filter(is_active=True).values_list('role', flat=True)
            )
            if user_roles & set(allowed_roles):
                return view_func(request, *args, **kwargs)
            messages.error(request, "Accès refusé : vous n'avez pas les droits nécessaires.")
            return redirect('dashboard')
        return _wrapped
    return decorator


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            if user.is_locked():
                messages.error(request, f"Compte bloqué jusqu'à {user.locked_until.strftime('%H:%M')}.")
                return render(request, 'auth/login.html')
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=['failed_login_attempts', 'locked_until'])
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Email ou mot de passe incorrect.")
    return render(request, 'auth/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    user = request.user

    # Superuser = développeur technique : dashboard système uniquement
    if user.is_superuser:
        from django.db import connection as db_conn
        from django.conf import settings
        from django.db.migrations.executor import MigrationExecutor
        from apps.audit.models import JournalAudit, ActionAudit

        # ── Santé DB ──────────────────────────────────────────────
        try:
            db_conn.ensure_connection()
            db_ok = True
        except Exception:
            db_ok = False
        db_engine = db_conn.settings_dict.get('ENGINE', '').split('.')[-1]
        db_name = db_conn.settings_dict.get('NAME', '')
        if hasattr(db_name, 'name'):  # Path object (SQLite)
            db_name = str(db_name).split('/')[-1].split('\\')[-1]

        # ── Migrations ────────────────────────────────────────────
        try:
            executor = MigrationExecutor(db_conn)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            nb_migrations_pending = len(plan)
            nb_migrations_applied = len(executor.loader.applied_migrations)
        except Exception:
            nb_migrations_pending = -1
            nb_migrations_applied = -1

        # ── Volumétrie ────────────────────────────────────────────
        nb_etabs    = Etablissement.objects.count()
        nb_users    = User.objects.filter(is_active=True).count()
        nb_eleves   = Inscription.objects.filter(statut='ACTIF').count()
        nb_notes    = Note.objects.count()
        nb_paiements = Paiement.objects.count()

        # ── Répartition des rôles ─────────────────────────────────
        role_counts = list(
            RoleUtilisateur.objects.filter(is_active=True)
            .values('role').annotate(nb=Count('id')).order_by('-nb')
        )

        # ── Admins groupe existants ───────────────────────────────
        admins_groupe = list(
            User.objects.filter(
                roles__role=RoleChoices.ADMIN_GROUPE, roles__is_active=True
            ).distinct().select_related().order_by('nom')
        )

        # ── Journal d'audit (15 dernières entrées) ─────────────────
        audit_recent = list(
            JournalAudit.objects.select_related('utilisateur')
            .order_by('-date_heure')[:15]
        )

        # ── Dernières connexions ──────────────────────────────────
        derniers_logins = list(
            JournalAudit.objects.filter(action=ActionAudit.LOGIN)
            .select_related('utilisateur').order_by('-date_heure')[:10]
        )

        # ── Création compte ADMIN_GROUPE (POST) ───────────────────
        create_success = request.session.pop('admin_create_success', None)
        create_error   = request.session.pop('admin_create_error',   None)

        if request.method == 'POST' and request.POST.get('action') == 'create_admin':
            email     = request.POST.get('email', '').strip()
            prenom    = request.POST.get('prenom', '').strip()
            nom_field = request.POST.get('nom', '').strip()
            telephone = request.POST.get('telephone', '').strip()
            password  = request.POST.get('password', 'admin1234').strip() or 'admin1234'
            if not (email and prenom and nom_field):
                request.session['admin_create_error'] = "Email, prénom et nom sont obligatoires."
            elif User.objects.filter(email=email).exists():
                request.session['admin_create_error'] = f"Un compte existe déjà pour {email}."
            else:
                new_user = User.objects.create_user(
                    email=email, password=password,
                    prenom=prenom, nom=nom_field, telephone=telephone,
                )
                RoleUtilisateur.objects.create(
                    user=new_user, role=RoleChoices.ADMIN_GROUPE, etablissement=None
                )
                request.session['admin_create_success'] = f"Compte {prenom} {nom_field} ({email}) créé."
            return redirect('dashboard')

        return render(request, 'dashboard/index.html', {
            'is_technique':           True,
            'debug_mode':             settings.DEBUG,
            'db_ok':                  db_ok,
            'db_engine':              db_engine,
            'db_name':                db_name,
            'nb_migrations_applied':  nb_migrations_applied,
            'nb_migrations_pending':  nb_migrations_pending,
            'nb_etabs':               nb_etabs,
            'nb_users':               nb_users,
            'nb_eleves':              nb_eleves,
            'nb_notes':               nb_notes,
            'nb_paiements':           nb_paiements,
            'role_counts':            role_counts,
            'admins_groupe':          admins_groupe,
            'audit_recent':           audit_recent,
            'derniers_logins':        derniers_logins,
            'create_success':         create_success,
            'create_error':           create_error,
            'notifs_non_lues':        Notification.objects.filter(destinataire=user, lue=False).count(),
        })

    etablissement = _get_etablissement(request)
    roles = list(user.roles.filter(is_active=True).values_list('role', flat=True))

    ctx = {
        'etablissement': etablissement,
        'roles': roles,
        'notifs_non_lues': Notification.objects.filter(destinataire=user, lue=False).count(),
        'nb_eleves': 0,
        'nb_classes': 0,
        'nb_modifs_en_attente': 0,
        'nb_bulletins_a_valider': 0,
        'encaisse_aujourd_hui': 0,
        'annee': None,
    }

    today = timezone.localdate()

    if etablissement:
        annee = AnneeScolaire.objects.filter(etablissement=etablissement, is_active=True).first()
        ctx['annee'] = annee

        if annee:
            ctx['nb_eleves'] = Inscription.objects.filter(
                etablissement=etablissement, annee_scolaire=annee, statut='ACTIF'
            ).count()
            ctx['nb_classes'] = Classe.objects.filter(
                etablissement=etablissement, annee_scolaire=annee
            ).count()

        ctx['nb_modifs_en_attente'] = ModificationNote.objects.filter(
            note__inscription__etablissement=etablissement, statut='EN_ATTENTE'
        ).count()

        ctx['nb_bulletins_a_valider'] = Bulletin.objects.filter(
            inscription__etablissement=etablissement, statut=StatutBulletin.BROUILLON
        ).count()

        ctx['encaisse_aujourd_hui'] = Paiement.objects.filter(
            inscription__etablissement=etablissement, date_paiement__date=today
        ).aggregate(t=Sum('montant'))['t'] or 0

    elif _can_switch_etablissement(user):
        # ADMIN_GROUPE en vue globale : stats consolidées tous établissements
        ctx['nb_eleves'] = Inscription.objects.filter(statut='ACTIF').count()
        ctx['nb_classes'] = Classe.objects.filter(annee_scolaire__is_active=True).count()
        ctx['nb_modifs_en_attente'] = ModificationNote.objects.filter(statut='EN_ATTENTE').count()
        ctx['nb_bulletins_a_valider'] = Bulletin.objects.filter(statut=StatutBulletin.BROUILLON).count()
        ctx['encaisse_aujourd_hui'] = Paiement.objects.filter(
            date_paiement__date=today
        ).aggregate(t=Sum('montant'))['t'] or 0
        ctx['is_global'] = True

    return render(request, 'dashboard/index.html', ctx)


# ─── ÉLÈVES ────────────────────────────────────────────────────────────────────

@roles_required(*_ROLES_ELEVES)
def eleves_list(request):
    etablissement = _get_etablissement(request)
    annee = AnneeScolaire.objects.filter(
        etablissement=etablissement, is_active=True
    ).first() if etablissement else None

    selected_cycle_id = request.GET.get('cycle', '')
    selected_classe_id = request.GET.get('classe', '')
    q = request.GET.get('q', '')

    # Niveau 1 : cycles avec comptage
    cycles = []
    if etablissement and annee:
        for cycle in Cycle.objects.filter(etablissement=etablissement, is_active=True).order_by('type_cycle'):
            nb = Inscription.objects.filter(
                etablissement=etablissement, annee_scolaire=annee,
                statut='ACTIF', classe__niveau__cycle=cycle
            ).count()
            nb_classes = Classe.objects.filter(
                etablissement=etablissement, annee_scolaire=annee, niveau__cycle=cycle
            ).count()
            if nb_classes > 0:
                cycles.append({'cycle': cycle, 'nb_eleves': nb, 'nb_classes': nb_classes})

    # Niveau 2 : classes du cycle sélectionné
    classes_du_cycle = []
    if selected_cycle_id and etablissement and annee:
        classes_du_cycle = list(
            Classe.objects.filter(
                etablissement=etablissement,
                annee_scolaire=annee,
                niveau__cycle_id=selected_cycle_id
            ).select_related('niveau').annotate(
                nb_inscrits=Count('inscriptions', filter=Q(inscriptions__statut='ACTIF'))
            ).order_by('niveau__ordre', 'nom')
        )

    # Niveau 3 : élèves de la classe sélectionnée
    page_obj = None
    selected_classe = None
    if selected_classe_id and etablissement:
        try:
            selected_classe = Classe.objects.select_related(
                'niveau', 'niveau__cycle'
            ).get(pk=selected_classe_id, etablissement=etablissement)
            qs = Inscription.objects.select_related(
                'eleve', 'classe', 'classe__niveau'
            ).filter(statut='ACTIF', classe_id=selected_classe_id)
            if q:
                qs = qs.filter(
                    Q(eleve__nom__icontains=q) |
                    Q(eleve__prenom__icontains=q) |
                    Q(eleve__matricule__icontains=q)
                )
            qs = qs.order_by('eleve__nom', 'eleve__prenom')
            paginator = Paginator(qs, 15)
            page_obj = paginator.get_page(request.GET.get('page', 1))
        except Classe.DoesNotExist:
            pass

    is_partial = request.headers.get('HX-Request') or request.GET.get('partial')
    ctx = {
        'cycles': cycles,
        'classes_du_cycle': classes_du_cycle,
        'page_obj': page_obj,
        'selected_classe': selected_classe,
        'selected_cycle_id': selected_cycle_id,
        'selected_classe_id': selected_classe_id,
        'q': q,
        'annee': annee,
        'etablissement': etablissement,
        'notifs_non_lues': Notification.objects.filter(destinataire=request.user, lue=False).count(),
    }

    if is_partial:
        return render(request, 'eleves/_table.html', ctx)
    return render(request, 'eleves/list.html', ctx)


@roles_required(*_ROLES_ELEVES)
def eleve_detail(request, eleve_id):
    etablissement = _get_etablissement(request)
    annee = AnneeScolaire.objects.filter(
        etablissement=etablissement, is_active=True
    ).first() if etablissement else None

    eleve = get_object_or_404(Eleve, pk=eleve_id)
    inscription = Inscription.objects.select_related(
        'classe', 'classe__niveau', 'classe__niveau__cycle', 'annee_scolaire'
    ).filter(eleve=eleve).order_by('-annee_scolaire__date_debut').first()

    notes = Note.objects.select_related(
        'matiere_classe__matiere', 'periode'
    ).filter(inscription__eleve=eleve).order_by('periode__numero', 'matiere_classe__matiere__nom') if inscription else []

    return render(request, 'eleves/detail.html', {
        'eleve': eleve,
        'inscription': inscription,
        'notes': notes,
        'etablissement': etablissement,
        'notifs_non_lues': Notification.objects.filter(destinataire=request.user, lue=False).count(),
    })


# ─── NOTES ─────────────────────────────────────────────────────────────────────

@roles_required(*_ROLES_PEDAGOGIE)
def notes_list(request):
    etablissement = _get_etablissement(request)
    annee = AnneeScolaire.objects.filter(
        etablissement=etablissement, is_active=True
    ).first() if etablissement else None

    active_tab = request.GET.get('tab', 'saisie')
    selected_cycle_id = request.GET.get('cycle', '')
    selected_classe_id = request.GET.get('classe', '')
    selected_mc_id = request.GET.get('mc', '')
    selected_periode_id = request.GET.get('periode', '')

    # Détecter si l'utilisateur est un simple PROFESSEUR (sans rôle admin/directeur)
    user_roles = set(request.user.roles.filter(is_active=True).values_list('role', flat=True))
    _roles_superieurs = {RoleChoices.ADMIN_GROUPE, RoleChoices.PRESIDENT_GROUPE,
                         RoleChoices.DIRIGEANT_GROUPE, RoleChoices.DIRECTEUR,
                         RoleChoices.PREFET, RoleChoices.SURVEILLANT}
    is_simple_prof = (
        not request.user.is_superuser
        and RoleChoices.PROFESSEUR in user_roles
        and not (user_roles & _roles_superieurs)
    )

    # Modifications en attente
    # Un simple professeur ne voit que ses propres demandes
    modifs_qs = ModificationNote.objects.filter(
        note__inscription__etablissement=etablissement, statut='EN_ATTENTE'
    ).select_related(
        'note__inscription__eleve', 'note__matiere_classe__matiere',
        'note__periode', 'modifie_par'
    ) if etablissement else ModificationNote.objects.none()
    if is_simple_prof:
        modifs_qs = modifs_qs.filter(modifie_par=request.user)
    modifs_en_attente = modifs_qs.order_by('-date_modification')
    nb_modifs = modifs_en_attente.count()

    # Classes assignées au professeur (pour le filtrage)
    prof_classes_ids = set()
    if is_simple_prof and etablissement and annee:
        prof_classes_ids = set(
            MatiereClasse.objects.filter(
                professeur=request.user,
                classe__etablissement=etablissement,
                classe__annee_scolaire=annee,
                is_active=True
            ).values_list('classe_id', flat=True)
        )

    # Cycles pour la navigation saisie
    cycles = []
    if etablissement and annee:
        for cycle in Cycle.objects.filter(etablissement=etablissement, is_active=True).order_by('type_cycle'):
            if is_simple_prof:
                nb_classes = Classe.objects.filter(
                    id__in=prof_classes_ids, niveau__cycle=cycle
                ).count()
            else:
                nb_classes = Classe.objects.filter(
                    etablissement=etablissement, annee_scolaire=annee, niveau__cycle=cycle
                ).count()
            if nb_classes > 0:
                cycles.append({'cycle': cycle, 'nb_classes': nb_classes})

    # Classes du cycle sélectionné
    classes_du_cycle = []
    if selected_cycle_id and etablissement and annee:
        qs_classes = Classe.objects.filter(
            etablissement=etablissement,
            annee_scolaire=annee,
            niveau__cycle_id=selected_cycle_id
        ).select_related('niveau').order_by('niveau__ordre', 'nom')
        if is_simple_prof:
            qs_classes = qs_classes.filter(id__in=prof_classes_ids)
        classes_du_cycle = list(qs_classes)

    # Matières et périodes pour la classe sélectionnée
    matieres_classe = []
    periodes = []
    selected_classe = None
    if selected_classe_id and etablissement:
        try:
            selected_classe = Classe.objects.select_related('niveau', 'niveau__cycle').get(
                pk=selected_classe_id, etablissement=etablissement
            )
            # Un professeur ne voit que ses propres matières dans la classe
            mc_qs = MatiereClasse.objects.filter(
                classe=selected_classe, is_active=True
            ).select_related('matiere', 'professeur')
            if is_simple_prof:
                mc_qs = mc_qs.filter(professeur=request.user)
            matieres_classe = list(mc_qs.order_by('matiere__nom'))
            if annee:
                periodes = list(
                    PeriodeEvaluation.objects.filter(
                        etablissement=etablissement, annee_scolaire=annee
                    ).order_by('date_debut')
                )
        except Classe.DoesNotExist:
            pass

    # Grille de saisie
    grille = []
    selected_mc = None
    selected_periode = None
    if selected_classe and selected_mc_id and selected_periode_id:
        try:
            mc_filter = {'pk': selected_mc_id, 'classe': selected_classe}
            if is_simple_prof:
                mc_filter['professeur'] = request.user
            selected_mc = MatiereClasse.objects.select_related('matiere', 'professeur').get(**mc_filter)
            selected_periode = PeriodeEvaluation.objects.get(pk=selected_periode_id)
            inscriptions_qs = Inscription.objects.filter(
                classe=selected_classe, statut='ACTIF'
            ).select_related('eleve').order_by('eleve__nom', 'eleve__prenom')

            notes_map = {
                n.inscription_id: n
                for n in Note.objects.filter(
                    inscription__classe=selected_classe,
                    matiere_classe=selected_mc,
                    periode=selected_periode
                )
            }
            grille = [
                {'inscription': insc, 'note': notes_map.get(insc.id)}
                for insc in inscriptions_qs
            ]
        except (MatiereClasse.DoesNotExist, PeriodeEvaluation.DoesNotExist):
            pass

    # Catalogue des matières
    catalogue = []
    if active_tab == 'catalogue' and etablissement and annee:
        cat_qs = MatiereClasse.objects.filter(
            classe__etablissement=etablissement,
            classe__annee_scolaire=annee,
            is_active=True
        ).select_related('matiere', 'classe', 'classe__niveau', 'professeur')
        if is_simple_prof:
            cat_qs = cat_qs.filter(professeur=request.user)
        catalogue = list(cat_qs.order_by('matiere__nom', 'classe__niveau__ordre', 'classe__nom'))

    return render(request, 'notes/list.html', {
        'active_tab': active_tab,
        'modifs_en_attente': modifs_en_attente,
        'nb_modifs': nb_modifs,
        'cycles': cycles,
        'classes_du_cycle': classes_du_cycle,
        'selected_classe': selected_classe,
        'matieres_classe': matieres_classe,
        'periodes': periodes,
        'grille': grille,
        'selected_mc': selected_mc,
        'selected_periode': selected_periode,
        'selected_cycle_id': selected_cycle_id,
        'selected_classe_id': selected_classe_id,
        'selected_mc_id': selected_mc_id,
        'selected_periode_id': selected_periode_id,
        'catalogue': catalogue,
        'etablissement': etablissement,
        'annee': annee,
        'notifs_non_lues': Notification.objects.filter(destinataire=request.user, lue=False).count(),
    })


@roles_required(*_ROLES_PEDAGOGIE)
def notes_sauvegarder(request):
    """POST : enregistre les notes de la grille de saisie."""
    if request.method != 'POST':
        return redirect('notes_list')

    etablissement = _get_etablissement(request)
    classe_id = request.POST.get('classe_id', '')
    mc_id = request.POST.get('mc_id', '')
    periode_id = request.POST.get('periode_id', '')

    try:
        mc = MatiereClasse.objects.get(pk=mc_id, classe__etablissement=etablissement)
        periode = PeriodeEvaluation.objects.get(pk=periode_id, etablissement=etablissement)

        saved = 0
        for key, val in request.POST.items():
            if not key.startswith('note_'):
                continue
            inscription_id = key[5:]  # remove 'note_'
            val = val.strip().replace(',', '.')
            valeur = None
            if val:
                try:
                    valeur = round(max(0.0, min(20.0, float(val))), 2)
                except ValueError:
                    continue
            try:
                inscription = Inscription.objects.get(pk=inscription_id, classe_id=classe_id)
                note_obj, created = Note.objects.get_or_create(
                    inscription=inscription,
                    matiere_classe=mc,
                    periode=periode,
                    defaults={'valeur': valeur, 'saisi_par': request.user, 'statut': StatutNote.ACTIVE}
                )
                if not created:
                    note_obj.valeur = valeur
                    note_obj.save(update_fields=['valeur'])
                saved += 1
            except Inscription.DoesNotExist:
                continue

        messages.success(request, f"{saved} note(s) enregistrée(s) avec succès.")
    except (MatiereClasse.DoesNotExist, PeriodeEvaluation.DoesNotExist) as e:
        messages.error(request, f"Erreur : configuration introuvable.")

    return redirect(
        f"/notes/?tab=saisie&classe={classe_id}&mc={mc_id}&periode={periode_id}"
    )


# ─── PROFESSEURS ───────────────────────────────────────────────────────────────

@roles_required(*_ROLES_PEDAGOGIE)
def professeurs_list(request):
    etablissement = _get_etablissement(request)
    annee = AnneeScolaire.objects.filter(
        etablissement=etablissement, is_active=True
    ).first() if etablissement else None

    profs = User.objects.filter(
        roles__role=RoleChoices.PROFESSEUR,
        roles__etablissement=etablissement,
        roles__is_active=True
    ).distinct().order_by('nom', 'prenom') if etablissement else []

    profs_data = []
    for prof in profs:
        qs = MatiereClasse.objects.filter(
            professeur=prof,
            classe__etablissement=etablissement,
            is_active=True,
        )
        if annee:
            qs = qs.filter(classe__annee_scolaire=annee)
        qs = qs.select_related('matiere', 'classe', 'classe__niveau')
        matieres_list = list(qs)
        classes_ids = {m.classe_id for m in matieres_list}
        matieres_ids = {m.matiere_id for m in matieres_list}
        profs_data.append({
            'prof': prof,
            'matieres': matieres_list,
            'nb_classes': len(classes_ids),
            'nb_matieres': len(matieres_ids),
        })

    return render(request, 'professeurs/list.html', {
        'profs_data': profs_data,
        'etablissement': etablissement,
        'annee': annee,
        'notifs_non_lues': Notification.objects.filter(destinataire=request.user, lue=False).count(),
    })


# ─── BULLETINS ─────────────────────────────────────────────────────────────────

@roles_required(*_ROLES_PEDAGOGIE)
def bulletins_list(request):
    etablissement = _get_etablissement(request)

    bulletins = Bulletin.objects.select_related(
        'inscription__eleve', 'inscription__classe', 'periode'
    ).filter(inscription__etablissement=etablissement) if etablissement else []

    statut_filter = request.GET.get('statut', '')
    if statut_filter:
        bulletins = bulletins.filter(statut=statut_filter)

    return render(request, 'bulletins/list.html', {
        'bulletins': bulletins.order_by('-periode__date_debut')[:100] if bulletins else [],
        'etablissement': etablissement,
        'statut_filter': statut_filter,
        'notifs_non_lues': Notification.objects.filter(destinataire=request.user, lue=False).count(),
    })


# ─── FINANCES ──────────────────────────────────────────────────────────────────

@roles_required(*_ROLES_FINANCES)
def finances_index(request):
    user = request.user
    etablissement = _get_etablissement(request)
    today = timezone.localdate()

    user_roles = set(user.roles.filter(is_active=True).values_list('role', flat=True))
    _roles_superieurs = {
        RoleChoices.COMPTABLE, RoleChoices.DIRECTEUR,
        RoleChoices.ADMIN_GROUPE, RoleChoices.PRESIDENT_GROUPE, RoleChoices.DIRIGEANT_GROUPE,
    }
    is_caissier_only = (
        RoleChoices.CAISSIER in user_roles
        and not (user_roles & _roles_superieurs)
    )

    base_qs = Paiement.objects.select_related(
        'inscription__eleve', 'frais__type_frais', 'caissier'
    ).filter(inscription__etablissement=etablissement) if etablissement else Paiement.objects.none()

    if is_caissier_only:
        # Caissier : uniquement ses encaissements du jour
        paiements = base_qs.filter(
            caissier=user, date_paiement__date=today
        ).order_by('-date_paiement')

        total_jour = paiements.filter(
            statut=StatutPaiement.VALIDE
        ).aggregate(t=Sum('montant'))['t'] or 0

        nb_paiements_jour = paiements.count()

        # Ses demandes de modification en attente
        mes_demandes = ModificationPaiement.objects.filter(
            demandeur=user, statut=StatutDemande.EN_ATTENTE
        ).select_related('paiement__inscription__eleve').order_by('-date_demande')

        cloture_today = ClotureCaisse.objects.filter(
            etablissement=etablissement, date=today
        ).first() if etablissement else None

        return render(request, 'finances/index.html', {
            'is_caissier_only': True,
            'paiements': paiements,
            'total_jour': total_jour,
            'nb_paiements_jour': nb_paiements_jour,
            'mes_demandes': mes_demandes,
            'cloture_today': cloture_today,
            'etablissement': etablissement,
            'notifs_non_lues': Notification.objects.filter(destinataire=user, lue=False).count(),
        })

    # Comptable / Directeur / Admin : vue globale
    paiements_recents = base_qs.filter(
        statut=StatutPaiement.VALIDE
    ).order_by('-date_paiement')[:30]

    total_mois = base_qs.filter(
        statut=StatutPaiement.VALIDE,
        date_paiement__year=today.year,
        date_paiement__month=today.month,
    ).aggregate(t=Sum('montant'))['t'] or 0

    total_jour = base_qs.filter(
        statut=StatutPaiement.VALIDE,
        date_paiement__date=today,
    ).aggregate(t=Sum('montant'))['t'] or 0

    cloture_today = ClotureCaisse.objects.filter(
        etablissement=etablissement, date=today
    ).first() if etablissement else None

    # Demandes en attente (pour validation)
    demandes_attente = ModificationPaiement.objects.filter(
        paiement__inscription__etablissement=etablissement,
        statut=StatutDemande.EN_ATTENTE,
    ).select_related(
        'paiement__inscription__eleve', 'paiement__frais__type_frais', 'demandeur'
    ).order_by('-date_demande') if etablissement else []

    return render(request, 'finances/index.html', {
        'is_caissier_only': False,
        'paiements_recents': paiements_recents,
        'total_mois': total_mois,
        'total_jour': total_jour,
        'cloture_today': cloture_today,
        'demandes_attente': demandes_attente,
        'nb_demandes_attente': len(demandes_attente),
        'etablissement': etablissement,
        'notifs_non_lues': Notification.objects.filter(destinataire=user, lue=False).count(),
    })


@roles_required(*_ROLES_FINANCES)
def finances_demander_modif(request, paiement_id):
    """Caissier soumet une demande de modification ou d'annulation d'un paiement."""
    user = request.user
    paiement = get_object_or_404(
        Paiement.objects.select_related('inscription__eleve', 'frais__type_frais'),
        pk=paiement_id,
        caissier=user,                        # il ne peut agir que sur ses propres paiements
        statut=StatutPaiement.VALIDE,
    )

    # Bloquer si une demande EN_ATTENTE existe déjà sur ce paiement
    if ModificationPaiement.objects.filter(
        paiement=paiement, statut=StatutDemande.EN_ATTENTE
    ).exists():
        messages.error(request, "Une demande est déjà en attente de validation pour ce paiement.")
        return redirect('finances_index')

    if request.method == 'POST':
        type_action   = request.POST.get('type_action', '')
        motif         = request.POST.get('motif', '').strip()
        nouveau_montant_raw = request.POST.get('nouveau_montant', '').strip()

        if type_action not in (TypeActionPaiement.MODIFICATION, TypeActionPaiement.ANNULATION):
            messages.error(request, "Type d'action invalide.")
            return redirect('finances_index')
        if not motif:
            messages.error(request, "Le motif est obligatoire.")
            return redirect('finances_index')

        nouveau_montant = None
        if type_action == TypeActionPaiement.MODIFICATION:
            try:
                nouveau_montant = float(nouveau_montant_raw.replace(',', '.'))
                if nouveau_montant <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                messages.error(request, "Montant invalide.")
                return redirect('finances_index')

        ModificationPaiement.objects.create(
            paiement=paiement,
            type_action=type_action,
            motif=motif,
            nouveau_montant=nouveau_montant,
            demandeur=user,
        )
        messages.success(request, "Demande envoyée. Le directeur ou le préfet devra la valider.")
        return redirect('finances_index')

    return redirect('finances_index')


@roles_required(RoleChoices.DIRECTEUR, RoleChoices.PREFET,
                RoleChoices.ADMIN_GROUPE, RoleChoices.PRESIDENT_GROUPE, RoleChoices.DIRIGEANT_GROUPE)
def finances_validations(request):
    """Page de validation : demandes paiement + inscriptions EN_ATTENTE."""
    etablissement = _get_etablissement(request)

    demandes = ModificationPaiement.objects.filter(
        paiement__inscription__etablissement=etablissement,
        statut=StatutDemande.EN_ATTENTE,
    ).select_related(
        'paiement__inscription__eleve', 'paiement__frais__type_frais', 'demandeur'
    ).order_by('-date_demande') if etablissement else []

    inscriptions_attente = Inscription.objects.filter(
        etablissement=etablissement,
        statut=StatutInscription.EN_ATTENTE,
    ).select_related('eleve', 'classe', 'inscrit_par').order_by('date_inscription') if etablissement else []

    historique = ModificationPaiement.objects.filter(
        paiement__inscription__etablissement=etablissement,
    ).exclude(statut=StatutDemande.EN_ATTENTE).select_related(
        'paiement__inscription__eleve', 'demandeur', 'validateur'
    ).order_by('-date_validation')[:20] if etablissement else []

    return render(request, 'finances/validations.html', {
        'demandes': demandes,
        'inscriptions_attente': inscriptions_attente,
        'historique': historique,
        'etablissement': etablissement,
        'notifs_non_lues': Notification.objects.filter(destinataire=request.user, lue=False).count(),
    })


@roles_required(RoleChoices.DIRECTEUR, RoleChoices.PREFET,
                RoleChoices.ADMIN_GROUPE, RoleChoices.PRESIDENT_GROUPE, RoleChoices.DIRIGEANT_GROUPE)
def finances_valider(request, demande_id):
    """Directeur / préfet approuve ou rejette une demande."""
    if request.method != 'POST':
        return redirect('finances_validations')

    demande = get_object_or_404(
        ModificationPaiement, pk=demande_id, statut=StatutDemande.EN_ATTENTE
    )
    decision = request.POST.get('decision', '')
    commentaire = request.POST.get('commentaire', '').strip()

    if decision not in ('APPROUVER', 'REJETER'):
        messages.error(request, "Décision invalide.")
        return redirect('finances_validations')

    now = timezone.now()
    demande.validateur    = request.user
    demande.date_validation = now
    demande.commentaire_validateur = commentaire

    if decision == 'APPROUVER':
        demande.statut = StatutDemande.APPROUVEE
        demande.save()

        paiement = demande.paiement
        if demande.type_action == TypeActionPaiement.ANNULATION:
            paiement.statut = StatutPaiement.ANNULE
            paiement.save(update_fields=['statut'])
            messages.success(request, f"Paiement annulé avec succès.")
        elif demande.type_action == TypeActionPaiement.MODIFICATION:
            paiement.montant = demande.nouveau_montant
            paiement.save(update_fields=['montant'])
            messages.success(request, f"Montant mis à jour : {demande.nouveau_montant} FCFA.")
    else:
        demande.statut = StatutDemande.REJETEE
        demande.save()
        messages.warning(request, "Demande rejetée.")

    return redirect('finances_validations')


# ─── INSCRIPTION PAR LE CAISSIER ───────────────────────────────────────────────

_ROLES_CAISSIER_INSCRIPTION = {
    RoleChoices.CAISSIER, RoleChoices.DIRECTEUR,
    RoleChoices.ADMIN_GROUPE, RoleChoices.PRESIDENT_GROUPE, RoleChoices.DIRIGEANT_GROUPE,
}

@roles_required(*_ROLES_CAISSIER_INSCRIPTION)
def inscription_caissier(request):
    """
    Formulaire d'inscription d'un nouvel élève par le caissier.
    Étapes intégrées dans une seule page :
      1. Recherche ou création de l'élève
      2. Choix de la classe
      3. Frais et encaissement (optionnel à ce stade)
    L'inscription est créée avec statut EN_ATTENTE — le directeur/préfet active.
    """
    from apps.finances.models import TypeFrais, Frais
    user = request.user
    etablissement = _get_etablissement(request)

    if not etablissement:
        messages.error(request, "Veuillez sélectionner un établissement.")
        return redirect('dashboard')

    annee = AnneeScolaire.objects.filter(etablissement=etablissement, is_active=True).first()
    if not annee:
        messages.error(request, "Aucune année scolaire active pour cet établissement.")
        return redirect('finances_index')

    classes = Classe.objects.filter(
        etablissement=etablissement, annee_scolaire=annee
    ).select_related('niveau', 'niveau__cycle').order_by('niveau__ordre', 'nom')

    types_frais = TypeFrais.objects.filter(
        etablissement=etablissement, is_active=True
    ).order_by('libelle')

    # Résultat recherche élève (HTMX ou GET)
    q_eleve = request.GET.get('q_eleve', '').strip()
    eleves_trouves = []
    if q_eleve:
        eleves_trouves = list(
            Eleve.objects.filter(
                Q(nom__icontains=q_eleve) |
                Q(prenom__icontains=q_eleve) |
                Q(matricule__icontains=q_eleve)
            ).order_by('nom', 'prenom')[:10]
        )

    if request.method == 'POST':
        action = request.POST.get('action', '')

        # ── Créer nouvel élève ─────────────────────────────────────────
        if action == 'creer_eleve':
            nom        = request.POST.get('nom', '').strip().upper()
            prenom     = request.POST.get('prenom', '').strip().title()
            date_naiss = request.POST.get('date_naissance', '').strip() or None
            lieu_naiss = request.POST.get('lieu_naissance', '').strip()
            sexe       = request.POST.get('sexe', 'M')

            if not (nom and prenom):
                messages.error(request, "Nom et prénom sont obligatoires.")
            else:
                eleve = Eleve.objects.create(
                    nom=nom, prenom=prenom,
                    date_naissance=date_naiss,
                    lieu_naissance=lieu_naiss,
                    sexe=sexe,
                )
                messages.success(request, f"Élève {eleve.nom_complet} créé (matricule : {eleve.matricule}).")
                return redirect(f"{request.path}?eleve_id={eleve.id}")

        # ── Inscrire un élève existant ou nouveau ──────────────────────
        elif action == 'inscrire':
            eleve_id    = request.POST.get('eleve_id', '')
            classe_id   = request.POST.get('classe_id', '')
            type_frais_id = request.POST.get('type_frais_id', '')
            montant_raw = request.POST.get('montant', '').strip()
            observation = request.POST.get('observation', '').strip()

            erreurs = []
            if not eleve_id:
                erreurs.append("Veuillez sélectionner un élève.")
            if not classe_id:
                erreurs.append("Veuillez sélectionner une classe.")

            eleve = None
            classe = None
            if eleve_id:
                try:
                    eleve = Eleve.objects.get(pk=eleve_id)
                except Eleve.DoesNotExist:
                    erreurs.append("Élève introuvable.")
            if classe_id:
                try:
                    classe = Classe.objects.select_related('niveau').get(
                        pk=classe_id, etablissement=etablissement
                    )
                except Classe.DoesNotExist:
                    erreurs.append("Classe invalide.")

            if not erreurs and eleve and classe:
                # Vérifier doublon
                if Inscription.objects.filter(
                    eleve=eleve, annee_scolaire=annee, etablissement=etablissement
                ).exists():
                    erreurs.append(
                        f"{eleve.nom_complet} est déjà inscrit(e) dans cet établissement "
                        f"pour cette année scolaire."
                    )

            if erreurs:
                for e in erreurs:
                    messages.error(request, e)
            else:
                # Créer l'inscription EN_ATTENTE
                inscription = Inscription.objects.create(
                    eleve=eleve,
                    classe=classe,
                    annee_scolaire=annee,
                    etablissement=etablissement,
                    statut=StatutInscription.EN_ATTENTE,
                    inscrit_par=user,
                )

                # Créer les frais et le paiement si montant saisi
                if type_frais_id and montant_raw:
                    try:
                        montant = float(montant_raw.replace(',', '.'))
                        type_frais = TypeFrais.objects.get(pk=type_frais_id, etablissement=etablissement)
                        frais, _ = Frais.objects.get_or_create(
                            inscription=inscription,
                            type_frais=type_frais,
                            defaults={'montant': type_frais.montant_defaut, 'created_by': user},
                        )
                        if montant > 0:
                            from apps.finances.models import Paiement as Pmt
                            Pmt.objects.create(
                                inscription=inscription,
                                frais=frais,
                                montant=montant,
                                caissier=user,
                                observation=observation,
                            )
                    except (ValueError, TypeFrais.DoesNotExist):
                        messages.warning(request, "Frais non enregistrés (données invalides).")

                messages.success(
                    request,
                    f"Inscription de {eleve.nom_complet} en {classe.nom} soumise. "
                    f"En attente de validation par le directeur."
                )
                return redirect('inscription_caissier')

    # Élève pré-sélectionné depuis la recherche
    eleve_selectionne = None
    eleve_id_param = request.GET.get('eleve_id', '')
    if eleve_id_param:
        try:
            eleve_selectionne = Eleve.objects.get(pk=eleve_id_param)
        except Eleve.DoesNotExist:
            pass

    # Mes inscriptions récentes (EN_ATTENTE ou ACTIF créées par moi aujourd'hui)
    mes_inscriptions = Inscription.objects.filter(
        inscrit_par=user,
        etablissement=etablissement,
    ).select_related('eleve', 'classe').order_by('-date_inscription')[:10]

    cycles = Cycle.objects.filter(etablissement=etablissement).order_by('type_cycle') if etablissement else []

    return render(request, 'scolarite/inscription_caissier.html', {
        'etablissement': etablissement,
        'annee': annee,
        'classes': classes,
        'cycles': cycles,
        'types_frais': types_frais,
        'q_eleve': q_eleve,
        'eleves_trouves': eleves_trouves,
        'eleve_selectionne': eleve_selectionne,
        'mes_inscriptions': mes_inscriptions,
        'notifs_non_lues': Notification.objects.filter(destinataire=user, lue=False).count(),
    })


@roles_required(RoleChoices.DIRECTEUR, RoleChoices.PREFET,
                RoleChoices.ADMIN_GROUPE, RoleChoices.PRESIDENT_GROUPE, RoleChoices.DIRIGEANT_GROUPE)
def inscription_valider(request, inscription_id):
    """Directeur / préfet active ou rejette une inscription EN_ATTENTE."""
    if request.method != 'POST':
        return redirect('finances_validations')

    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe'),
        pk=inscription_id,
        statut=StatutInscription.EN_ATTENTE,
    )
    decision    = request.POST.get('decision', '')
    motif_rejet = request.POST.get('motif_rejet', '').strip()

    if decision not in ('ACTIVER', 'REJETER'):
        messages.error(request, "Décision invalide.")
        return redirect('finances_validations')

    now = timezone.now()
    inscription.valide_par     = request.user
    inscription.date_validation = now

    if decision == 'ACTIVER':
        inscription.statut = StatutInscription.ACTIF
        inscription.save(update_fields=['statut', 'valide_par', 'date_validation'])
        messages.success(
            request,
            f"Inscription de {inscription.eleve.nom_complet} en {inscription.classe.nom} activée."
        )
    else:
        inscription.statut      = StatutInscription.REJETE
        inscription.motif_rejet = motif_rejet
        inscription.save(update_fields=['statut', 'valide_par', 'date_validation', 'motif_rejet'])
        messages.warning(request, f"Inscription de {inscription.eleve.nom_complet} rejetée.")

    return redirect('finances_validations')


# ─── ENCAISSEMENT ──────────────────────────────────────────────────────────────

# Mois scolaires Oct → Jul
_MOIS_SCOLAIRES = [
    (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre'),
    (1,  'Janvier'),  (2,  'Février'),  (3,  'Mars'),
    (4,  'Avril'),    (5,  'Mai'),      (6,  'Juin'),   (7, 'Juillet'),
]



@roles_required(*_ROLES_FINANCES)
def encaisser_paiement(request):
    """
    Page d'encaissement :
    - GET sans params : formulaire de recherche d'élève
    - GET ?inscription_id=X : situation financière de l'élève
    - POST : crée le paiement + reçu
    """
    user = request.user
    etablissement = _get_etablissement(request)
    if not etablissement:
        messages.error(request, "Veuillez sélectionner un établissement.")
        return redirect('dashboard')

    annee = AnneeScolaire.objects.filter(etablissement=etablissement, is_active=True).first()

    # ── Recherche élève ───────────────────────────────────────────────────────
    q = request.GET.get('q', '').strip()
    eleves_trouves = []
    if q:
        eleves_trouves = list(
            Eleve.objects.filter(
                Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(matricule__icontains=q)
            ).order_by('nom', 'prenom')[:10]
        )

    # ── Situation financière d'une inscription ───────────────────────────────
    inscription = None
    frais_data = []
    total_annuel = 0
    total_paye = 0

    inscription_id = request.GET.get('inscription_id') or request.POST.get('inscription_id')
    if inscription_id:
        try:
            inscription = Inscription.objects.select_related(
                'eleve', 'classe', 'classe__niveau', 'annee_scolaire'
            ).get(pk=inscription_id, etablissement=etablissement, statut=StatutInscription.ACTIF)
        except Inscription.DoesNotExist:
            messages.error(request, "Inscription introuvable ou non active.")

    if inscription:
        # Récupère ou crée les frais standards depuis les TypeFrais actifs pour ce niveau
        types_actifs = TypeFrais.objects.filter(
            etablissement=etablissement, is_active=True
        ).filter(
            Q(niveau=inscription.classe.niveau) | Q(niveau__isnull=True)
        )
        if annee:
            types_actifs = types_actifs.filter(
                Q(annee_scolaire=annee) | Q(annee_scolaire__isnull=True)
            )

        for tf in types_actifs.order_by('categorie', 'libelle'):
            frais, _ = Frais.objects.get_or_create(
                inscription=inscription,
                type_frais=tf,
                defaults={
                    'montant': tf.montant_defaut,
                    'created_by': user,
                },
            )
            paye = frais.paiements.filter(statut=StatutPaiement.VALIDE).aggregate(t=Sum('montant'))['t'] or 0
            solde = frais.montant - paye
            frais_data.append({
                'frais': frais,
                'type_frais': tf,
                'paye': paye,
                'solde': solde,
                'solde_positif': solde > 0,
            })
            total_annuel += frais.montant
            total_paye += paye

    # ── POST : créer le(s) paiement(s) ──────────────────────────────────────
    if request.method == 'POST' and inscription:
        observation = request.POST.get('observation', '').strip()

        # Multi-select
        frais_ids = request.POST.getlist('frais_ids')
        if frais_ids:
            total_paid = 0
            nb_paid = 0
            last_recu = None
            for fid in frais_ids:
                try:
                    frais_obj = Frais.objects.get(pk=fid, inscription=inscription)
                    paye = frais_obj.paiements.filter(statut=StatutPaiement.VALIDE).aggregate(t=Sum('montant'))['t'] or 0
                    solde = frais_obj.montant - paye
                    if solde > 0:
                        paiement = Paiement.objects.create(
                            inscription=inscription,
                            frais=frais_obj,
                            montant=solde,
                            caissier=user,
                            observation=observation,
                            statut=StatutPaiement.VALIDE,
                        )
                        last_recu = Recu.objects.create(paiement=paiement)
                        total_paid += solde
                        nb_paid += 1
                except (Frais.DoesNotExist, Exception):
                    pass
            if nb_paid:
                messages.success(request, f"{nb_paid} paiement(s) enregistré(s) — {total_paid:,.0f} FCFA.")
            return redirect(f"{request.path}?inscription_id={inscription.id}")

        # Paiement simple
        frais_id    = request.POST.get('frais_id', '')
        montant_raw = request.POST.get('montant', '').strip().replace(',', '.')

        try:
            frais_obj = Frais.objects.get(pk=frais_id, inscription=inscription)
            montant = float(montant_raw)
            if montant <= 0:
                raise ValueError
        except (ValueError, TypeError, Frais.DoesNotExist):
            messages.error(request, "Montant ou frais invalide.")
            return redirect(f"{request.path}?inscription_id={inscription.id}")

        paiement = Paiement.objects.create(
            inscription=inscription,
            frais=frais_obj,
            montant=montant,
            caissier=user,
            observation=observation,
            statut=StatutPaiement.VALIDE,
        )
        recu = Recu.objects.create(paiement=paiement)
        messages.success(request, f"Paiement de {montant:,.0f} FCFA enregistré.")
        return redirect('recu_print', recu_id=recu.id)

    return render(request, 'finances/encaisser.html', {
        'etablissement': etablissement,
        'annee': annee,
        'q': q,
        'eleves_trouves': eleves_trouves,
        'inscription': inscription,
        'frais_data': frais_data,
        'total_annuel': total_annuel,
        'total_paye': total_paye,
        'total_solde': total_annuel - total_paye,
        'notifs_non_lues': Notification.objects.filter(destinataire=user, lue=False).count(),
    })


@roles_required(*_ROLES_FINANCES)
def recu_print(request, recu_id):
    """Page d'impression du reçu (standalone, sans base.html)."""
    user = request.user
    etablissement = _get_etablissement(request)

    user_roles = set(user.roles.filter(is_active=True).values_list('role', flat=True))
    _roles_superieurs = {
        RoleChoices.COMPTABLE, RoleChoices.DIRECTEUR,
        RoleChoices.ADMIN_GROUPE, RoleChoices.PRESIDENT_GROUPE, RoleChoices.DIRIGEANT_GROUPE,
    }
    is_caissier_only = RoleChoices.CAISSIER in user_roles and not (user_roles & _roles_superieurs)

    if is_caissier_only:
        recu = get_object_or_404(
            Recu.objects.select_related(
                'paiement__inscription__eleve', 'paiement__inscription__classe',
                'paiement__frais__type_frais', 'paiement__caissier',
            ),
            pk=recu_id,
            paiement__caissier=user,
        )
    else:
        recu = get_object_or_404(
            Recu.objects.select_related(
                'paiement__inscription__eleve', 'paiement__inscription__classe',
                'paiement__frais__type_frais', 'paiement__caissier',
            ),
            pk=recu_id,
            paiement__inscription__etablissement=etablissement,
        )

    return render(request, 'finances/recu.html', {
        'recu': recu,
        'paiement': recu.paiement,
        'etablissement': recu.paiement.inscription.etablissement,
    })


# ─── ABSENCES ──────────────────────────────────────────────────────────────────

@roles_required(*_ROLES_PEDAGOGIE)
def absences_list(request):
    etablissement = _get_etablissement(request)
    annee = AnneeScolaire.objects.filter(
        etablissement=etablissement, is_active=True
    ).first() if etablissement else None

    selected_cycle_id = request.GET.get('cycle', '')
    selected_classe_id = request.GET.get('classe', '')
    date_filter = request.GET.get('date', '')

    cycles = []
    if etablissement and annee:
        for cycle in Cycle.objects.filter(etablissement=etablissement, is_active=True).order_by('type_cycle'):
            nb_classes = Classe.objects.filter(
                etablissement=etablissement, annee_scolaire=annee, niveau__cycle=cycle
            ).count()
            if nb_classes > 0:
                cycles.append({'cycle': cycle, 'nb_classes': nb_classes})

    classes_du_cycle = []
    if selected_cycle_id and etablissement and annee:
        classes_du_cycle = list(
            Classe.objects.filter(
                etablissement=etablissement,
                annee_scolaire=annee,
                niveau__cycle_id=selected_cycle_id
            ).select_related('niveau').order_by('niveau__ordre', 'nom')
        )

    absences = []
    selected_classe = None
    nb_total = nb_justifiees = nb_non_justifiees = 0

    if selected_classe_id and etablissement:
        try:
            selected_classe = Classe.objects.select_related('niveau', 'niveau__cycle').get(
                pk=selected_classe_id, etablissement=etablissement
            )
            qs = AbsenceEleve.objects.select_related(
                'inscription__eleve', 'enregistre_par'
            ).filter(inscription__classe=selected_classe)
            if date_filter:
                qs = qs.filter(date=date_filter)
            absences = list(qs.order_by('-date', 'inscription__eleve__nom'))
            nb_total = len(absences)
            nb_justifiees = sum(1 for a in absences if a.justifiee)
            nb_non_justifiees = nb_total - nb_justifiees
        except Classe.DoesNotExist:
            pass

    return render(request, 'absences/list.html', {
        'cycles': cycles,
        'classes_du_cycle': classes_du_cycle,
        'selected_classe': selected_classe,
        'selected_cycle_id': selected_cycle_id,
        'selected_classe_id': selected_classe_id,
        'date_filter': date_filter,
        'absences': absences,
        'nb_total': nb_total,
        'nb_justifiees': nb_justifiees,
        'nb_non_justifiees': nb_non_justifiees,
        'etablissement': etablissement,
        'annee': annee,
        'notifs_non_lues': Notification.objects.filter(destinataire=request.user, lue=False).count(),
    })


# ─── EMPLOI DU TEMPS ───────────────────────────────────────────────────────────

@roles_required(*_ROLES_PEDAGOGIE)
def emploi_du_temps(request):
    etablissement = _get_etablissement(request)
    annee = AnneeScolaire.objects.filter(
        etablissement=etablissement, is_active=True
    ).first() if etablissement else None

    selected_classe_id = request.GET.get('classe', '')
    classes = []
    if etablissement and annee:
        classes = list(
            Classe.objects.filter(
                etablissement=etablissement, annee_scolaire=annee
            ).select_related('niveau', 'niveau__cycle').order_by('niveau__ordre', 'nom')
        )

    jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
    heures = ['08:00', '09:00', '10:00', '11:00', '12:00', '14:00', '15:00', '16:00', '17:00']

    return render(request, 'edt/list.html', {
        'classes': classes,
        'selected_classe_id': selected_classe_id,
        'jours': jours,
        'heures': heures,
        'etablissement': etablissement,
        'annee': annee,
        'notifs_non_lues': Notification.objects.filter(destinataire=request.user, lue=False).count(),
    })


# ─── NOTIFICATIONS ─────────────────────────────────────────────────────────────

@login_required
def notifications_list(request):
    # Marquer toutes comme lues si demandé
    if request.POST.get('action') == 'marquer_tout_lu':
        Notification.objects.filter(destinataire=request.user, lue=False).update(lue=True)
        return redirect('notifications_list')

    notifs = Notification.objects.filter(destinataire=request.user).order_by('-created_at')
    non_lues = notifs.filter(lue=False)
    lues = notifs.filter(lue=True)
    return render(request, 'notifications/list.html', {
        'non_lues': non_lues,
        'lues': lues,
        'notifs_non_lues': non_lues.count(),
    })


@login_required
def notification_marquer_lu(request, notif_id):
    notif = get_object_or_404(Notification, pk=notif_id, destinataire=request.user)
    notif.lue = True
    notif.save(update_fields=['lue'])
    next_url = request.GET.get('next', 'notifications_list')
    return redirect(next_url)


# ─── CAISSE — OUVERTURE / FERMETURE ────────────────────────────────────────────

@roles_required(*_ROLES_FINANCES)
def caisse_toggle(request):
    """Ouvrir ou fermer la caisse avec vérification du code PIN."""
    if request.method != 'POST':
        return redirect('finances_index')

    user = request.user
    etablissement = _get_etablissement(request)
    if not etablissement:
        return redirect('finances_index')

    today = timezone.localdate()
    action = request.POST.get('action', 'ouvrir')

    if action == 'ouvrir':
        pin = request.POST.get('pin', '')
        if not user.check_pin_caisse(pin):
            messages.error(request, "Code PIN incorrect. Veuillez réessayer.")
            return redirect('finances_index')

        cloture, created = ClotureCaisse.objects.get_or_create(
            etablissement=etablissement,
            date=today,
            defaults={'caissier': user, 'statut': StatutCloture.OUVERTE, 'total_encaisse': 0}
        )
        if not created and cloture.statut == StatutCloture.CLOTUREE:
            cloture.statut = StatutCloture.OUVERTE
            cloture.save(update_fields=['statut'])

        request.session['caisse_unlocked'] = True
        messages.success(request, "Caisse ouverte. Bonne journée !")

    elif action == 'fermer':
        cloture = ClotureCaisse.objects.filter(
            etablissement=etablissement, date=today
        ).first()
        if cloture and cloture.statut == StatutCloture.OUVERTE:
            total = Paiement.objects.filter(
                inscription__etablissement=etablissement,
                caissier=user,
                date_paiement__date=today,
                statut=StatutPaiement.VALIDE,
            ).aggregate(t=Sum('montant'))['t'] or 0
            cloture.total_encaisse = total
            cloture.statut = StatutCloture.CLOTUREE
            cloture.cloture_at = timezone.now()
            cloture.save()

        request.session.pop('caisse_unlocked', None)
        messages.success(request, "Caisse fermée.")

    return redirect('finances_index')


# ─── REÇUS ÉLÈVE ───────────────────────────────────────────────────────────────

@roles_required(*_ROLES_FINANCES)
def recus_eleve(request):
    """Tous les reçus d'un élève pour une année scolaire donnée."""
    etablissement = _get_etablissement(request)
    annees = AnneeScolaire.objects.filter(
        etablissement=etablissement
    ).order_by('-date_debut') if etablissement else []

    eleve_id = request.GET.get('eleve_id', '')
    annee_id = request.GET.get('annee_id', '')
    q = request.GET.get('q', '').strip()

    eleve = None
    recus = []
    eleves_result = []

    if eleve_id:
        try:
            eleve = Eleve.objects.get(pk=eleve_id)
        except Eleve.DoesNotExist:
            pass

    if q:
        eleves_result = list(
            Eleve.objects.filter(
                Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(matricule__icontains=q),
                inscriptions__etablissement=etablissement,
            ).order_by('nom', 'prenom').distinct()[:10]
        )

    if eleve and annee_id:
        recus = list(Recu.objects.filter(
            paiement__inscription__eleve=eleve,
            paiement__inscription__etablissement=etablissement,
            paiement__inscription__annee_scolaire_id=annee_id,
            paiement__statut=StatutPaiement.VALIDE,
        ).select_related(
            'paiement__frais__type_frais',
            'paiement__inscription__classe',
            'paiement__caissier',
        ).order_by('-date_generation'))

    total_recus = sum(r.paiement.montant for r in recus)

    return render(request, 'finances/recus_eleve.html', {
        'etablissement': etablissement,
        'annees': annees,
        'eleve': eleve,
        'annee_id': annee_id,
        'recus': recus,
        'total_recus': total_recus,
        'q': q,
        'eleves_result': eleves_result,
        'notifs_non_lues': Notification.objects.filter(destinataire=request.user, lue=False).count(),
    })


# ─── AUTOCOMPLETE JSON ──────────────────────────────────────────────────────────

@login_required
def eleve_search_json(request):
    """JSON: autocomplete élève — exclut les déjà inscrits cette année."""
    q = request.GET.get('q', '').strip()
    etablissement = _get_etablissement(request)

    if not q or len(q) < 2:
        return JsonResponse({'results': []})

    annee = AnneeScolaire.objects.filter(
        etablissement=etablissement, is_active=True
    ).first() if etablissement else None

    enrolled_ids = set(
        Inscription.objects.filter(
            etablissement=etablissement, annee_scolaire=annee
        ).values_list('eleve_id', flat=True)
    ) if annee else set()

    # Multi-mots : chaque mot filtré sur nom ou prénom
    words = q.split()
    qs = Eleve.objects.exclude(id__in=enrolled_ids)
    for w in words:
        qs = qs.filter(Q(nom__icontains=w) | Q(prenom__icontains=w) | Q(matricule__icontains=w))
    qs = qs.order_by('nom', 'prenom')[:10]

    results = []
    for e in list(qs):
        last_insc = e.inscriptions.order_by('-date_inscription').first()
        results.append({
            'id': e.id,
            'nom': e.nom,
            'prenom': e.prenom,
            'matricule': e.matricule,
            'last_classe': last_insc.classe.nom if last_insc else '',
            'initials': f"{e.prenom[0].upper()}{e.nom[0].upper()}",
        })

    return JsonResponse({'results': results})


@login_required
def classes_par_cycle_json(request):
    """JSON: classes filtrées par cycle."""
    etablissement = _get_etablissement(request)
    cycle_type = request.GET.get('cycle', '')
    annee = AnneeScolaire.objects.filter(
        etablissement=etablissement, is_active=True
    ).first() if etablissement else None

    qs = Classe.objects.filter(
        etablissement=etablissement, annee_scolaire=annee
    ).select_related('niveau', 'niveau__cycle').order_by('niveau__ordre', 'nom')

    if cycle_type:
        qs = qs.filter(niveau__cycle__type_cycle=cycle_type)

    return JsonResponse({
        'classes': [{'id': c.id, 'nom': c.nom, 'niveau': c.niveau.nom} for c in qs]
    })


# ─── HELPERS ───────────────────────────────────────────────────────────────────

def _can_switch_etablissement(user):
    """Retourne True si l'utilisateur peut naviguer entre établissements."""
    if user.is_superuser:
        return True
    return user.roles.filter(role=RoleChoices.ADMIN_GROUPE, is_active=True).exists()


def _get_etablissement(request):
    """
    Retourne l'établissement actif pour la requête.

    - is_superuser / ADMIN_GROUPE : peuvent choisir via session (vue globale si None)
    - DIRECTEUR et tous autres rôles : verrouillés sur leur établissement
    """
    user = request.user

    if _can_switch_etablissement(user):
        # Ces utilisateurs peuvent être en "vue globale" (None) ou avoir choisi un étab
        etab_id = request.session.get('etablissement_id')
        if etab_id:
            try:
                return Etablissement.objects.get(pk=etab_id, is_active=True)
            except Etablissement.DoesNotExist:
                request.session.pop('etablissement_id', None)
        return None

    # Tous les autres rôles : verrouillés sur leur établissement
    etab_id = request.session.get('etablissement_id')
    if etab_id:
        # Vérifier que l'utilisateur a bien accès à cet établissement
        role = user.roles.filter(is_active=True, etablissement_id=etab_id).first()
        if role:
            return role.etablissement

    # Fallback : premier établissement assigné
    role = user.roles.filter(is_active=True, etablissement__isnull=False).first()
    if role:
        request.session['etablissement_id'] = role.etablissement_id
        return role.etablissement
    return None


@login_required
def reset_etablissement(request):
    """Remet l'admin groupe/superuser en vue globale (supprime l'étab de la session)."""
    if not _can_switch_etablissement(request.user):
        return redirect('dashboard')
    request.session.pop('etablissement_id', None)
    return redirect('dashboard')


@login_required
def mon_profil(request):
    user = request.user
    roles = user.roles.filter(is_active=True).select_related('etablissement').order_by('etablissement__nom')
    return render(request, 'profil/index.html', {
        'etablissement': _get_etablissement(request),
        'roles': roles,
        'notifs_non_lues': Notification.objects.filter(destinataire=user, lue=False).count(),
    })


@login_required
def parametres(request):
    user = request.user
    saved = False
    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        prenom = request.POST.get('prenom', '').strip()
        telephone = request.POST.get('telephone', '').strip()
        if nom and prenom:
            user.nom = nom
            user.prenom = prenom
            user.telephone = telephone
            user.save(update_fields=['nom', 'prenom', 'telephone'])
            messages.success(request, 'Informations mises à jour avec succès.')
            saved = True

        new_pw = request.POST.get('new_password', '').strip()
        confirm_pw = request.POST.get('confirm_password', '').strip()
        if new_pw:
            if new_pw == confirm_pw and len(new_pw) >= 8:
                user.set_password(new_pw)
                user.save()
                login(request, user)
                messages.success(request, 'Mot de passe modifié avec succès.')
            else:
                messages.error(request, 'Mot de passe invalide (8 caractères min, confirmation identique).')

        return redirect('parametres')

    return render(request, 'parametres/index.html', {
        'etablissement': _get_etablissement(request),
        'notifs_non_lues': Notification.objects.filter(destinataire=user, lue=False).count(),
    })


@login_required
def changer_etablissement(request, etab_id):
    if not _can_switch_etablissement(request.user):
        return redirect('dashboard')
    try:
        etab = Etablissement.objects.get(pk=etab_id, is_active=True)
        request.session['etablissement_id'] = etab.id
    except Etablissement.DoesNotExist:
        pass
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


# ─── PAGE DE DÉVELOPPEMENT : liste des comptes ─────────────────────────────────

def extra_usage(request):
    """Page non protégée listant tous les comptes de test (dev only)."""
    from apps.scolarite.models import Eleve

    etablissements = Etablissement.objects.filter(is_active=True).order_by('nom')

    ROLES_STAFF = {
        RoleChoices.DIRECTEUR, RoleChoices.PREFET, RoleChoices.COMPTABLE,
        RoleChoices.CAISSIER, RoleChoices.SURVEILLANT, RoleChoices.PROFESSEUR,
        RoleChoices.ADMIN_GROUPE, RoleChoices.PRESIDENT_GROUPE, RoleChoices.DIRIGEANT_GROUPE,
    }

    # Superadmin
    superadmins = list(User.objects.filter(is_superuser=True).order_by('email'))

    # Staff par étab
    etabs_data = []
    for etab in etablissements:
        staff = []
        seen = set()
        qs = User.objects.filter(
            roles__etablissement=etab,
            roles__is_active=True,
        ).prefetch_related('roles__etablissement').order_by('roles__role', 'email').distinct()
        for u in qs:
            if u.id in seen:
                continue
            seen.add(u.id)
            roles = [r for r in u.roles.filter(is_active=True) if r.role in ROLES_STAFF]
            if roles:
                staff.append({'user': u, 'roles': roles})

        eleves = list(
            Eleve.objects.filter(
                inscriptions__etablissement=etab,
                inscriptions__statut='ACTIF',
            ).select_related('user').prefetch_related('user__roles').order_by('nom', 'prenom').distinct()
        )

        etabs_data.append({'etab': etab, 'staff': staff, 'eleves': eleves})

    return render(request, 'extra_usage.html', {
        'superadmins': superadmins,
        'etabs_data': etabs_data,
        'etablissements': etablissements,
        'mot_de_passe': 'admin1234',
    })
