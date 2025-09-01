import pytest
from decimal import Decimal
from django.urls import reverse
from apps.accounts.models import Account
from apps.accounts.services import deposit, withdraw, transfer
from apps.accounts.serializers import AccountSerializer
from apps.users.models import CustomUser


@pytest.mark.django_db
class TestAccountUnit:
    def setup_method(self):
        self.owner = CustomUser.objects.create_user(
            email="u1@test.com", password="pw", is_active=True
        )
        self.account = Account.objects.create(
            owner=self.owner, name="테스트계좌", number="1234", currency="KRW"
        )

    def test_deposit(self):
        tx = deposit(
            self.account.id,
            Decimal("1000.0"),
            currency="KRW",
            idempotency_key="DEPOTEST1",
        )
        self.account.refresh_from_db()
        assert tx.amount == Decimal("1000.0")
        assert self.account.balance == Decimal("1000.0")

    def test_withdraw(self):
        deposit(self.account.id, Decimal("500"), currency="KRW")
        tx = withdraw(
            self.account.id, Decimal("200"), currency="KRW", idempotency_key="WD1"
        )
        self.account.refresh_from_db()
        assert tx.amount == Decimal("200")
        assert self.account.balance == Decimal("300.0")

    def test_transfer(self):
        owner2 = CustomUser.objects.create_user(
            email="u2@test.com", password="pw", is_active=True
        )
        account2 = Account.objects.create(
            owner=owner2, name="상대계좌", number="5678", currency="KRW"
        )
        deposit(self.account.id, Decimal("200"))
        out_tx, in_tx = transfer(
            self.account.id, account2.id, Decimal("100"), currency="KRW"
        )
        self.account.refresh_from_db()
        account2.refresh_from_db()
        assert self.account.balance == Decimal("100.0")
        assert account2.balance == Decimal("100.0")

    def test_account_serialization(self):
        serializer = AccountSerializer(self.account)
        data = serializer.data
        assert data["id"] == str(self.account.id)
        assert data["name"] == self.account.name
        assert data["number"] == self.account.number
        assert data["balance"] == str(self.account.balance)
        assert "created_at" in data

    def test_account_deserialization_valid(self):
        valid_data = {
            "name": "새계좌",
            "number": "9876543210",
            "currency": "KRW",
        }
        serializer = AccountSerializer(data=valid_data)
        assert serializer.is_valid(), serializer.errors
        account = serializer.save(owner=self.owner)
        assert account.name == valid_data["name"]
        assert account.number == valid_data["number"]

    def test_account_deserialization_invalid(self):
        invalid_data = {
            "name": "",
            "number": "",
        }
        serializer = AccountSerializer(data=invalid_data)
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "number" in serializer.errors

    # Django Admin tests
    def test_admin_account_list_view(self, admin_client):
        url = reverse("admin:accounts_account_changelist")  # admin url for Account list
        response = admin_client.get(url)
        assert response.status_code == 200
        assert "테스트계좌" in response.content.decode()

    def test_admin_account_change_view(self, admin_client):
        url = reverse("admin:accounts_account_change", args=[self.account.id])
        response = admin_client.get(url)
        assert response.status_code == 200
        # Owner email 표시 확인
        assert self.owner.email in response.content.decode()

    def test_admin_custom_method_get_owner_email(self, admin_client):
        from apps.accounts.admin import AccountAdmin
        from django.contrib import admin

        admin_instance = AccountAdmin(Account, admin.site)
        owner_email = admin_instance.get_owner_email(self.account)
        assert owner_email == self.owner.email
