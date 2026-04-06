from decimal import Decimal
from django.db.models import Avg
from .models import Note, PeriodeEvaluation, TypePeriode


def calculer_moyenne_cc(matiere_classe, inscription):
    """
    Calcule la moyenne CC selon le mode choisi par le prof.
    - TOUTES : moyenne simple de toutes les notes mensuelles du semestre
    - N_MEILLEURES : seules les N meilleures notes
    Exclut les absences justifiées.
    """
    notes = Note.objects.filter(
        inscription=inscription,
        matiere_classe=matiere_classe,
        periode__type_periode=TypePeriode.MENSUEL,
        statut='ACTIVE',
        absence_justifiee=False,
    ).values_list('valeur', flat=True)

    valeurs = [v for v in notes if v is not None]
    if not valeurs:
        return None

    mode = matiere_classe.mode_calcul_cc
    if mode == 'N_MEILLEURES' and matiere_classe.n_meilleures_notes:
        n = matiere_classe.n_meilleures_notes
        valeurs = sorted(valeurs, reverse=True)[:n]

    return sum(valeurs) / len(valeurs)


def calculer_moyenne_elementaire(matiere_classe, inscription):
    """
    Moyenne annuelle élémentaire = moyenne simple des 6 notes (contrôles + compositions).
    """
    notes = Note.objects.filter(
        inscription=inscription,
        matiere_classe=matiere_classe,
        statut='ACTIVE',
        absence_justifiee=False,
    ).exclude(valeur=None).values_list('valeur', flat=True)

    valeurs = list(notes)
    if not valeurs:
        return None
    return sum(valeurs) / len(valeurs)


def calculer_rang_dans_classe(matiere_classe, periode):
    """
    Retourne un dict {inscription_id: rang} pour une matière et une période données.
    """
    notes = Note.objects.filter(
        matiere_classe=matiere_classe,
        periode=periode,
        statut='ACTIVE',
    ).exclude(valeur=None).order_by('-valeur').select_related('inscription')

    rangs = {}
    for rang, note in enumerate(notes, start=1):
        rangs[note.inscription_id] = rang
    return rangs


def calculer_moyenne_generale(inscription, periode):
    """
    Moyenne générale pondérée par les coefficients pour une inscription sur une période.
    """
    notes = Note.objects.filter(
        inscription=inscription,
        periode=periode,
        statut='ACTIVE',
    ).exclude(valeur=None).select_related('matiere_classe')

    total_points = Decimal('0')
    total_coef = Decimal('0')

    for note in notes:
        coef = note.matiere_classe.coefficient
        total_points += note.valeur * coef
        total_coef += coef

    if total_coef == 0:
        return None
    return total_points / total_coef
