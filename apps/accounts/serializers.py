from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils import timezone
from django.conf import settings
from .models import User, RoleUtilisateur, SessionActive


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        from django.contrib.auth import authenticate
        email = attrs.get('email') or attrs.get(self.username_field)
        password = attrs.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Identifiants invalides.")

        if user.is_locked():
            raise serializers.ValidationError(
                f"Compte bloqué. Réessayez après {user.locked_until.strftime('%H:%M')}."
            )

        if not user.check_password(password):
            user.failed_login_attempts += 1
            max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
            if user.failed_login_attempts >= max_attempts:
                lockout = getattr(settings, 'LOGIN_LOCKOUT_DURATION', 30)
                user.locked_until = timezone.now() + timezone.timedelta(minutes=lockout)
            user.save(update_fields=['failed_login_attempts', 'locked_until'])
            raise serializers.ValidationError("Identifiants invalides.")

        if not user.is_active:
            raise serializers.ValidationError("Ce compte est désactivé.")

        # Réinitialiser les tentatives en cas de succès
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=['failed_login_attempts', 'locked_until'])

        attrs[self.username_field] = email
        data = super().validate(attrs)

        data['must_change_password'] = user.must_change_password
        data['user'] = UserSerializer(user).data

        # Récupérer les établissements de l'utilisateur
        roles = RoleUtilisateur.objects.filter(user=user, is_active=True).select_related('etablissement')
        etablissements = []
        for r in roles:
            if r.etablissement and r.etablissement not in [e['id'] for e in etablissements]:
                etablissements.append({
                    'id': r.etablissement.id,
                    'nom': r.etablissement.nom,
                    'sigle': r.etablissement.sigle,
                    'role': r.role,
                })
        data['etablissements'] = etablissements

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['nom_complet'] = user.nom_complet
        return token


class UserSerializer(serializers.ModelSerializer):
    nom_complet = serializers.ReadOnlyField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'nom', 'prenom', 'nom_complet',
            'telephone', 'photo', 'is_active', 'must_change_password',
            'date_joined', 'roles',
        ]
        read_only_fields = ['date_joined', 'must_change_password']

    def get_roles(self, obj):
        return RoleUtilisateur.objects.filter(
            user=obj, is_active=True
        ).values('role', 'etablissement__sigle', 'etablissement__nom')


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['email', 'nom', 'prenom', 'telephone', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    ancien_mot_de_passe = serializers.CharField()
    nouveau_mot_de_passe = serializers.CharField(min_length=8)

    def validate_ancien_mot_de_passe(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mot de passe actuel incorrect.")
        return value


class RoleUtilisateurSerializer(serializers.ModelSerializer):
    user_nom = serializers.ReadOnlyField(source='user.nom_complet')
    etablissement_sigle = serializers.ReadOnlyField(source='etablissement.sigle')

    class Meta:
        model = RoleUtilisateur
        fields = [
            'id', 'user', 'user_nom', 'etablissement', 'etablissement_sigle',
            'role', 'cycle', 'is_active', 'date_affectation',
        ]


class SessionActiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionActive
        fields = ['id', 'ip_address', 'user_agent', 'created_at', 'last_activity', 'is_active']
