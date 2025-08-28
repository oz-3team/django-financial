from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/notifications/', include('apps.notification.urls')),
    path('api/analysis/', include('apps.analysis.urls')),
]
