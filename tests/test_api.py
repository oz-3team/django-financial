# tests/test_api.py
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Iterable, Optional, Tuple, Type
from uuid import uuid4

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone


# ------------------------------
# Generic model helpers
# ------------------------------
def _get_model(*candidates: Tuple[str, str]):
    for app_label, model_name in candidates:
        try:
            return django_apps.get_model(app_label, model_name)
        except LookupError:
            continue
    return None


class _ModelBuilder:
    def __init__(
        self, user, context: Optional[Dict[Type[models.Model], models.Model]] = None
    ):
        self.user = user
        self.context = context or {}
        self.context.setdefault(type(user), user)

    def create(
        self, model: Type[models.Model], extra: Optional[Dict[str, Any]] = None
    ) -> models.Model:
        data: Dict[str, Any] = {}
        extra = extra or {}

        if model in self.context and isinstance(self.context[model], model):
            return self.context[model]

        for field in model._meta.get_fields():
            if not isinstance(field, models.Field):
                continue
            if field.auto_created or field.primary_key:
                continue
            if isinstance(field, models.ManyToManyField):
                continue
            if getattr(field, "auto_now", False) or getattr(
                field, "auto_now_add", False
            ):
                continue

            if field.name in extra:
                data[field.name] = extra[field.name]
                continue

            has_default = field.default is not models.NOT_PROVIDED
            if field.null or getattr(field, "blank", False) or has_default:
                continue

            if isinstance(field, models.ForeignKey):
                rel_model = field.remote_field.model  # type: ignore[attr-defined]
                if rel_model in self.context and isinstance(
                    self.context[rel_model], rel_model
                ):
                    data[field.name] = self.context[rel_model]
                    continue
                if rel_model == get_user_model():
                    data[field.name] = self.user
                    continue
                data[field.name] = self._create_minimal_related(rel_model)
                continue

            if field.choices:
                data[field.name] = field.choices[0][0]
                continue

            data[field.name] = self._default_for(field)

        data.update(extra)
        obj = model(**data)
        try:
            obj.full_clean()
        except Exception:
            pass
        obj.save()
        return obj

    def _create_minimal_related(self, rel_model: Type[models.Model]) -> models.Model:
        data: Dict[str, Any] = {}
        for field in rel_model._meta.get_fields():
            if not isinstance(field, models.Field):
                continue
            if field.auto_created or field.primary_key:
                continue
            if getattr(field, "auto_now", False) or getattr(
                field, "auto_now_add", False
            ):
                continue
            if (
                field.null
                or getattr(field, "blank", False)
                or (field.default is not models.NOT_PROVIDED)
            ):
                continue

            if (
                isinstance(field, models.ForeignKey)
                and field.remote_field.model == get_user_model()
            ):
                data[field.name] = self.user
                continue

            if field.choices:
                data[field.name] = field.choices[0][0]
                continue

            data[field.name] = self._default_for(field)

        obj = rel_model(**data)
        try:
            obj.full_clean()
        except Exception:
            pass
        obj.save()
        return obj

    @staticmethod
    def _default_for(field: models.Field) -> Any:
        if isinstance(field, (models.CharField, models.SlugField)):
            return f"{field.name}-{uuid4().hex[:12]}"
        if isinstance(field, models.TextField):
            return f"{field.name} text"
        if isinstance(
            field,
            (
                models.IntegerField,
                models.SmallIntegerField,
                models.BigIntegerField,
                models.PositiveIntegerField,
                models.PositiveSmallIntegerField,
            ),
        ):
            return 1
        if isinstance(field, models.FloatField):
            return 1.0
        if isinstance(field, models.DecimalField):
            q = "1" + ("0" * field.decimal_places) if field.decimal_places > 0 else "1"
            return Decimal(q)
        if isinstance(field, models.BooleanField):
            return True
        if isinstance(field, models.DateTimeField):
            return timezone.now()
        if isinstance(field, models.DateField):
            return timezone.now().date()
        if hasattr(models, "JSONField") and isinstance(field, models.JSONField):  # type: ignore
            return {}
        if isinstance(field, models.EmailField):
            return f"{uuid4().hex[:8]}@example.com"
        return f"{field.name}-{uuid4().hex[:8]}"


# ------------------------------
# URL helpers
# ------------------------------
_ALL_NAMESPACES = [
    "",
    "api",
    "v1",
    "accounts",
    "transactions",
    "analysis",
    "notification",
    "notifications",
    "users",
]
_BASES = [
    "account",
    "accounts",
    "transaction",
    "transactions",
    "analysis",
    "analyses",
    "notification",
    "notifications",
    "user",
    "users",
]


def _reverse_first(candidates: Iterable[str]) -> Optional[str]:
    for name in candidates:
        try:
            return reverse(name)
        except NoReverseMatch:
            continue
    return None


def _list_name_candidates(base: str) -> Iterable[str]:
    for ns in _ALL_NAMESPACES:
        yield (f"{ns}:{base}-list") if ns else f"{base}-list"


def _detail_name_candidates(base: str, pk: Any) -> Iterable[Tuple[str, tuple]]:
    for ns in _ALL_NAMESPACES:
        name = (f"{ns}:{base}-detail") if ns else f"{base}-detail"
        yield name, (pk,)


def _assert_not_server_or_notfound(testcase: TestCase, status: int):
    testcase.assertNotIn(status, {404, 500, 502, 503})


# ------------------------------
# API Smoke Tests
# ------------------------------
class APISmokeTests(TestCase):
    """
    DRF DefaultRouter 패턴(***-list / ***-detail)의 API 엔드포인트가 존재하면
    OPTIONS/GET이 404/5xx가 아닌지 점검한다. 존재하지 않으면 skip.
    """

    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()
        cls.user = cls.User.objects.create_user(
            email="apiuser@example.com",
            password="pass1234!",
        )

        # 모델 찾기 및 최소 인스턴스 생성
        cls.AccountModel = _get_model(("accounts", "Account"), ("accounts", "Accounts"))
        cls.TransactionModel = _get_model(
            ("accounts", "Transaction"),
            ("accounts", "Transactions"),
            ("transactions", "Transaction"),
            ("transactions", "Transactions"),
        )
        cls.AnalysisModel = _get_model(
            ("analysis", "Analysis"), ("analysis", "Analyses")
        )
        cls.NotificationModel = _get_model(
            ("notification", "Notification"),
            ("notifications", "Notification"),
            ("notification", "Notifications"),
        )

        cls.builder = _ModelBuilder(user=cls.user)
        cls.account = cls.builder.create(cls.AccountModel) if cls.AccountModel else None
        if cls.TransactionModel:
            if cls.account:
                cls.builder.context[type(cls.account)] = cls.account
            cls.transaction = cls.builder.create(cls.TransactionModel)
        else:
            cls.transaction = None
        cls.analysis = (
            cls.builder.create(cls.AnalysisModel) if cls.AnalysisModel else None
        )
        cls.notification = (
            cls.builder.create(cls.NotificationModel) if cls.NotificationModel else None
        )

    # -------- accounts --------
    def test_accounts_list_and_detail(self):
        bases = ["account", "accounts"]
        list_url = _reverse_first(
            name for b in bases for name in _list_name_candidates(b)
        )
        if not list_url:
            self.skipTest("accounts 리스트 엔드포인트를 찾지 못함")
        resp = self.client.options(list_url)
        _assert_not_server_or_notfound(self, resp.status_code)
        resp = self.client.get(list_url)
        _assert_not_server_or_notfound(self, resp.status_code)

        if not self.account:
            self.skipTest("accounts detail 테스트용 객체 없음")
        for b in bases:
            for name, args in _detail_name_candidates(b, self.account.pk):
                try:
                    url = reverse(name, args=args)
                except NoReverseMatch:
                    continue
                resp = self.client.options(url)
                _assert_not_server_or_notfound(self, resp.status_code)
                resp = self.client.get(url)
                _assert_not_server_or_notfound(self, resp.status_code)
                return
        self.skipTest("accounts detail 엔드포인트를 찾지 못함")

    # -------- transactions --------
    def test_transactions_list_and_detail(self):
        bases = ["transaction", "transactions"]
        list_url = _reverse_first(
            name for b in bases for name in _list_name_candidates(b)
        )
        if not list_url:
            self.skipTest("transactions 리스트 엔드포인트를 찾지 못함")
        resp = self.client.options(list_url)
        _assert_not_server_or_notfound(self, resp.status_code)
        resp = self.client.get(list_url)
        _assert_not_server_or_notfound(self, resp.status_code)

        if not self.transaction:
            self.skipTest("transactions detail 테스트용 객체 없음")
        for b in bases:
            for name, args in _detail_name_candidates(b, self.transaction.pk):
                try:
                    url = reverse(name, args=args)
                except NoReverseMatch:
                    continue
                resp = self.client.options(url)
                _assert_not_server_or_notfound(self, resp.status_code)
                resp = self.client.get(url)
                _assert_not_server_or_notfound(self, resp.status_code)
                return
        self.skipTest("transactions detail 엔드포인트를 찾지 못함")

    # -------- analysis --------
    def test_analysis_list_and_detail(self):
        bases = ["analysis", "analyses"]
        list_url = _reverse_first(
            name for b in bases for name in _list_name_candidates(b)
        )
        if not list_url:
            self.skipTest("analysis 리스트 엔드포인트를 찾지 못함")
        resp = self.client.options(list_url)
        _assert_not_server_or_notfound(self, resp.status_code)
        resp = self.client.get(list_url)
        _assert_not_server_or_notfound(self, resp.status_code)

        if not self.analysis:
            self.skipTest("analysis detail 테스트용 객체 없음")
        for b in bases:
            for name, args in _detail_name_candidates(b, self.analysis.pk):
                try:
                    url = reverse(name, args=args)
                except NoReverseMatch:
                    continue
                resp = self.client.options(url)
                _assert_not_server_or_notfound(self, resp.status_code)
                resp = self.client.get(url)
                _assert_not_server_or_notfound(self, resp.status_code)
                return
        self.skipTest("analysis detail 엔드포인트를 찾지 못함")

    # -------- notification --------
    def test_notification_list_and_detail(self):
        bases = ["notification", "notifications"]
        list_url = _reverse_first(
            name for b in bases for name in _list_name_candidates(b)
        )
        if not list_url:
            self.skipTest("notification 리스트 엔드포인트를 찾지 못함")
        resp = self.client.options(list_url)
        _assert_not_server_or_notfound(self, resp.status_code)
        resp = self.client.get(list_url)
        _assert_not_server_or_notfound(self, resp.status_code)

        if not self.notification:
            self.skipTest("notification detail 테스트용 객체 없음")
        for b in bases:
            for name, args in _detail_name_candidates(b, self.notification.pk):
                try:
                    url = reverse(name, args=args)
                except NoReverseMatch:
                    continue
                resp = self.client.options(url)
                _assert_not_server_or_notfound(self, resp.status_code)
                resp = self.client.get(url)
                _assert_not_server_or_notfound(self, resp.status_code)
                return
        self.skipTest("notification detail 엔드포인트를 찾지 못함")


# tests/test_api.py  (변경점만 요약: 후보 추가)
