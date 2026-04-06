from config.celery import app
from decimal import Decimal


@app.task
def calculer_fiches_de_paie_mensuelles(etablissement_id, mois_str):
    """
    Calcule les fiches de paie provisoires pour tous les profs d'un établissement.
    mois_str: '2025-01-01' (premier jour du mois)
    """
    from datetime import date
    from django.db.models import Sum
    from .models import Affectation, Seance, Emargement, FicheDePaie, LigneFicheDePaie, StatutEmargement
    from apps.etablissements.models import Etablissement

    mois = date.fromisoformat(mois_str)
    try:
        etablissement = Etablissement.objects.get(pk=etablissement_id)
    except Etablissement.DoesNotExist:
        return

    affectations = Affectation.objects.filter(
        etablissement=etablissement, is_active=True
    ).select_related('professeur', 'matiere_classe')

    # Grouper par professeur
    profs = {}
    for aff in affectations:
        profs.setdefault(aff.professeur_id, []).append(aff)

    for prof_id, affs in profs.items():
        prof = affs[0].professeur
        fiche, _ = FicheDePaie.objects.get_or_create(
            professeur=prof,
            etablissement=etablissement,
            mois=mois,
            defaults={'statut': 'PROVISOIRE', 'montant_total': 0}
        )
        if fiche.statut != 'PROVISOIRE':
            continue

        LigneFicheDePaie.objects.filter(fiche=fiche).delete()
        total = Decimal('0')

        for aff in affs:
            # Heures validées = séances PRESENT dans le mois
            emargements = Emargement.objects.filter(
                seance__affectation=aff,
                seance__date__year=mois.year,
                seance__date__month=mois.month,
                statut=StatutEmargement.PRESENT,
            )
            heures = sum(
                Decimal(str(e.duree_minutes)) / Decimal('60')
                for e in emargements
            )
            montant_ligne = heures * aff.taux_horaire
            total += montant_ligne

            LigneFicheDePaie.objects.create(
                fiche=fiche,
                affectation=aff,
                heures_validees=heures,
                taux_horaire=aff.taux_horaire,
                montant=montant_ligne,
            )

        fiche.montant_total = total
        fiche.save(update_fields=['montant_total'])

    # Notifier le comptable
    from apps.notifications.services import notifier_fiches_paie_a_valider
    notifier_fiches_paie_a_valider(etablissement)
