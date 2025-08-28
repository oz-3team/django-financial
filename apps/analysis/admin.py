from django.contrib import admin
from .models import Analysis


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    """
    Analysis 관리자 화면 설정
    - list_display: 관리자 화면에서 보여줄 컬럼
    - list_filter: 오른쪽 사이드바 필터
    - search_fields: FK 포함 검색 가능
    """
    list_display = (
        'user',
        'analysis_target',
        'period_type',
        'start_date',
        'end_date',
        'created_at',
        'updated_at',  # 수정일도 추가
    )
    list_filter = (
        'period_type',
        'analysis_target',
        'created_at',  # 날짜 필터 추가
    )
    search_fields = (
        'user__username',  # FK user 참조
        'user__email',     # 이메일로도 검색 가능
        'description',     # 분석 설명 검색 가능
    )
    ordering = ('-created_at',)  # 기본 정렬: 최신순

