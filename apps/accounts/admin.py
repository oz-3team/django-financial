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
    list_display = ('id', 'account', 'tx_type', 'amount', 'running_balance', 'occurred_at', 'posted_at')
    list_filter = ('tx_type', 'currency')
    search_fields = ('account__number', 'account__owner__email', 'description')
