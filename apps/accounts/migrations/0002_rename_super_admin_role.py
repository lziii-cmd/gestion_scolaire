from django.db import migrations


def rename_super_admin(apps, schema_editor):
    RoleUtilisateur = apps.get_model('accounts', 'RoleUtilisateur')
    RoleUtilisateur.objects.filter(role='SUPER_ADMIN').update(role='ADMIN_GROUPE')


def reverse_rename(apps, schema_editor):
    RoleUtilisateur = apps.get_model('accounts', 'RoleUtilisateur')
    RoleUtilisateur.objects.filter(role='ADMIN_GROUPE').update(role='SUPER_ADMIN')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(rename_super_admin, reverse_code=reverse_rename),
    ]
