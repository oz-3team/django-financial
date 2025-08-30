from django.apps import AppConfig


class NotificationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notification"

    def ready(self):
        # 앱이 준비될 때 signals 모듈을 임포트하여 시그널 등록
        import apps.notification.signals  # noqa: F401
