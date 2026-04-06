from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Etablissement, Cycle, Niveau, Serie, AnneeScolaire, JourFerie
from .serializers import (
    EtablissementSerializer, EtablissementListSerializer, CycleSerializer,
    NiveauSerializer, SerieSerializer, AnneeScolaireSerializer, JourFerieSerializer,
)
from apps.accounts.permissions import IsSuperAdmin, IsDirecteur


class EtablissementListCreateView(generics.ListCreateAPIView):
    queryset = Etablissement.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EtablissementSerializer
        return EtablissementListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSuperAdmin()]
        return [IsAuthenticated()]


class EtablissementDetailView(generics.RetrieveUpdateAPIView):
    queryset = Etablissement.objects.all()
    serializer_class = EtablissementSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]


class CycleListCreateView(generics.ListCreateAPIView):
    serializer_class = CycleSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        return Cycle.objects.filter(
            etablissement_id=self.kwargs['etablissement_pk']
        ).prefetch_related('niveaux')


class NiveauListCreateView(generics.ListCreateAPIView):
    serializer_class = NiveauSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        return Niveau.objects.filter(cycle_id=self.kwargs['cycle_pk'])


class SerieListCreateView(generics.ListCreateAPIView):
    queryset = Serie.objects.all()
    serializer_class = SerieSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSuperAdmin()]
        return [IsAuthenticated()]


class AnneeScolaireListCreateView(generics.ListCreateAPIView):
    serializer_class = AnneeScolaireSerializer
    permission_classes = [IsAuthenticated, IsDirecteur]

    def get_queryset(self):
        return AnneeScolaire.objects.filter(
            etablissement_id=self.kwargs['etablissement_pk']
        ).order_by('-date_debut')


class AnneeScolaireDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = AnneeScolaireSerializer
    permission_classes = [IsAuthenticated, IsDirecteur]

    def get_queryset(self):
        return AnneeScolaire.objects.filter(
            etablissement_id=self.kwargs['etablissement_pk']
        )


class JourFerieListCreateView(generics.ListCreateAPIView):
    serializer_class = JourFerieSerializer
    permission_classes = [IsAuthenticated, IsDirecteur]

    def get_queryset(self):
        return JourFerie.objects.filter(
            etablissement_id=self.kwargs['etablissement_pk']
        )
