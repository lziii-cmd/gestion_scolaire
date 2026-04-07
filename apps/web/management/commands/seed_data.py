"""
Commande de peuplement avec des donnees de test realistes.
Usage: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.db import transaction
import random
from datetime import date

from apps.accounts.models import User, RoleUtilisateur, RoleChoices
from apps.etablissements.models import (
    Etablissement, Cycle, TypeCycle, Niveau, AnneeScolaire
)
from apps.scolarite.models import Eleve, Classe, Inscription, LienParentEleve
from apps.matieres.models import Matiere, MatiereClasse
from apps.notes.models import PeriodeEvaluation, TypePeriode, Note
from apps.finances.models import TypeFrais, Frais, Paiement
from apps.notifications.models import Notification, TypeNotification


PRENOMS_M = ['Moussa', 'Ibrahima', 'Cheikh', 'Omar', 'Mamadou', 'Abdou',
             'Ousmane', 'Alioune', 'Modou', 'Lamine', 'Aliou', 'Babacar', 'Samba', 'Pape', 'Serigne']
PRENOMS_F = ['Fatou', 'Aissatou', 'Mariama', 'Rokhaya', 'Khady', 'Ndeye',
             'Aminata', 'Astou', 'Coumba', 'Dieynaba', 'Yacine', 'Sokhna', 'Rama', 'Awa', 'Mame']
NOMS = ['Diallo', 'Ndiaye', 'Sow', 'Fall', 'Diop', 'Ba', 'Mbaye', 'Sarr', 'Gueye', 'Cisse',
        'Sy', 'Faye', 'Diouf', 'Wade', 'Seck', 'Thiam', 'Ndoye', 'Camara', 'Toure', 'Konate']

MATIERES = [
    ('Mathematiques', 'MATH', 5),
    ('Francais', 'FR', 4),
    ('Anglais', 'ANG', 3),
    ('Physique-Chimie', 'PC', 4),
    ('Sciences de la Vie et de la Terre', 'SVT', 3),
    ('Histoire-Geographie', 'HG', 3),
    ('Philosophie', 'PHILO', 2),
    ('Informatique', 'INFO', 2),
    ('Économie', 'ECO', 2),
    ('Sport', 'EPS', 1),
]

NIVEAUX = [
    ('6eme', 1, TypeCycle.COLLEGE),
    ('5eme', 2, TypeCycle.COLLEGE),
    ('4eme', 3, TypeCycle.COLLEGE),
    ('3eme', 4, TypeCycle.COLLEGE),
    ('2nde', 5, TypeCycle.LYCEE),
    ('1ere', 6, TypeCycle.LYCEE),
    ('Terminale', 7, TypeCycle.LYCEE),
]


def rp(genre='M'):
    return random.choice(PRENOMS_M if genre == 'M' else PRENOMS_F)

def rn():
    return random.choice(NOMS)

def rtel():
    return f"7{random.choice(['7','8','6'])}{random.randint(1000000,9999999)}"


class Command(BaseCommand):
    help = 'Peuple la base de donnees avec des donnees de test'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('\n  Demarrage du peuplement...\n'))

        self._matieres()
        etabs = self._etablissements()
        self._annees(etabs)
        self._niveaux_classes(etabs)
        self._users(etabs)
        self._eleves(etabs)
        self._notes(etabs)
        self._notifications(etabs)

        self.stdout.write(self.style.SUCCESS('\n  Peuplement termine!\n'))
        self.stdout.write('-' * 55)
        self.stdout.write('Comptes disponibles (mot de passe: admin1234):')
        self.stdout.write('  Super Admin   -> admin@gsep.sn')
        self.stdout.write('  Directeur GSEP-> directeur@gsep.sn')
        self.stdout.write('  Directeur ISFT-> directeur@isft.sn')
        self.stdout.write('  Directeur GSSP-> directeur@gssp.sn')
        self.stdout.write('  Professeur    -> prof1@gsep.sn')
        self.stdout.write('  Comptable     -> comptable@gsep.sn')
        self.stdout.write('-' * 55)

    # -- Matieres ---------------------------------------------
    def _matieres(self):
        self.stdout.write('   Matieres...')
        for nom, code, _ in MATIERES:
            Matiere.objects.get_or_create(nom=nom, defaults={'code': code})
        self.stdout.write(f'     -> {len(MATIERES)} matieres OK')

    # -- Établissements ----------------------------------------
    def _etablissements(self):
        self.stdout.write('   tablissements...')
        data = [
            ('GSEP', 'Groupe Scolaire Élite Plus', 'contact@gsep.sn'),
            ('ISFT', 'Institut Superieur de Formation Technique', 'contact@isft.sn'),
            ('GSSP', 'Groupe Scolaire Saint-Pierre', 'contact@gssp.sn'),
        ]
        etabs = []
        for sigle, nom, email in data:
            etab, c = Etablissement.objects.get_or_create(
                sigle=sigle,
                defaults={'nom': nom, 'email': email, 'telephone': rtel(),
                          'adresse': 'Avenue de la Republique, Dakar'}
            )
            etabs.append(etab)
            self.stdout.write(f'     {"" if c else "~"} {etab.nom}')
        return etabs

    # -- Annees scolaires --------------------------------------
    def _annees(self, etabs):
        self.stdout.write('   Annees scolaires...')
        for etab in etabs:
            AnneeScolaire.objects.get_or_create(
                etablissement=etab, libelle='2025-2026',
                defaults={'date_debut': date(2025, 10, 1),
                          'date_fin': date(2026, 7, 31), 'is_active': True}
            )

    # -- Niveaux & Classes -------------------------------------
    def _niveaux_classes(self, etabs):
        self.stdout.write('    Niveaux & classes...')
        for etab in etabs:
            annee = AnneeScolaire.objects.get(etablissement=etab, is_active=True)
            cycles = {}
            for tc in [TypeCycle.COLLEGE, TypeCycle.LYCEE]:
                c, _ = Cycle.objects.get_or_create(
                    etablissement=etab, type_cycle=tc
                )
                cycles[tc] = c

            for nom_niv, ordre, type_cycle in NIVEAUX:
                cycle = cycles[type_cycle]
                niv, _ = Niveau.objects.get_or_create(
                    cycle=cycle, nom=nom_niv,
                    defaults={'ordre': ordre}
                )
                for lettre in ['A', 'B']:
                    classe, _ = Classe.objects.get_or_create(
                        etablissement=etab, annee_scolaire=annee,
                        nom=f"{nom_niv} {lettre}",
                        defaults={'niveau': niv, 'effectif_max': random.randint(35, 45)}
                    )
                    # Attacher matieres
                    for nom_m, _, coeff in MATIERES:
                        mat = Matiere.objects.get(nom=nom_m)
                        MatiereClasse.objects.get_or_create(
                            classe=classe, matiere=mat,
                            defaults={'coefficient': coeff, 'mode_calcul_cc': 'MOYENNE'}
                        )
        self.stdout.write('     -> Classes et matieres configurees')

    # -- Utilisateurs & roles ----------------------------------
    def _users(self, etabs):
        self.stdout.write('   Utilisateurs...')

        # Super Admin
        sa, c = User.objects.get_or_create(
            email='admin@gsep.sn',
            defaults={'nom': 'Admin', 'prenom': 'Super',
                      'telephone': '770000000', 'is_staff': True, 'is_superuser': True}
        )
        if c:
            sa.set_password('admin1234'); sa.save()
        RoleUtilisateur.objects.get_or_create(
            user=sa, etablissement=None, role=RoleChoices.SUPER_ADMIN
        )

        for etab in etabs:
            s = etab.sigle.lower()

            roles_to_create = [
                (f'directeur@{s}.sn', rp('M'), rn(), RoleChoices.DIRECTEUR, True),
                (f'prefet@{s}.sn', rp('M'), rn(), RoleChoices.PREFET, False),
                (f'comptable@{s}.sn', rp('F'), rn(), RoleChoices.COMPTABLE, False),
                (f'caissier@{s}.sn', rp('M'), rn(), RoleChoices.CAISSIER, False),
                (f'surveillant1@{s}.sn', rp('M'), rn(), RoleChoices.SURVEILLANT, False),
                (f'surveillant2@{s}.sn', rp('F'), rn(), RoleChoices.SURVEILLANT, False),
            ]
            for j in range(1, 9):
                g = 'F' if j % 4 == 0 else 'M'
                roles_to_create.append((f'prof{j}@{s}.sn', rp(g), rn(), RoleChoices.PROFESSEUR, False))

            for email, prenom, nom, role, is_staff in roles_to_create:
                u, c = User.objects.get_or_create(
                    email=email,
                    defaults={'nom': nom, 'prenom': prenom,
                              'telephone': rtel(), 'is_staff': is_staff}
                )
                if c:
                    u.set_password('admin1234'); u.save()
                RoleUtilisateur.objects.get_or_create(
                    user=u, etablissement=etab,
                    defaults={'role': role}
                )

            self.stdout.write(f'     -> {etab.sigle}: directeur, prefet, comptable, caissier, 2 surveillants, 8 profs')

    # -- Éleves & inscriptions ---------------------------------
    def _eleves(self, etabs):
        self.stdout.write('   leves & inscriptions...')
        for etab in etabs:
            annee = AnneeScolaire.objects.get(etablissement=etab, is_active=True)
            caissier = User.objects.filter(
                roles__etablissement=etab, roles__role=RoleChoices.CAISSIER
            ).first()

            tf_sco, _ = TypeFrais.objects.get_or_create(
                etablissement=etab, libelle='Scolarite',
                defaults={'montant_defaut': 180000}
            )
            tf_ins, _ = TypeFrais.objects.get_or_create(
                etablissement=etab, libelle='Inscription',
                defaults={'montant_defaut': 25000}
            )

            classes = Classe.objects.filter(etablissement=etab, annee_scolaire=annee)
            total = 0

            for classe in classes:
                nb = random.randint(25, 38)
                for _ in range(nb):
                    sexe = 'M' if random.random() > 0.42 else 'F'
                    prenom = rp(sexe)
                    nom = rn()
                    annee_naiss = random.randint(2003, 2012)

                    # Retry en cas de collision de matricule (UUID court)
                    eleve = None
                    for _retry in range(5):
                        try:
                            from django.db import transaction as _tx
                            with _tx.atomic():
                                eleve = Eleve.objects.create(
                                    nom=nom, prenom=prenom, sexe=sexe,
                                    date_naissance=date(annee_naiss, random.randint(1, 12), random.randint(1, 28)),
                                    lieu_naissance=random.choice(['Dakar', 'Thies', 'Saint-Louis', 'Ziguinchor', 'Kaolack']),
                                )
                            break
                        except Exception:
                            continue
                    if eleve is None:
                        continue

                    inscription = Inscription.objects.create(
                        eleve=eleve, classe=classe,
                        etablissement=etab, annee_scolaire=annee,
                        statut='ACTIF',
                    )

                    # Frais de scolarite
                    montant = random.choice([150000, 175000, 200000])
                    frais = Frais.objects.create(
                        inscription=inscription,
                        type_frais=tf_sco,
                        montant=montant,
                    )

                    # Paiement partiel ou total
                    pct = random.choice([0.5, 0.75, 1.0, 1.0])
                    montant_paye = int(montant * pct)
                    if montant_paye > 0 and caissier:
                        Paiement.objects.create(
                            inscription=inscription,
                            frais=frais,
                            montant=montant_paye,
                            caissier=caissier,
                        )

                    # Parent (pour ~65% des eleves)
                    if random.random() > 0.35:
                        g_parent = 'F' if random.random() > 0.6 else 'M'
                        email_parent = f"p.{eleve.matricule.replace('-','').lower()}@mail.sn"
                        try:
                            parent = User.objects.create(
                                email=email_parent,
                                nom=nom,
                                prenom=rp(g_parent),
                                telephone=rtel(),
                            )
                            parent.set_password('admin1234')
                            parent.save()
                            RoleUtilisateur.objects.create(
                                user=parent, etablissement=etab,
                                role=RoleChoices.PARENT
                            )
                            LienParentEleve.objects.create(
                                parent=parent, eleve=eleve,
                                lien='PERE' if g_parent == 'M' else 'MERE',
                            )
                        except Exception:
                            pass

                    total += 1

            self.stdout.write(f'     -> {etab.sigle}: {total} eleves inscrits')

    # -- Notes -------------------------------------------------
    def _notes(self, etabs):
        self.stdout.write('   Notes...')
        total_notes = 0

        for etab in etabs:
            annee = AnneeScolaire.objects.get(etablissement=etab, is_active=True)
            prof = User.objects.filter(
                roles__etablissement=etab, roles__role=RoleChoices.PROFESSEUR
            ).first()

            # Periodes: 3 controles + 1 composition
            periodes_def = [
                (TypePeriode.CONTROLE, 1, '1er Controle', date(2025, 10, 20), date(2025, 11, 5)),
                (TypePeriode.CONTROLE, 2, '2eme Controle', date(2025, 11, 10), date(2025, 11, 25)),
                (TypePeriode.COMPOSITION, 1, '1ere Composition', date(2025, 12, 1), date(2025, 12, 20)),
            ]
            periodes = []
            for tp, num, lib, dd, df in periodes_def:
                p, _ = PeriodeEvaluation.objects.get_or_create(
                    etablissement=etab, annee_scolaire=annee,
                    type_periode=tp, numero=num,
                    defaults={'libelle': lib, 'date_debut': dd, 'date_fin': df}
                )
                periodes.append(p)

            # Saisir notes pour les 4 premieres classes seulement (perf)
            classes = Classe.objects.filter(etablissement=etab, annee_scolaire=annee)[:4]
            for classe in classes:
                inscriptions = Inscription.objects.filter(
                    classe=classe, statut='ACTIF'
                )[:15]  # 15 eleves max par classe
                matieres_classes = MatiereClasse.objects.filter(classe=classe)[:6]

                for inscription in inscriptions:
                    for mc in matieres_classes:
                        for periode in periodes:
                            try:
                                _, c = Note.objects.get_or_create(
                                    inscription=inscription,
                                    matiere_classe=mc,
                                    periode=periode,
                                    defaults={
                                        'valeur': round(random.uniform(4, 20), 2),
                                        'saisi_par': prof,
                                    }
                                )
                                if c:
                                    total_notes += 1
                            except Exception:
                                pass

        self.stdout.write(f'     -> {total_notes} notes saisies')

    # -- Notifications -----------------------------------------
    def _notifications(self, etabs):
        self.stdout.write('   Notifications...')
        for etab in etabs:
            directeur = User.objects.filter(
                roles__etablissement=etab, roles__role=RoleChoices.DIRECTEUR
            ).first()
            prefet = User.objects.filter(
                roles__etablissement=etab, roles__role=RoleChoices.PREFET
            ).first()

            notifs = [
                (directeur, TypeNotification.MODIFICATION_NOTE_SOUMISE,
                 'Demande de modification', 'Une demande de modification de note est en attente de validation.', False),
                (directeur, TypeNotification.CLOTURE_OUBLIEE,
                 'Cloture oubliee', "La caisse d'hier n'a pas ete cloturee. Veuillez regulariser.", False),
                (directeur, TypeNotification.FICHE_PAIE_A_VALIDER,
                 'Fiches de paie', '3 fiches de paie du mois de novembre sont pretes a valider.', True),
                (prefet, TypeNotification.NOTES_NON_SAISIES,
                 'Notes manquantes', 'Le professeur de Mathematiques 3eme B n\'a pas encore saisi ses notes.', False),
                (prefet, TypeNotification.ALERTE_RETARDS_ELEVE,
                 'Retards repetes', 'L\'eleve Moussa Diallo (6eme A) a accumule 5 retards ce mois.', False),
            ]

            for dest, type_n, titre, msg, lue in notifs:
                if dest:
                    Notification.objects.get_or_create(
                        destinataire=dest, type_notification=type_n, titre=titre,
                        defaults={'message': msg, 'lue': lue}
                    )

        self.stdout.write('     -> Notifications creees')
