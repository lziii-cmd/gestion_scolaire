from django.urls import path
from . import views

urlpatterns = [
    path('<int:etablissement_pk>/periodes/', views.PeriodeListCreateView.as_view(), name='periode-list'),
    path('', views.NoteListView.as_view(), name='note-list'),
    path('saisir/', views.SaisirNoteView.as_view(), name='note-saisir'),
    path('modifications/', views.ModificationNoteListView.as_view(), name='modification-list'),
    path('modifications/<int:modification_pk>/valider/', views.ValiderModificationNoteView.as_view(), name='modification-valider'),
]
