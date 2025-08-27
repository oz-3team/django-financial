from django.contrib import admin
from django.urls import path, include

from apps.analysis import urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/notifications/', include('apps.notification.urls')),
    path('api/analysis/', include('apps.analysis.urls')),
]
