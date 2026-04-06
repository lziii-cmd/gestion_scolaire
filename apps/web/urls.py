from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('eleves/', views.eleves_list, name='eleves_list'),
    path('notes/', views.notes_list, name='notes_list'),
    path('bulletins/', views.bulletins_list, name='bulletins_list'),
    path('finances/', views.finances_index, name='finances_index'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('etablissement/<int:etab_id>/changer/', views.changer_etablissement, name='changer_etablissement'),
]
