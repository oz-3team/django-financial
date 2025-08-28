from django.contrib import admin
from .models import Analysis
from ..accounts.models import TransactionHistory


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

@admin.register(TransactionHistory)
class TransactionHistoryAdmin(admin.ModelAdmin):
    """
    TransactionHistory 관리자 화면 설정
    - list_display: 주요 컬럼 표시
    - list_filter: 필터링 가능, FK 필드 포함
    - search_fields: FK 참조 필드 검색 가능
    - ordering: 기본 정렬
    """
    list_display = (
        'id',
        'account',
        'tx_type',
        'amount',
        'currency',
        'occurred_at',
        'posted_at',
        'counterparty',  # 상대 계좌도 표시
    )
    list_filter = (
        'tx_type',
        'account',
        'occurred_at',
        'currency',
    )
    search_fields = (
        'account__number',      # FK 참조
        'counterparty__number', # 상대 계좌 검색 가능
        'description',
        'external_ref',
    )
    ordering = ('-occurred_at',)