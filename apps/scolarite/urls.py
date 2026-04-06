from django.urls import path
from . import views

urlpatterns = [
    path('eleves/', views.EleveListCreateView.as_view(), name='eleve-list'),
    path('eleves/<int:pk>/', views.EleveDetailView.as_view(), name='eleve-detail'),

    path('<int:etablissement_pk>/classes/', views.ClasseListCreateView.as_view(), name='classe-list'),
    path('<int:etablissement_pk>/inscriptions/', views.InscriptionListCreateView.as_view(), name='inscription-list'),
    path('inscriptions/<int:pk>/', views.InscriptionDetailView.as_view(), name='inscription-detail'),

    path('lier-parent/', views.LierParentEleveView.as_view(), name='lier-parent'),

    path('inscriptions/<int:inscription_pk>/initier-transfert/', views.InitierTransfertView.as_view(), name='initier-transfert'),
    path('transferts/<int:transfert_pk>/confirmer/', views.ConfirmerTransfertView.as_view(), name='confirmer-transfert'),
]
