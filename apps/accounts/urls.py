from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.UserListCreateView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('me/', views.MeView.as_view(), name='me'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('roles/', views.RoleUtilisateurListCreateView.as_view(), name='role-list'),
    path('roles/<int:pk>/', views.RoleUtilisateurDetailView.as_view(), name='role-detail'),
    path('sessions/', views.SessionsActivesView.as_view(), name='sessions-list'),
    path('sessions/<int:session_id>/deconnecter/', views.DeconnecterSessionView.as_view(), name='session-deconnecter'),
]
