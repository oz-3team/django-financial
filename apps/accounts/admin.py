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
        return obj.owner.email

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

    # 1️⃣ Transfer id
    # 보통 외부 송금/이체 시스템에서 생성된 고유 ID
    # 예: 은행 API에서 받아오는 트랜잭션 ID
    #
    # Admin 입력 시 테스트용이면 그냥 임의 값 넣어도 됩니다.
    # 예: TRX20250830-001
    #
    # 2️⃣ Idempotency key
    # 중복 방지를 위한 고유 키
    # 같은 요청이 여러 번 들어와도 1회만 처리되도록 하는 값
    # 테스트용: TEST1 등 임의 문자열 가능
    #
    # 3️⃣ External ref
    # 외부 참조 번호, 회계나 송금용으로 연결되는 다른 시스템의 ID
    # 테스트용: EXT20250830-001
    #
    # 4️⃣ Counterparty
    # 거래 상대방 계좌 (ForeignKey)
    # Admin 폼에서 드롭다운으로 선택 가능하거나 계좌 번호 입력
    # 테스트용: 존재하는 Account 객체 선택
    #
    # 5️⃣ Metadata
    # 추가 정보나 JSON 형태 데이터를 넣을 수 있는 필드
    # 테스트용: { "note": "테스트 거래" } 정도
