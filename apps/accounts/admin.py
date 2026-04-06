from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, RoleUtilisateur, SessionActive


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['email']
    list_display = ['email', 'nom', 'prenom', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff']
    search_fields = ['email', 'nom', 'prenom']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('nom', 'prenom', 'telephone', 'photo')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'must_change_password')}),
        ('Sécurité', {'fields': ('failed_login_attempts', 'locked_until')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nom', 'prenom', 'password1', 'password2'),
        }),
    )


@admin.register(RoleUtilisateur)
class RoleUtilisateurAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'etablissement', 'cycle', 'is_active']
    list_filter = ['role', 'is_active', 'etablissement']
    search_fields = ['user__email', 'user__nom']


@admin.register(SessionActive)
class SessionActiveAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'created_at', 'last_activity', 'is_active']
    list_filter = ['is_active']
