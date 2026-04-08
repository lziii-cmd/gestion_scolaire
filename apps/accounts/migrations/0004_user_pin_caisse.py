from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_remove_admin_informatique_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='pin_caisse',
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
