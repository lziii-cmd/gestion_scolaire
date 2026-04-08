from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scolarite', '0002_inscription_en_attente_validation'),
    ]

    operations = [
        migrations.AddField(
            model_name='eleve',
            name='type_eleve',
            field=models.CharField(
                choices=[
                    ('ORDINAIRE', 'Ordinaire'),
                    ('BOURSIER', 'Boursier'),
                    ('AUDITEUR', 'Auditeur libre'),
                ],
                default='ORDINAIRE',
                max_length=20,
            ),
        ),
    ]
