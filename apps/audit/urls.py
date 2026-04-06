from django.urls import path
from . import views

urlpatterns = [
    path('', views.JournalAuditListView.as_view(), name='journal-audit'),
]
