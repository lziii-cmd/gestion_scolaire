from django.db import migrations


def convert_admin_informatique(apps, schema_editor):
    RoleUtilisateur = apps.get_model('accounts', 'RoleUtilisateur')
    RoleUtilisateur.objects.filter(role='ADMIN_INFORMATIQUE').update(role='DIRECTEUR')


def reverse_convert(apps, schema_editor):
    # Pas de reverse possible sans savoir qui était ADMIN_INFORMATIQUE avant
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_rename_super_admin_role'),
    ]

    operations = [
        migrations.RunPython(convert_admin_informatique, reverse_code=reverse_convert),
    ]
