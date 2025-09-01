from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "created_at")
    list_filter = ("is_read", "created_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # user 관계 미리 가져오기 → N+1 문제 방지
        return qs.select_related("user")
