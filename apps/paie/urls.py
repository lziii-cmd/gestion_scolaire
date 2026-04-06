from django.urls import path
from . import views

urlpatterns = [
    path('<int:etablissement_pk>/affectations/', views.AffectationListCreateView.as_view(), name='affectation-list'),
    path('emploi-du-temps/', views.EmploiDuTempsListCreateView.as_view(), name='edt-list'),
    path('<int:etablissement_pk>/emargement/', views.EmargementJourView.as_view(), name='emargement-jour'),
    path('<int:etablissement_pk>/fiches-de-paie/', views.FicheDePaieListView.as_view(), name='fiche-paie-list'),
    path('fiches-de-paie/<int:fiche_pk>/valider/', views.ValiderFicheDePaieView.as_view(), name='fiche-paie-valider'),
    path('fiches-de-paie/<int:fiche_pk>/payer/', views.PayerFicheDePaieView.as_view(), name='fiche-paie-payer'),
]
