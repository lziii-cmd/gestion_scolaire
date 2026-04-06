from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone

from apps.accounts.models import RoleUtilisateur, RoleChoices
from apps.etablissements.models import Etablissement, AnneeScolaire
from apps.scolarite.models import Inscription, Eleve, Classe
from apps.finances.models import Paiement, ClotureCaisse
from apps.notifications.models import Notification
from apps.notes.models import ModificationNote
from apps.bulletins.models import Bulletin, StatutBulletin


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
    etablissement = _get_etablissement(request)
    roles = list(user.roles.filter(is_active=True).values_list('role', flat=True))

    ctx = {
        'etablissement': etablissement,
        'roles': roles,
        'notifs_non_lues': Notification.objects.filter(destinataire=user, lue=False).count(),
    }

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
            note__inscription__etablissement=etablissement,
            statut='EN_ATTENTE'
        ).count()

        ctx['nb_bulletins_a_valider'] = Bulletin.objects.filter(
            inscription__etablissement=etablissement,
            statut=StatutBulletin.BROUILLON
        ).count()

        today = timezone.localdate()
        ctx['encaisse_aujourd_hui'] = Paiement.objects.filter(
            inscription__etablissement=etablissement,
            date_paiement__date=today
        ).aggregate(t=Sum('montant'))['t'] or 0

    return render(request, 'dashboard/index.html', ctx)


@login_required
def eleves_list(request):
    etablissement = _get_etablissement(request)
    annee = AnneeScolaire.objects.filter(etablissement=etablissement, is_active=True).first() if etablissement else None

    q = request.GET.get('q', '')
    classe_id = request.GET.get('classe', '')

    inscriptions = Inscription.objects.select_related(
        'eleve', 'classe', 'classe__niveau'
    ).filter(statut='ACTIF')

    if etablissement:
        inscriptions = inscriptions.filter(etablissement=etablissement)
    if annee:
        inscriptions = inscriptions.filter(annee_scolaire=annee)
    if q:
        inscriptions = inscriptions.filter(
            Q(eleve__nom__icontains=q) | Q(eleve__prenom__icontains=q) |
            Q(eleve__matricule__icontains=q)
        )
    if classe_id:
        inscriptions = inscriptions.filter(classe_id=classe_id)

    classes = Classe.objects.filter(etablissement=etablissement, annee_scolaire=annee) if etablissement and annee else []

    return render(request, 'eleves/list.html', {
        'inscriptions': inscriptions.order_by('eleve__nom', 'eleve__prenom'),
        'classes': classes,
        'q': q,
        'classe_id': classe_id,
        'etablissement': etablissement,
        'notifs_non_lues': Notification.objects.filter(destinataire=request.user, lue=False).count(),
    })


@login_required
def notes_list(request):
    etablissement = _get_etablissement(request)
    modifs_en_attente = ModificationNote.objects.filter(
        note__inscription__etablissement=etablissement,
        statut='EN_ATTENTE'
    ).select_related(
        'note__inscription__eleve',
        'note__matiere_classe__matiere',
        'note__periode',
        'modifie_par'
    ).order_by('-date_modification') if etablissement else []

    return render(request, 'notes/list.html', {
        'modifs_en_attente': modifs_en_attente,
        'etablissement': etablissement,
        'notifs_non_lues': Notification.objects.filter(destinataire=request.user, lue=False).count(),
    })


@login_required
def bulletins_list(request):
    etablissement = _get_etablissement(request)
    annee = AnneeScolaire.objects.filter(etablissement=etablissement, is_active=True).first() if etablissement else None

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


@login_required
def finances_index(request):
    etablissement = _get_etablissement(request)
    today = timezone.localdate()

    paiements_recents = Paiement.objects.select_related(
        'inscription__eleve', 'frais__type_frais', 'caissier'
    ).filter(inscription__etablissement=etablissement).order_by('-date_paiement')[:20] if etablissement else []

    total_mois = Paiement.objects.filter(
        inscription__etablissement=etablissement,
        date_paiement__year=today.year,
        date_paiement__month=today.month,
    ).aggregate(t=Sum('montant'))['t'] or 0 if etablissement else 0

    cloture_today = ClotureCaisse.objects.filter(
        etablissement=etablissement, date=today
    ).first() if etablissement else None

    return render(request, 'finances/index.html', {
        'paiements_recents': paiements_recents,
        'total_mois': total_mois,
        'cloture_today': cloture_today,
        'etablissement': etablissement,
        'notifs_non_lues': Notification.objects.filter(destinataire=request.user, lue=False).count(),
    })


@login_required
def notifications_list(request):
    notifs = Notification.objects.filter(destinataire=request.user).order_by('-created_at')
    return render(request, 'notifications/list.html', {
        'notifs': notifs,
        'notifs_non_lues': notifs.filter(lue=False).count(),
    })


def _get_etablissement(request):
    etab_id = request.session.get('etablissement_id')
    if etab_id:
        try:
            return Etablissement.objects.get(pk=etab_id)
        except Etablissement.DoesNotExist:
            pass
    role = request.user.roles.filter(is_active=True, etablissement__isnull=False).first()
    if role:
        request.session['etablissement_id'] = role.etablissement_id
        return role.etablissement
    return None


@login_required
def changer_etablissement(request, etab_id):
    try:
        etab = Etablissement.objects.get(pk=etab_id)
        request.session['etablissement_id'] = etab.id
    except Etablissement.DoesNotExist:
        pass
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
