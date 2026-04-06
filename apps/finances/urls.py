from django.urls import path
from . import views

urlpatterns = [
    path('<int:etablissement_pk>/types-frais/', views.TypeFraisListCreateView.as_view(), name='type-frais-list'),
    path('frais/', views.FraisListCreateView.as_view(), name='frais-list'),
    path('payer/', views.EncaisserPaiementView.as_view(), name='encaisser-paiement'),
    path('inscriptions/<int:inscription_pk>/situation/', views.SituationFinanciereView.as_view(), name='situation-financiere'),
    path('<int:etablissement_pk>/clotures/', views.ClotureCaisseListView.as_view(), name='cloture-list'),
    path('<int:etablissement_pk>/clotures/effectuer/', views.EffectuerClotureCaisseView.as_view(), name='cloture-effectuer'),
    path('<int:etablissement_pk>/clotures/forcer/', views.ForcerClotureCaisseView.as_view(), name='cloture-forcer'),
]
