from django.contrib import admin
from .models import Account, TransactionHistory


# ----------------------------
# Account Admin
# ----------------------------


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_owner_email",
        "name",
        "number",
        "currency",
        "balance",
        "status",
        "created_at",
    )
    search_fields = ("owner__email", "name", "number")
    list_filter = ("currency", "status")
    readonly_fields = ("balance", "created_at", "updated_at")

    def get_owner_email(self, obj):
        return obj.owner.emai

    get_owner_email.short_description = "Owner Email"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("owner")


# ----------------------------
# TransactionHistory Admin
# ----------------------------
@admin.register(TransactionHistory)
class TransactionHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "account",
        "tx_type",
        "amount",
        "currency",
        "occurred_at",
        "posted_at",
        "counterparty",
    )
    list_filter = (
        "tx_type",
        "account",
        "occurred_at",
        "currency",
    )
    search_fields = (
        "account__number",
        "counterparty__number",
        "description",
        "external_ref",
    )
    ordering = ("-occurred_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("account", "counterparty")
