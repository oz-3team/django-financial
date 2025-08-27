from django.contrib import admin
from .models import Analysis


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ('user', 'analysis_target', 'period_type', 'start_date', 'end_date', 'created_at')
    list_filter = ('period_type', 'analysis_target')
    search_fields = ('user__username',)