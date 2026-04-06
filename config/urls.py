from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from apps.accounts.views import CustomTokenObtainPairView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Web Interface
    path('', include('apps.web.urls')),

    # Auth
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Apps
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/etablissements/', include('apps.etablissements.urls')),
    path('api/scolarite/', include('apps.scolarite.urls')),
    path('api/matieres/', include('apps.matieres.urls')),
    path('api/notes/', include('apps.notes.urls')),
    path('api/bulletins/', include('apps.bulletins.urls')),
    path('api/finances/', include('apps.finances.urls')),
    path('api/paie/', include('apps.paie.urls')),
    path('api/vie-scolaire/', include('apps.vie_scolaire.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/audit/', include('apps.audit.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
