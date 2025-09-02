from django.apps import AppConfig


class AnalysisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analysis"

    def ready(self):
        # 시그널 등록
        import apps.analysis.signals  # noqa: F401
