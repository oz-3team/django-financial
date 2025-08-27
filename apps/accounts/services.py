from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import F
from django.utils import timezone
import uuid

from .models import Account, TransactionHistory as TH

TWO_DP = Decimal("0.01")

def _q(amount: Decimal) -> Decimal:
    # 소수점 2자리 반올림 고정
    return (Decimal(amount)).quantize(TWO_DP, rounding=ROUND_HALF_UP)

def _ensure_currency(account: Account, currency: str):
    if account.currency != currency:
        raise ValueError(f"Currency mismatch: account={account.currency}, tx={currency}")

@transaction.atomic
def deposit(account_id, amount, currency="KRW", description="", idempotency_key=None, metadata=None):
    amount = _q(amount)
    if amount <= 0:
        raise ValueError("amount must be > 0")

    acc = Account.objects.select_for_update().get(pk=account_id)
    _ensure_currency(acc, currency)

    # 멱등성: 동일 키가 이미 존재하면 그대로 반환
    if idempotency_key:
        existing = TH.objects.filter(account=acc, idempotency_key=idempotency_key).first()
        if existing:
            return existing

    new_balance = _q(acc.balance + amount)

    tx = TH.objects.create(
        account=acc,
        tx_type=TH.TxType.DEPOSIT,
        amount=amount,
        running_balance=new_balance,
        currency=currency,
        description=description,
        occurred_at=timezone.now(),
        idempotency_key=idempotency_key,
        metadata=metadata or {},
    )

    # 잔액/버전 갱신
    Account.objects.filter(pk=acc.pk).update(balance=new_balance, version=F("version") + 1)
    return tx


@transaction.atomic
def withdraw(account_id, amount, currency="KRW", description="", idempotency_key=None, metadata=None):
    amount = _q(amount)
    if amount <= 0:
        raise ValueError("amount must be > 0")

    acc = Account.objects.select_for_update().get(pk=account_id)
    _ensure_currency(acc, currency)

    if idempotency_key:
        existing = TH.objects.filter(account=acc, idempotency_key=idempotency_key).first()
        if existing:
            return existing

    if acc.status != "ACTIVE":
        raise ValueError(f"account status not ACTIVE: {acc.status}")

    if acc.balance < amount:
        raise ValueError("insufficient funds")

    new_balance = _q(acc.balance - amount)

    tx = TH.objects.create(
        account=acc,
        tx_type=TH.TxType.WITHDRAW,
        amount=amount,
        running_balance=new_balance,
        currency=currency,
        description=description,
        occurred_at=timezone.now(),
        idempotency_key=idempotency_key,
        metadata=metadata or {},
    )

    Account.objects.filter(pk=acc.pk).update(balance=new_balance, version=F("version") + 1)
    return tx


@transaction.atomic
def transfer(from_account_id, to_account_id, amount, currency="KRW", description=""):
    if from_account_id == to_account_id:
        raise ValueError("cannot transfer to the same account")

    amount = _q(amount)
    if amount <= 0:
        raise ValueError("amount must be > 0")

    # 교착 방지: id 순서로 잠금
    a_id, b_id = sorted([from_account_id, to_account_id])
    a, b = Account.objects.select_for_update().filter(pk__in=[a_id, b_id]).order_by("pk")
    from_acc = a if a.pk == from_account_id else b
    to_acc = b if a.pk == from_account_id else a

    _ensure_currency(from_acc, currency)
    _ensure_currency(to_acc, currency)

    if from_acc.status != "ACTIVE" or to_acc.status != "ACTIVE":
        raise ValueError("both accounts must be ACTIVE")

    if from_acc.balance < amount:
        raise ValueError("insufficient funds")

    transfer_id = uuid.uuid4()

    # 출금(OUT)
    from_new_bal = _q(from_acc.balance - amount)
    out_tx = TH.objects.create(
        account=from_acc,
        tx_type=TH.TxType.TRANSFER_OUT,
        amount=amount,
        running_balance=from_new_bal,
        currency=currency,
        description=description,
        occurred_at=timezone.now(),
        transfer_id=transfer_id,
        counterparty=to_acc,
        metadata={"side": "out"},
    )

    # 입금(IN)
    to_new_bal = _q(to_acc.balance + amount)
    in_tx = TH.objects.create(
        account=to_acc,
        tx_type=TH.TxType.TRANSFER_IN,
        amount=amount,
        running_balance=to_new_bal,
        currency=currency,
        description=description,
        occurred_at=out_tx.occurred_at,
        transfer_id=transfer_id,
        counterparty=from_acc,
        metadata={"side": "in"},
    )

    # 두 계좌 잔액/버전 갱신
    Account.objects.filter(pk=from_acc.pk).update(balance=from_new_bal, version=F("version") + 1)
    Account.objects.filter(pk=to_acc.pk).update(balance=to_new_bal, version=F("version") + 1)

    return out_tx, in_tx
