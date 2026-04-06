from rest_framework import serializers
from .models import JournalAudit


class JournalAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalAudit
        fields = [
            'id', 'utilisateur', 'utilisateur_email', 'role_au_moment',
            'etablissement_id_au_moment', 'action', 'module',
            'table_concernee', 'enregistrement_id',
            'anciennes_valeurs', 'nouvelles_valeurs',
            'ip_address', 'user_agent', 'date_heure',
        ]
        read_only_fields = fields
