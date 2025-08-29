from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI Schema 설정
schema_view = get_schema_view(
    openapi.Info(
        title="My Project API",
        default_version="v1",
        description="API documentation for My Project",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # 기존 URL 유지
    path("admin/", admin.site.urls),
    path("api/users/", include("apps.users.urls")),
    path("api/notifications/", include("apps.notification.urls")),
    path("api/analysis/", include("apps.analysis.urls")),
    # Swagger UI
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    # Redoc UI
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
