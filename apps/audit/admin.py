from django.contrib import admin
from .models import JournalAudit


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ['date_heure', 'utilisateur_email', 'role_au_moment', 'action', 'module', 'ip_address']
    list_filter = ['action', 'module']
    search_fields = ['utilisateur_email', 'enregistrement_id']
    readonly_fields = [f.name for f in JournalAudit._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
