from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0002_modificationpaiement_statut'),
    ]

    operations = [
        migrations.AddField(
            model_name='typefrais',
            name='categorie',
            field=models.CharField(
                choices=[
                    ('INSCRIPTION', "Frais d'inscription"),
                    ('SCOLARITE_MENSUELLE', 'Scolarité mensuelle'),
                    ('AUTRE', 'Autre'),
                ],
                default='AUTRE',
                max_length=20,
            ),
        ),
    ]
