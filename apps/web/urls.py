from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('eleves/', views.eleves_list, name='eleves_list'),
    path('eleves/<int:eleve_id>/', views.eleve_detail, name='eleve_detail'),
    path('professeurs/', views.professeurs_list, name='professeurs_list'),
    path('notes/', views.notes_list, name='notes_list'),
    path('notes/saisir/', views.notes_sauvegarder, name='notes_sauvegarder'),
    path('bulletins/', views.bulletins_list, name='bulletins_list'),
    path('finances/', views.finances_index, name='finances_index'),
    path('finances/paiement/<int:paiement_id>/modifier/', views.finances_demander_modif, name='finances_demander_modif'),
    path('finances/validations/', views.finances_validations, name='finances_validations'),
    path('finances/validations/<int:demande_id>/traiter/', views.finances_valider, name='finances_valider'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('absences/', views.absences_list, name='absences_list'),
    path('edt/', views.emploi_du_temps, name='emploi_du_temps'),
    path('profil/', views.mon_profil, name='mon_profil'),
    path('parametres/', views.parametres, name='parametres'),
    path('etablissement/reset/', views.reset_etablissement, name='reset_etablissement'),
    path('etablissement/<int:etab_id>/changer/', views.changer_etablissement, name='changer_etablissement'),
    path('extra-usage/', views.extra_usage, name='extra_usage'),
]
