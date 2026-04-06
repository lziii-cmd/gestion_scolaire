from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import JournalAudit
from .serializers import JournalAuditSerializer
from apps.accounts.permissions import IsSuperAdmin


class JournalAuditListView(generics.ListAPIView):
    """
    Journal d'audit en lecture seule.
    Accessible uniquement au Super Admin.
    """
    queryset = JournalAudit.objects.all()
    serializer_class = JournalAuditSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['action', 'module', 'utilisateur', 'etablissement_id_au_moment']
    ordering_fields = ['date_heure']
    ordering = ['-date_heure']
