# apps/analysis/management/commands/uuid.py
import uuid
from datetime import datetime
from django.core.management.base import BaseCommand
from apps.accounts.models import Account, TransactionHistory


class Command(BaseCommand):
    help = "Add a sample TransactionHistory record"

    def handle(self, *args, **kwargs):
        account = Account.objects.get(id=1)

        transaction = TransactionHistory.objects.create(
            tx_type="deposit",
            amount="1000.50",
            currency="USD",
            description="Initial deposit",
            occurred_at=datetime.now(),
            transfer_id=str(uuid.uuid4()),
            idempotency_key=str(uuid.uuid4())[:64],
            external_ref="EXT123456",
            metadata={},
            account=str(account.id),
            counterparty=str(uuid.uuid4()),
        )

        self.stdout.write(self.style.SUCCESS(f"Transaction created: {transaction.id}"))
