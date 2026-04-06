from django.urls import path
from . import views

urlpatterns = [
    path('', views.MatiereListCreateView.as_view(), name='matiere-list'),
    path('<int:pk>/', views.MatiereDetailView.as_view(), name='matiere-detail'),
    path('classes/', views.MatiereClasseListCreateView.as_view(), name='matiere-classe-list'),
    path('classes/<int:pk>/', views.MatiereClasseDetailView.as_view(), name='matiere-classe-detail'),
]
