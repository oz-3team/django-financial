import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

from apps.analysis.models import Analysis
from apps.analysis.serializers import AnalysisSerializer
from apps.analysis.services import AnalysisService
from apps.users.models import CustomUser
from apps.accounts.models import Account, TransactionHistory


@pytest.mark.django_db
class TestAnalysisUnit:
    def setup_method(self):
        Analysis.objects.all().delete()

        self.user = CustomUser.objects.create_user(
            email="analysisuser@test.com", password="testpass", is_active=True
        )
        self.account = Account.objects.create(
            owner=self.user, name="테스트계좌", number="1234", currency="KRW"
        )

        TransactionHistory.objects.create(
            account=self.account,
            tx_type=TransactionHistory.TxType.DEPOSIT,
            amount=Decimal("100.00"),
            running_balance=Decimal("100.00"),
            currency="KRW",
            occurred_at=date(2025, 1, 1),
        )
        TransactionHistory.objects.create(
            account=self.account,
            tx_type=TransactionHistory.TxType.WITHDRAW,
            amount=Decimal("50.00"),
            running_balance=Decimal("50.00"),
            currency="KRW",
            occurred_at=date(2025, 1, 2),
        )

        self.analysis = Analysis.objects.create(
            user=self.user,
            analysis_target="INCOME",
            period_type="DAILY",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        self.factory = RequestFactory()
        self.request = self.factory.get("/")
        self.request.user = self.user

    def test_serializer_valid(self):
        valid_data = {
            "user": self.user.id,
            "analysis_target": "EXPENSE",
            "period_type": "WEEKLY",
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=7),
            "description": "시리얼라이저 테스트",
        }
        serializer = AnalysisSerializer(
            data=valid_data, context={"request": self.request}
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

    def test_serializer_invalid(self):
        invalid_data = {
            "user": self.user.id,
            "analysis_target": "EXPENSE",
            "period_type": "WEEKLY",
            "start_date": None,
            "end_date": date.today() + timedelta(days=7),
            "description": "Invalid 테스트",
        }
        serializer = AnalysisSerializer(
            data=invalid_data, context={"request": self.request}
        )
        assert not serializer.is_valid()
        assert "start_date" in serializer.errors

    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch("os.remove")
    def test_result_image_file_deleted_on_instance_delete(
        self, mock_remove, mock_isfile
    ):
        image_file = SimpleUploadedFile("test.jpg", b"file_content")
        analysis = Analysis.objects.create(
            user=self.user,
            analysis_target="EXPENSE",
            period_type="WEEKLY",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            result_image=image_file,
        )
        # 삭제 시 경로 존재 확인 및 삭제 시그널 테스트
        analysis.delete()
        mock_isfile.assert_called_once()
        mock_remove.assert_called_once()

    def test_get_transaction_queryset(self):
        qs = AnalysisService.get_transaction_queryset(self.analysis)
        assert qs.count() == 2
        assert qs.first().account == self.account

    def test_get_analysis_data(self):
        data = AnalysisService.get_analysis_data(self.analysis)
        assert "total_amount" in data
        assert data["transaction_count"] == 2
        assert isinstance(data["period_data"], list)
        assert data["currency"] == "KRW"
