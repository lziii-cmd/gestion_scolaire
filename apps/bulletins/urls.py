from django.urls import path
from . import views

urlpatterns = [
    path('', views.BulletinListView.as_view(), name='bulletin-list'),
    path('<int:pk>/', views.BulletinDetailView.as_view(), name='bulletin-detail'),
    path('generer/<int:classe_id>/<int:periode_id>/', views.GenererBulletinsClasseView.as_view(), name='bulletin-generer'),
    path('<int:bulletin_pk>/valider/', views.ValiderBulletinView.as_view(), name='bulletin-valider'),
    path('<int:bulletin_pk>/publier/', views.PublierBulletinView.as_view(), name='bulletin-publier'),
    path('<int:bulletin_pk>/debloquer/', views.DebloquerBulletinView.as_view(), name='bulletin-debloquer'),
]
