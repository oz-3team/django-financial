from django.contrib import admin
from .models import Account, TransactionHistory

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_owner_email', 'name', 'number', 'currency', 'balance', 'status', 'created_at')
    search_fields = ('owner__email', 'name', 'number')
    list_filter = ('currency', 'status')
    readonly_fields = ('balance', 'created_at', 'updated_at')

    def get_owner_email(self, obj):
        return obj.owner.email
    get_owner_email.short_description = 'Owner Email'


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