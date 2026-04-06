from rest_framework import serializers
from .models import Notification, TokenFCM


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'type_notification', 'titre', 'message',
            'lue', 'date_lecture', 'objet_type', 'objet_id', 'created_at',
        ]
        read_only_fields = ['created_at']


class TokenFCMSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenFCM
        fields = ['id', 'token', 'created_at']
        read_only_fields = ['created_at']
