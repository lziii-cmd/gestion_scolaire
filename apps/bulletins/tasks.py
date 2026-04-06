from config.celery import app
from .models import Bulletin, BulletinLigne, StatutBulletin
from apps.notes.models import Note, TypePeriode
from apps.notes.services import calculer_rang_dans_classe, calculer_moyenne_generale
from apps.matieres.models import MatiereClasse


@app.task
def generer_bulletin(inscription_id, periode_id):
    """
    Tâche asynchrone : génère ou regénère le bulletin d'un élève pour une période donnée.
    """
    from apps.scolarite.models import Inscription
    from apps.notes.models import PeriodeEvaluation

    try:
        inscription = Inscription.objects.select_related(
            'classe', 'etablissement', 'eleve'
        ).get(pk=inscription_id)
        periode = PeriodeEvaluation.objects.get(pk=periode_id)
    except (Inscription.DoesNotExist, PeriodeEvaluation.DoesNotExist):
        return

    bulletin, _ = Bulletin.objects.get_or_create(
        inscription=inscription,
        periode=periode,
        defaults={'statut': StatutBulletin.BROUILLON}
    )

    matieres = MatiereClasse.objects.filter(
        classe=inscription.classe,
        is_active=True,
    )

    # Calcul des rangs dans la classe pour cette période
    rangs_par_matiere = {}
    for mc in matieres:
        rangs_par_matiere[mc.pk] = calculer_rang_dans_classe(mc, periode)

    # Génération des lignes
    BulletinLigne.objects.filter(bulletin=bulletin).delete()
    for mc in matieres:
        note_obj = Note.objects.filter(
            inscription=inscription,
            matiere_classe=mc,
            periode=periode,
            statut='ACTIVE',
        ).first()

        rang = rangs_par_matiere[mc.pk].get(inscription.pk)

        BulletinLigne.objects.create(
            bulletin=bulletin,
            matiere_classe=mc,
            note=note_obj.valeur if note_obj and not note_obj.absence_justifiee else None,
            rang=rang,
        )

    # Moyenne générale et rang général
    moy = calculer_moyenne_generale(inscription, periode)
    bulletin.moyenne_generale = moy
    bulletin.save(update_fields=['moyenne_generale'])


@app.task
def generer_pdf_bulletin(bulletin_id):
    """
    Génère le PDF d'un bulletin (via ReportLab ou WeasyPrint).
    À implémenter selon le moteur PDF retenu.
    """
    try:
        bulletin = Bulletin.objects.select_related(
            'inscription__eleve', 'inscription__etablissement', 'periode'
        ).prefetch_related('lignes__matiere_classe__matiere').get(pk=bulletin_id)
    except Bulletin.DoesNotExist:
        return

    # TODO: Générer le PDF et sauvegarder dans bulletin.pdf
    pass


@app.task
def generer_bulletins_classe(classe_id, periode_id):
    """Lance la génération pour tous les élèves d'une classe."""
    from apps.scolarite.models import Inscription
    inscriptions = Inscription.objects.filter(
        classe_id=classe_id, statut='ACTIF'
    ).values_list('pk', flat=True)
    for inscription_id in inscriptions:
        generer_bulletin.delay(inscription_id, periode_id)
