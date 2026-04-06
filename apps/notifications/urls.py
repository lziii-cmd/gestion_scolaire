from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('<int:notif_pk>/lire/', views.MarquerLueView.as_view(), name='notification-lire'),
    path('tout-lire/', views.MarquerToutesLuesView.as_view(), name='notification-tout-lire'),
    path('fcm/enregistrer/', views.EnregistrerTokenFCMView.as_view(), name='fcm-enregistrer'),
]
