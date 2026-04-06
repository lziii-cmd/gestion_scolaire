from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Matiere, MatiereClasse
from .serializers import MatiereSerializer, MatiereClasseSerializer
from apps.accounts.permissions import IsSuperAdmin, IsPrefetOrDirecteur


class MatiereListCreateView(generics.ListCreateAPIView):
    queryset = Matiere.objects.filter(is_active=True)
    serializer_class = MatiereSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSuperAdmin()]
        return [IsAuthenticated()]


class MatiereDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Matiere.objects.all()
    serializer_class = MatiereSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]


class MatiereClasseListCreateView(generics.ListCreateAPIView):
    serializer_class = MatiereClasseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MatiereClasse.objects.select_related('matiere', 'classe', 'serie', 'professeur')
        classe_id = self.request.query_params.get('classe')
        if classe_id:
            qs = qs.filter(classe_id=classe_id)
        return qs

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsPrefetOrDirecteur()]
        return [IsAuthenticated()]


class MatiereClasseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MatiereClasse.objects.all()
    serializer_class = MatiereClasseSerializer
    permission_classes = [IsAuthenticated, IsPrefetOrDirecteur]
