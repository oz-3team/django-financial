import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone

CURRENCY_CHOICES = [
    ("KRW", "KRW"),
    ("USD", "USD"),
]


class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    name = models.CharField(max_length=100)  # 은행 이름/계좌명
    number = models.CharField(max_length=32, unique=True)  # 계좌번호/식별자
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="KRW")
    balance = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("0.00")
    )
    status = models.CharField(
        max_length=16, default="ACTIVE"
    )  # ACTIVE, FROZEN, CLOSED 등
    version = models.PositiveIntegerField(default=0)  # 낙관적 락 보조용
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner"]),
            models.Index(fields=["number"]),
        ]

    def __str__(self):
        return f"{self.name}({self.number}) {self.currency}"


class TransactionHistory(models.Model):
    class TxType(models.TextChoices):
        DEPOSIT = "DEPOSIT", "DEPOSIT"
        WITHDRAW = "WITHDRAW", "WITHDRAW"
        TRANSFER_OUT = "TRANSFER_OUT", "TRANSFER_OUT"
        TRANSFER_IN = "TRANSFER_IN", "TRANSFER_IN"
        FEE = "FEE", "FEE"
        REVERSAL = "REVERSAL", "REVERSAL"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    tx_type = models.CharField(max_length=16, choices=TxType.choices)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    running_balance = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(
        max_length=3, choices=[("KRW", "KRW"), ("USD", "USD")], default="KRW"
    )
    description = models.CharField(max_length=255, blank=True, default="")
    occurred_at = models.DateTimeField(default=timezone.now)
    posted_at = models.DateTimeField(auto_now_add=True)

    transfer_id = models.UUIDField(null=True, blank=True, db_index=True)
    idempotency_key = models.CharField(max_length=64, null=True, blank=True)
    external_ref = models.CharField(
        max_length=64, unique=True, default=uuid.uuid4, editable=False
    )
    counterparty = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="counter_transactions",
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["account", "-occurred_at"]),
            models.Index(fields=["transfer_id"]),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="amount_gt_zero"),
        ]
        unique_together = [
            ("account", "idempotency_key"),
        ]

    def __str__(self):
        return f"{self.tx_type} {self.amount} {self.currency} ({self.account.number})"
