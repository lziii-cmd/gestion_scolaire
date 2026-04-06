from django.urls import path
from . import views

urlpatterns = [
    path('absences/', views.AbsenceListCreateView.as_view(), name='absence-list'),
    path('retards/', views.RetardListCreateView.as_view(), name='retard-list'),
    path('<int:etablissement_pk>/types-sanctions/', views.TypeSanctionListCreateView.as_view(), name='type-sanction-list'),
    path('sanctions/', views.SanctionListCreateView.as_view(), name='sanction-list'),
]
