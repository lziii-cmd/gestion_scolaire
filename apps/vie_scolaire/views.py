from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import AbsenceEleve, RetardEleve, TypeSanction, Sanction
from .serializers import (
    AbsenceEleveSerializer, RetardEleveSerializer,
    TypeSanctionSerializer, SanctionSerializer,
)
from apps.accounts.permissions import IsSurveillant, IsDirecteur


class AbsenceListCreateView(generics.ListCreateAPIView):
    serializer_class = AbsenceEleveSerializer
    permission_classes = [IsAuthenticated, IsSurveillant]

    def get_queryset(self):
        qs = AbsenceEleve.objects.select_related('inscription__eleve')
        inscription_id = self.request.query_params.get('inscription')
        classe_id = self.request.query_params.get('classe')
        date = self.request.query_params.get('date')
        if inscription_id:
            qs = qs.filter(inscription_id=inscription_id)
        if classe_id:
            qs = qs.filter(inscription__classe_id=classe_id)
        if date:
            qs = qs.filter(date=date)
        return qs

    def perform_create(self, serializer):
        serializer.save(enregistre_par=self.request.user)


class RetardListCreateView(generics.ListCreateAPIView):
    serializer_class = RetardEleveSerializer
    permission_classes = [IsAuthenticated, IsSurveillant]

    def get_queryset(self):
        qs = RetardEleve.objects.select_related('inscription__eleve')
        inscription_id = self.request.query_params.get('inscription')
        if inscription_id:
            qs = qs.filter(inscription_id=inscription_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(enregistre_par=self.request.user)


class TypeSanctionListCreateView(generics.ListCreateAPIView):
    serializer_class = TypeSanctionSerializer
    permission_classes = [IsAuthenticated, IsDirecteur]

    def get_queryset(self):
        return TypeSanction.objects.filter(
            etablissement_id=self.kwargs['etablissement_pk']
        )


class SanctionListCreateView(generics.ListCreateAPIView):
    serializer_class = SanctionSerializer
    permission_classes = [IsAuthenticated, IsSurveillant]

    def get_queryset(self):
        qs = Sanction.objects.select_related('inscription__eleve', 'type_sanction')
        inscription_id = self.request.query_params.get('inscription')
        if inscription_id:
            qs = qs.filter(inscription_id=inscription_id)
        return qs

    def perform_create(self, serializer):
        type_sanction = serializer.validated_data['type_sanction']
        apparait = serializer.validated_data.get(
            'apparait_bulletin',
            type_sanction.apparait_bulletin_defaut
        )
        serializer.save(prononce_par=self.request.user, apparait_bulletin=apparait)
