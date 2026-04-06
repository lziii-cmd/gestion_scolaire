from config.celery import app


@app.task
def generer_pdf_recu(recu_id):
    """Génère le PDF d'un reçu de paiement."""
    from .models import Recu
    try:
        recu = Recu.objects.select_related(
            'paiement__inscription__eleve',
            'paiement__inscription__etablissement',
            'paiement__frais__type_frais',
        ).get(pk=recu_id)
    except Recu.DoesNotExist:
        return
    # TODO: Générer PDF et sauvegarder recu.pdf


@app.task
def verifier_clotures_oubliees():
    """
    Tâche planifiée quotidiennement : vérifie les établissements
    sans clôture du jour et envoie des notifications.
    """
    from django.utils.timezone import localdate
    from apps.etablissements.models import Etablissement
    from .models import ClotureCaisse, StatutCloture
    from apps.notifications.services import notifier_cloture_oubliee

    today = localdate()
    etablissements = Etablissement.objects.filter(is_active=True)
    for etab in etablissements:
        if not ClotureCaisse.objects.filter(etablissement=etab, date=today).exists():
            notifier_cloture_oubliee(etab)


@app.task
def bloquer_bulletins_fin_annee(annee_scolaire_id):
    """
    À la clôture d'année : bloque les bulletins des élèves
    du second degré ayant un solde impayé.
    """
    from apps.scolarite.models import Inscription
    from apps.bulletins.models import Bulletin
    from apps.etablissements.models import TypeCycle
    from django.db.models import Sum, F

    inscriptions = Inscription.objects.filter(
        annee_scolaire_id=annee_scolaire_id,
        classe__niveau__cycle__type_cycle__in=[TypeCycle.COLLEGE, TypeCycle.LYCEE],
    ).select_related('eleve')

    for inscription in inscriptions:
        total_du = inscription.frais.aggregate(t=Sum('montant'))['t'] or 0
        total_paye = inscription.paiements.aggregate(t=Sum('montant'))['t'] or 0
        if float(total_du) - float(total_paye) > 0:
            Bulletin.objects.filter(inscription=inscription).update(
                bloque=True,
                motif_blocage='Solde impayé en fin d\'année scolaire.'
            )
