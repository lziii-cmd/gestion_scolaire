from django.urls import path
from . import views

urlpatterns = [
    path('', views.EtablissementListCreateView.as_view(), name='etablissement-list'),
    path('<int:pk>/', views.EtablissementDetailView.as_view(), name='etablissement-detail'),

    path('<int:etablissement_pk>/cycles/', views.CycleListCreateView.as_view(), name='cycle-list'),
    path('<int:etablissement_pk>/cycles/<int:cycle_pk>/niveaux/', views.NiveauListCreateView.as_view(), name='niveau-list'),

    path('<int:etablissement_pk>/annees/', views.AnneeScolaireListCreateView.as_view(), name='annee-list'),
    path('<int:etablissement_pk>/annees/<int:pk>/', views.AnneeScolaireDetailView.as_view(), name='annee-detail'),

    path('<int:etablissement_pk>/jours-feries/', views.JourFerieListCreateView.as_view(), name='jour-ferie-list'),

    path('series/', views.SerieListCreateView.as_view(), name='serie-list'),
]
