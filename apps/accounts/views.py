from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils import timezone

from .models import User, RoleUtilisateur, SessionActive
from .serializers import (
    CustomTokenObtainPairSerializer, UserSerializer, UserCreateSerializer,
    ChangePasswordSerializer, RoleUtilisateurSerializer, SessionActiveSerializer,
)
from .permissions import IsSuperAdmin, IsPrefetOrDirecteur


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.all().order_by('nom', 'prenom')
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def destroy(self, request, *args, **kwargs):
        # Soft delete — désactivation uniquement
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['nouveau_mot_de_passe'])
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])
        return Response({'detail': 'Mot de passe modifié avec succès.'})


class RoleUtilisateurListCreateView(generics.ListCreateAPIView):
    serializer_class = RoleUtilisateurSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        qs = RoleUtilisateur.objects.select_related('user', 'etablissement', 'cycle')
        user_id = self.request.query_params.get('user')
        etablissement_id = self.request.query_params.get('etablissement')
        if user_id:
            qs = qs.filter(user_id=user_id)
        if etablissement_id:
            qs = qs.filter(etablissement_id=etablissement_id)
        return qs


class RoleUtilisateurDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RoleUtilisateur.objects.all()
    serializer_class = RoleUtilisateurSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]


class SessionsActivesView(generics.ListAPIView):
    serializer_class = SessionActiveSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SessionActive.objects.filter(user=self.request.user, is_active=True)


class DeconnecterSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, session_id):
        try:
            session = SessionActive.objects.get(pk=session_id, user=request.user)
            session.is_active = False
            session.save(update_fields=['is_active'])
            return Response({'detail': 'Session déconnectée.'})
        except SessionActive.DoesNotExist:
            return Response({'detail': 'Session introuvable.'}, status=status.HTTP_404_NOT_FOUND)
