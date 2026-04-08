"""
Seed complet et realiste.
  - 3 etablissements (GSEP, ISFT, GSSP)
  - 7 niveaux x 2 classes = 14 classes par etab
  - 10 eleves par classe (avec compte user + role ELEVE)
  - 8 professeurs par etab, chacun affecte a ses matieres dans toutes les classes
  - Frais inscription + scolarite mensuelle par niveau (avec paiements realistes)
  - 3 periodes d evaluation avec toutes les notes
  - Parents pour ~65 % des eleves
  - Quelques absences par classe
  - Notifications directeur / prefet
Usage : python manage.py seed_data
"""
import unicodedata
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User, RoleUtilisateur, RoleChoices
from apps.etablissements.models import Etablissement, Cycle, TypeCycle, Niveau, AnneeScolaire
from apps.scolarite.models import (
    Eleve, Classe, Inscription, LienParentEleve,
    StatutInscription, TypeEleve,
)
from apps.matieres.models import Matiere, MatiereClasse
from apps.notes.models import PeriodeEvaluation, TypePeriode, Note, StatutNote
from apps.finances.models import (
    TypeFrais, TypeCategorieFrais, Frais, Paiement, StatutPaiement,
)
from apps.notifications.models import Notification, TypeNotification
from apps.vie_scolaire.models import AbsenceEleve


# ---------------------------------------------------------------------------
# DONNEES DE REFERENCE
# ---------------------------------------------------------------------------

DOMAINE = 'ensmg.sn'
MOT_DE_PASSE = 'admin1234'
NB_ELEVES_PAR_CLASSE = 10

PRENOMS_M = [
    'Moussa', 'Ibrahima', 'Cheikh', 'Omar', 'Mamadou', 'Abdou',
    'Ousmane', 'Alioune', 'Modou', 'Lamine', 'Aliou', 'Babacar',
    'Samba', 'Pape', 'Serigne', 'Daouda', 'Malick', 'El Hadji',
    'Boubacar', 'Assane', 'Seydou', 'Tidiane', 'Demba', 'Habib',
    'Idrissa', 'Gorgui', 'Bamba', 'Khadim', 'Mame Balla', 'Fallou',
]
PRENOMS_F = [
    'Fatou', 'Aissatou', 'Mariama', 'Rokhaya', 'Khady', 'Ndeye',
    'Aminata', 'Astou', 'Coumba', 'Dieynaba', 'Yacine', 'Sokhna',
    'Rama', 'Awa', 'Mame', 'Adja', 'Binta', 'Ndella', 'Seynabou',
    'Penda', 'Ndoumbel', 'Kine', 'Ramatoulaye', 'Oumou', 'Awa Binta',
    'Marieme', 'Bigue', 'Amy', 'Nafi', 'Daba',
]
NOMS = [
    'Diallo', 'Ndiaye', 'Sow', 'Fall', 'Diop', 'Ba', 'Mbaye', 'Sarr',
    'Gueye', 'Cisse', 'Sy', 'Faye', 'Diouf', 'Wade', 'Seck', 'Thiam',
    'Ndoye', 'Camara', 'Toure', 'Konate', 'Sakho', 'Ndour', 'Badji',
    'Manga', 'Mendy', 'Gomis', 'Tendeng', 'Sambou', 'Dieme', 'Diatta',
    'Coly', 'Bodian', 'Keita', 'Coulibaly', 'Traore', 'Balde',
]
VILLES = [
    'Dakar', 'Thies', 'Saint-Louis', 'Ziguinchor', 'Kaolack',
    'Mbour', 'Louga', 'Tambacounda', 'Kolda', 'Fatick',
    'Diourbel', 'Touba', 'Rufisque', 'Pikine', 'Guediawaye',
]

# Matieres : (nom, code, coefficient)
MATIERES = [
    ('Mathematiques',                     'MATH',  5),
    ('Francais',                           'FR',    4),
    ('Anglais',                            'ANG',   3),
    ('Physique-Chimie',                    'PC',    4),
    ('Sciences de la Vie et de la Terre',  'SVT',   3),
    ('Histoire-Geographie',               'HG',    3),
    ('Philosophie',                        'PHILO', 2),
    ('Informatique',                       'INFO',  2),
    ('Economie',                           'ECO',   2),
    ('Education Physique et Sportive',     'EPS',   1),
]

# Niveaux : (nom, ordre, cycle)
NIVEAUX = [
    ('6eme',      1, TypeCycle.COLLEGE),
    ('5eme',      2, TypeCycle.COLLEGE),
    ('4eme',      3, TypeCycle.COLLEGE),
    ('3eme',      4, TypeCycle.COLLEGE),
    ('2nde',      5, TypeCycle.LYCEE),
    ('1ere',      6, TypeCycle.LYCEE),
    ('Terminale', 7, TypeCycle.LYCEE),
]

# Frais par niveau : (montant inscription, mensualite scolarite par mois)
FRAIS_NIVEAU = {
    '6eme':      (25_000,  18_000),
    '5eme':      (25_000,  18_000),
    '4eme':      (25_000,  20_000),
    '3eme':      (25_000,  20_000),
    '2nde':      (30_000,  25_000),
    '1ere':      (35_000,  28_000),
    'Terminale': (35_000,  30_000),
}

# 10 mois scolaires (un TypeFrais distinct par mois)
MOIS_SCOLAIRES = [
    ('Scolarite Octobre',   10, 2025),
    ('Scolarite Novembre',  11, 2025),
    ('Scolarite Decembre',  12, 2025),
    ('Scolarite Janvier',    1, 2026),
    ('Scolarite Fevrier',    2, 2026),
    ('Scolarite Mars',       3, 2026),
    ('Scolarite Avril',      4, 2026),
    ('Scolarite Mai',        5, 2026),
    ('Scolarite Juin',       6, 2026),
    ('Scolarite Juillet',    7, 2026),
]

# Professeurs : chaque prof enseigne ses matieres dans TOUTES les classes de l etab
# (tag_email, genre, [noms de matieres])
PROFS_CONFIG = [
    ('prof.math',   'M', ['Mathematiques']),
    ('prof.fr',     'F', ['Francais']),
    ('prof.ang',    'M', ['Anglais']),
    ('prof.pc',     'M', ['Physique-Chimie']),
    ('prof.svt',    'F', ['Sciences de la Vie et de la Terre']),
    ('prof.hg',     'M', ['Histoire-Geographie']),
    ('prof.philo',  'F', ['Philosophie', 'Economie']),
    ('prof.info',   'M', ['Informatique', 'Education Physique et Sportive']),
]

# Periodes d evaluation
PERIODES_DEF = [
    (TypePeriode.CONTROLE,    1, '1er Controle',     date(2025, 10, 20), date(2025, 11,  5)),
    (TypePeriode.CONTROLE,    2, '2eme Controle',    date(2025, 11, 10), date(2025, 11, 25)),
    (TypePeriode.COMPOSITION, 1, '1ere Composition', date(2025, 12,  1), date(2025, 12, 20)),
    (TypePeriode.CONTROLE,    3, '3eme Controle',    date(2026,  1, 12), date(2026,  1, 28)),
    (TypePeriode.COMPOSITION, 2, '2eme Composition', date(2026,  3,  2), date(2026,  3, 20)),
]

# Repartition type eleve : 70% ordinaire, 20% boursier, 10% auditeur
TYPES_ELEVE_POOL = (
    [TypeEleve.ORDINAIRE] * 7
    + [TypeEleve.BOURSIER] * 2
    + [TypeEleve.AUDITEUR] * 1
)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _norm(s):
    """'El Hadji Diallo' -> 'el.hadji.diallo' (sans accents)"""
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.lower().replace(' ', '.')


def _unique_email(prenom, nom, extra=''):
    base = f"{_norm(prenom)}.{_norm(nom)}{extra}"
    for i in range(30):
        e = f"{base}{'.' + str(i+2) if i else ''}@{DOMAINE}"
        if not User.objects.filter(email=e).exists():
            return e
    return f"{base}.{random.randint(1000,9999)}@{DOMAINE}"


def _create_user(prenom, nom, email, role=None, etab=None, is_staff=False,
                 is_superuser=False):
    u, created = User.objects.get_or_create(
        email=email,
        defaults={
            'nom': nom, 'prenom': prenom,
            'telephone': f"7{random.choice(['7','8','6'])}{random.randint(1_000_000,9_999_999)}",
            'is_staff': is_staff, 'is_superuser': is_superuser,
            'must_change_password': False,
        }
    )
    if created:
        u.set_password(MOT_DE_PASSE)
        u.save()
    if role:
        RoleUtilisateur.objects.get_or_create(
            user=u, etablissement=etab,
            defaults={'role': role}
        )
    return u


rp = lambda g='M': random.choice(PRENOMS_M if g == 'M' else PRENOMS_F)
rn = lambda: random.choice(NOMS)


# ---------------------------------------------------------------------------
# COMMANDE
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Seed complet : 10 eleves/classe, profs affectes, notes, frais, absences'

    def handle(self, *args, **options):
        w = self.stdout.write
        ok = self.style.SUCCESS
        h  = self.style.MIGRATE_HEADING

        w(h('\n=== SEED COMPLET ===\n'))

        with transaction.atomic():
            matieres_obj = self._matieres(w)
            etabs        = self._etablissements(w)
            self._annees(etabs)
            niveaux_map  = self._niveaux(etabs, w)
            classes_map  = self._classes(etabs, niveaux_map, w)
            self._frais_types(etabs, niveaux_map, w)
            self._superadmin(w)
            profs_map    = self._professeurs(etabs, classes_map, matieres_obj, w)
            periodes_map = self._periodes(etabs, w)
            self._eleves(etabs, classes_map, matieres_obj, profs_map, periodes_map, w)
            self._notifications(etabs, w)

        w(ok('\n=== PEUPLEMENT TERMINE ===\n'))
        w('-' * 60)
        w(f'Super Admin  : super.admin@{DOMAINE}')
        w(f'Directeur    : directeur.[nom]@{DOMAINE}')
        w(f'Professeur   : prof.math.[nom]@{DOMAINE}  etc.')
        w(f'Eleve        : [prenom].[nom]@{DOMAINE}')
        w(f'Mot de passe : {MOT_DE_PASSE}')
        w('-' * 60)

    # ------------------------------------------------------------------
    # MATIERES
    # ------------------------------------------------------------------
    def _matieres(self, w):
        w('  [1] Matieres...')
        objs = {}
        for nom, code, _ in MATIERES:
            m, _ = Matiere.objects.get_or_create(nom=nom, defaults={'code': code})
            objs[nom] = m
        w(f'      {len(objs)} matieres OK')
        return objs

    # ------------------------------------------------------------------
    # ETABLISSEMENTS
    # ------------------------------------------------------------------
    def _etablissements(self, w):
        w('  [2] Etablissements...')
        data = [
            ('GSEP', 'Groupe Scolaire Elite Plus',
             'Rue 10, Cite Keur Gorgui, Dakar', '338670001'),
            ('ISFT', 'Institut Superieur de Formation Technique',
             'Avenue Bourguiba, Dakar', '338670002'),
            ('GSSP', 'Groupe Scolaire Savoir Plus',
             'VDN Lot 45, Dakar', '338670003'),
        ]
        etabs = []
        for sigle, nom, adresse, tel in data:
            etab, c = Etablissement.objects.get_or_create(
                sigle=sigle,
                defaults={
                    'nom': nom, 'adresse': adresse, 'telephone': tel,
                    'email': f'contact@{sigle.lower()}.sn',
                }
            )
            etabs.append(etab)
            w(f'      {"+" if c else "~"} {etab.nom}')
        return etabs

    # ------------------------------------------------------------------
    # ANNEES SCOLAIRES
    # ------------------------------------------------------------------
    def _annees(self, etabs):
        for etab in etabs:
            AnneeScolaire.objects.get_or_create(
                etablissement=etab, libelle='2025-2026',
                defaults={
                    'date_debut': date(2025, 10, 1),
                    'date_fin':   date(2026,  7, 31),
                    'is_active':  True,
                }
            )

    # ------------------------------------------------------------------
    # NIVEAUX
    # ------------------------------------------------------------------
    def _niveaux(self, etabs, w):
        w('  [3] Niveaux...')
        niveaux_map = {}   # (etab_id, nom_niv) -> Niveau
        for etab in etabs:
            cycles = {}
            for tc in [TypeCycle.COLLEGE, TypeCycle.LYCEE]:
                c, _ = Cycle.objects.get_or_create(etablissement=etab, type_cycle=tc)
                cycles[tc] = c
            for nom_niv, ordre, tc in NIVEAUX:
                niv, _ = Niveau.objects.get_or_create(
                    cycle=cycles[tc], nom=nom_niv,
                    defaults={'ordre': ordre}
                )
                niveaux_map[(etab.id, nom_niv)] = niv
        w(f'      {len(NIVEAUX) * len(etabs)} niveaux OK')
        return niveaux_map

    # ------------------------------------------------------------------
    # CLASSES (2 par niveau)
    # ------------------------------------------------------------------
    def _classes(self, etabs, niveaux_map, w):
        w('  [4] Classes...')
        classes_map = {}   # (etab_id, nom_classe) -> Classe
        total = 0
        for etab in etabs:
            annee = AnneeScolaire.objects.get(etablissement=etab, is_active=True)
            for nom_niv, _, _ in NIVEAUX:
                niv = niveaux_map[(etab.id, nom_niv)]
                for lettre in ['A', 'B']:
                    nom_classe = f"{nom_niv} {lettre}"
                    cls, _ = Classe.objects.get_or_create(
                        etablissement=etab, annee_scolaire=annee, nom=nom_classe,
                        defaults={'niveau': niv, 'effectif_max': 40}
                    )
                    classes_map[(etab.id, nom_classe)] = cls
                    total += 1
        w(f'      {total} classes OK  ({total * NB_ELEVES_PAR_CLASSE} eleves prevus)')
        return classes_map

    # ------------------------------------------------------------------
    # TYPES DE FRAIS par niveau
    # ------------------------------------------------------------------
    def _frais_types(self, etabs, niveaux_map, w):
        w('  [5] Types de frais...')
        for etab in etabs:
            annee = AnneeScolaire.objects.get(etablissement=etab, is_active=True)
            for nom_niv, _, _ in NIVEAUX:
                niv = niveaux_map[(etab.id, nom_niv)]
                mnt_ins, mnt_men = FRAIS_NIVEAU[nom_niv]
                # Frais d inscription (one-shot)
                TypeFrais.objects.get_or_create(
                    etablissement=etab, libelle='Inscription',
                    niveau=niv, annee_scolaire=annee,
                    defaults={
                        'categorie': TypeCategorieFrais.INSCRIPTION,
                        'montant_defaut': mnt_ins,
                    }
                )
                # Un TypeFrais distinct par mois (Oct -> Jul)
                for libelle_mois, _, _ in MOIS_SCOLAIRES:
                    TypeFrais.objects.get_or_create(
                        etablissement=etab, libelle=libelle_mois,
                        niveau=niv, annee_scolaire=annee,
                        defaults={
                            'categorie': TypeCategorieFrais.SCOLARITE_MENSUELLE,
                            'montant_defaut': mnt_men,
                        }
                    )
        w('      Frais inscription + 10 mensualites par niveau OK')

    # ------------------------------------------------------------------
    # SUPER ADMIN
    # ------------------------------------------------------------------
    def _superadmin(self, w):
        w('  [6] Super admin...')
        _create_user(
            'Super', 'Admin',
            f'super.admin@{DOMAINE}',
            is_staff=True, is_superuser=True,
        )
        w('      super.admin OK')

    # ------------------------------------------------------------------
    # PROFESSEURS — assignes a leurs matieres dans toutes les classes
    # ------------------------------------------------------------------
    def _professeurs(self, etabs, classes_map, matieres_obj, w):
        w('  [7] Professeurs & affectations...')
        profs_map = {}   # (etab_id, nom_matiere) -> User (prof)
        total_mc = 0

        for etab in etabs:
            annee = AnneeScolaire.objects.get(etablissement=etab, is_active=True)
            classes_etab = [
                cls for (eid, _), cls in classes_map.items() if eid == etab.id
            ]

            # Roles de direction / gestion
            roles_support = [
                ('directeur', 'M', RoleChoices.DIRECTEUR, True),
                ('prefet',    'M', RoleChoices.PREFET,    False),
                ('comptable', 'F', RoleChoices.COMPTABLE, False),
                ('caissier',  'M', RoleChoices.CAISSIER,  False),
                ('surveil1',  'M', RoleChoices.SURVEILLANT, False),
                ('surveil2',  'F', RoleChoices.SURVEILLANT, False),
            ]
            for tag, genre, role, is_staff in roles_support:
                prenom = rp(genre)
                nom    = rn()
                email  = _unique_email(tag, nom, f'.{etab.sigle.lower()}')
                _create_user(prenom, nom, email, role=role, etab=etab, is_staff=is_staff)

            # Professeurs specialises
            for tag, genre, mat_noms in PROFS_CONFIG:
                prenom = rp(genre)
                nom    = rn()
                email  = _unique_email(tag, nom, f'.{etab.sigle.lower()}')
                prof   = _create_user(prenom, nom, email,
                                      role=RoleChoices.PROFESSEUR, etab=etab)

                for mat_nom in mat_noms:
                    mat = matieres_obj.get(mat_nom)
                    if not mat:
                        continue
                    _, coeff, _ = next(
                        ((n, c, _) for n, _, c in [(m[0], m[1], m[2]) for m in MATIERES]
                         if n == mat_nom), (None, 1, None)
                    )
                    # Trouver le coeff depuis MATIERES
                    coeff_val = next(
                        (c for n, _, c in MATIERES if n == mat_nom), 1
                    )
                    for cls in classes_etab:
                        mc, _ = MatiereClasse.objects.get_or_create(
                            matiere=mat, classe=cls,
                            defaults={
                                'coefficient': coeff_val,
                                'professeur':  prof,
                                'mode_calcul_cc': 'TOUTES',
                            }
                        )
                        if mc.professeur != prof:
                            mc.professeur = prof
                            mc.save(update_fields=['professeur'])
                        profs_map[(etab.id, mat_nom)] = prof
                        total_mc += 1

            w(f'      {etab.sigle}: 8 profs, {len(PROFS_CONFIG)} specialites configurees')

        w(f'      {total_mc} affectations MatiereClasse OK')
        return profs_map

    # ------------------------------------------------------------------
    # PERIODES D EVALUATION
    # ------------------------------------------------------------------
    def _periodes(self, etabs, w):
        w('  [8] Periodes evaluation...')
        periodes_map = {}   # etab_id -> [PeriodeEvaluation]
        for etab in etabs:
            annee = AnneeScolaire.objects.get(etablissement=etab, is_active=True)
            periodes = []
            for tp, num, lib, dd, df in PERIODES_DEF:
                p, _ = PeriodeEvaluation.objects.get_or_create(
                    etablissement=etab, annee_scolaire=annee,
                    type_periode=tp, numero=num,
                    defaults={'libelle': lib, 'date_debut': dd, 'date_fin': df}
                )
                periodes.append(p)
            periodes_map[etab.id] = periodes
        w(f'      {len(PERIODES_DEF)} periodes x {len(etabs)} etabs OK')
        return periodes_map

    # ------------------------------------------------------------------
    # ELEVES — 10 par classe, complets
    # ------------------------------------------------------------------
    def _eleves(self, etabs, classes_map, matieres_obj, profs_map, periodes_map, w):
        w('  [9] Eleves, inscriptions, frais, notes, absences...')
        total_eleves = total_notes = total_absences = 0

        for etab in etabs:
            annee    = AnneeScolaire.objects.get(etablissement=etab, is_active=True)
            caissier = User.objects.filter(
                roles__etablissement=etab, roles__role=RoleChoices.CAISSIER
            ).first()
            surveillant = User.objects.filter(
                roles__etablissement=etab, roles__role=RoleChoices.SURVEILLANT
            ).first()
            periodes = periodes_map[etab.id]

            classes_etab = [
                cls for (eid, _), cls in classes_map.items() if eid == etab.id
            ]

            for classe in classes_etab:
                niv = classe.niveau
                matieres_classe = list(
                    MatiereClasse.objects.filter(classe=classe)
                    .select_related('matiere', 'professeur')
                )
                tf_ins = TypeFrais.objects.filter(
                    etablissement=etab, niveau=niv, annee_scolaire=annee,
                    categorie=TypeCategorieFrais.INSCRIPTION
                ).first()

                notes_batch = []

                for _ in range(NB_ELEVES_PAR_CLASSE):
                    sexe   = 'M' if random.random() > 0.42 else 'F'
                    prenom = rp(sexe)
                    nom    = rn()

                    # Eleve
                    eleve = None
                    for _r in range(5):
                        try:
                            from django.db import transaction as _tx
                            with _tx.atomic():
                                eleve = Eleve.objects.create(
                                    nom=nom, prenom=prenom, sexe=sexe,
                                    type_eleve=random.choice(TYPES_ELEVE_POOL),
                                    date_naissance=date(
                                        random.randint(2004, 2013),
                                        random.randint(1, 12),
                                        random.randint(1, 28),
                                    ),
                                    lieu_naissance=random.choice(VILLES),
                                )
                            break
                        except Exception:
                            nom = rn()
                            continue
                    if eleve is None:
                        continue

                    # Compte eleve
                    e_email = _unique_email(prenom, nom)
                    try:
                        eu = _create_user(prenom, nom, e_email,
                                          role=RoleChoices.ELEVE, etab=etab)
                        eleve.user = eu
                        eleve.save(update_fields=['user'])
                    except Exception:
                        pass

                    # Inscription
                    inscription = Inscription.objects.create(
                        eleve=eleve, classe=classe,
                        etablissement=etab, annee_scolaire=annee,
                        statut=StatutInscription.ACTIF,
                    )

                    # Frais d inscription
                    if tf_ins:
                        f_ins = Frais.objects.create(
                            inscription=inscription,
                            type_frais=tf_ins,
                            montant=tf_ins.montant_defaut,
                            created_by=caissier,
                        )
                        if random.random() > 0.15 and caissier:
                            Paiement.objects.create(
                                inscription=inscription, frais=f_ins,
                                montant=tf_ins.montant_defaut,
                                caissier=caissier, statut=StatutPaiement.VALIDE,
                            )

                    # Frais mensuel : 1 Frais par mois, paye ou non
                    # Determiner jusqu a quel mois l eleve a paye (aleatoire)
                    mois_payes_n = random.choice([0, 1, 2, 2, 3, 3, 4, 5, 6, 7, 8, 10])
                    for i, (libelle_mois, mois_num, mois_annee) in enumerate(MOIS_SCOLAIRES):
                        tf_mois = TypeFrais.objects.filter(
                            etablissement=etab, niveau=niv,
                            annee_scolaire=annee, libelle=libelle_mois
                        ).first()
                        if not tf_mois:
                            continue
                        f_mois = Frais.objects.create(
                            inscription=inscription,
                            type_frais=tf_mois,
                            montant=tf_mois.montant_defaut,
                            created_by=caissier,
                        )
                        # Les mois_payes_n premiers mois sont payes
                        if i < mois_payes_n and caissier:
                            Paiement.objects.create(
                                inscription=inscription, frais=f_mois,
                                montant=tf_mois.montant_defaut,
                                caissier=caissier, statut=StatutPaiement.VALIDE,
                            )

                    # Notes — tous les matieres x toutes les periodes
                    for mc in matieres_classe:
                        for periode in periodes:
                            # Notes realistes selon le profil
                            if eleve.type_eleve == TypeEleve.BOURSIER:
                                val = round(random.triangular(10, 20, 16), 2)
                            elif eleve.type_eleve == TypeEleve.AUDITEUR:
                                val = round(random.triangular(5, 18, 12), 2)
                            else:
                                val = round(random.triangular(4, 20, 13), 2)
                            val = min(20.0, max(0.0, val))

                            notes_batch.append(Note(
                                inscription=inscription,
                                matiere_classe=mc,
                                periode=periode,
                                valeur=round(val, 2),
                                statut=StatutNote.ACTIVE,
                                saisi_par=mc.professeur or caissier,
                            ))

                    # Parent (65%)
                    if random.random() > 0.35:
                        g_p = 'F' if random.random() > 0.55 else 'M'
                        p_prenom = rp(g_p)
                        p_email  = _unique_email(p_prenom, nom, '.parent')
                        try:
                            p = _create_user(p_prenom, nom, p_email,
                                             role=RoleChoices.PARENT, etab=etab)
                            LienParentEleve.objects.get_or_create(
                                parent=p, eleve=eleve,
                                defaults={'lien': 'PERE' if g_p == 'M' else 'MERE'}
                            )
                        except Exception:
                            pass

                    total_eleves += 1

                # Bulk insert notes
                if notes_batch:
                    Note.objects.bulk_create(notes_batch, ignore_conflicts=True)
                    total_notes += len(notes_batch)

                # Absences : 2-4 absences aleatoires par classe
                inscriptions_classe = list(
                    Inscription.objects.filter(classe=classe, statut='ACTIF')
                )
                nb_abs = random.randint(2, 4)
                for _ in range(nb_abs):
                    if not inscriptions_classe or not surveillant:
                        break
                    insc  = random.choice(inscriptions_classe)
                    delta = random.randint(0, 60)
                    abs_date = date(2025, 10, 1) + timedelta(days=delta)
                    try:
                        AbsenceEleve.objects.get_or_create(
                            inscription=insc,
                            date=abs_date,
                            defaults={
                                'justifiee': random.random() > 0.6,
                                'enregistre_par': surveillant,
                                'motif': random.choice([
                                    'Maladie', 'Raison familiale',
                                    'Non precisee', 'Voyage'
                                ]),
                            }
                        )
                        total_absences += 1
                    except Exception:
                        pass

            w(f'      {etab.sigle} : {total_eleves} eleves, {total_notes} notes')

        w(f'      Total : {total_eleves} eleves | {total_notes} notes | {total_absences} absences')

    # ------------------------------------------------------------------
    # NOTIFICATIONS
    # ------------------------------------------------------------------
    def _notifications(self, etabs, w):
        w('  [10] Notifications...')
        msgs = [
            (RoleChoices.DIRECTEUR, TypeNotification.MODIFICATION_NOTE_SOUMISE,
             'Demande modification note',
             'Une note de Maths 3eme A est en attente de validation.', False),
            (RoleChoices.DIRECTEUR, TypeNotification.CLOTURE_OUBLIEE,
             'Cloture caisse oubliee',
             "La caisse n'a pas ete cloturee hier. Veuillez regulariser.", False),
            (RoleChoices.DIRECTEUR, TypeNotification.FICHE_PAIE_A_VALIDER,
             'Fiches de paie a valider',
             '5 fiches de paie novembre sont pretes a etre validees.', True),
            (RoleChoices.PREFET, TypeNotification.NOTES_NON_SAISIES,
             'Notes non saisies',
             'Prof anglais 2nde B : aucune note saisie pour le 2eme controle.', False),
            (RoleChoices.PREFET, TypeNotification.ALERTE_RETARDS_ELEVE,
             'Retards repetes',
             '3 eleves de 6eme A ont accumule plus de 5 retards ce mois.', False),
        ]
        for etab in etabs:
            for role, typ, titre, msg, lue in msgs:
                dest = User.objects.filter(
                    roles__etablissement=etab, roles__role=role
                ).first()
                if dest:
                    Notification.objects.get_or_create(
                        destinataire=dest, type_notification=typ, titre=titre,
                        defaults={'message': msg, 'lue': lue}
                    )
        w('      Notifications OK')
