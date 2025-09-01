# apps/accounts/tests/test_all.py
from __future__ import annotations

import importlib
import inspect
from decimal import Decimal
from uuid import uuid4
from typing import Any, Dict, Optional, Type

from django.apps import apps as django_apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


# -------------------------------------------------------------------
# 유틸 함수
# -------------------------------------------------------------------
def _maybe_import(modname: str):
    try:
        return importlib.import_module(modname)
    except Exception:
        return None


def _get_model(app_label, *names):
    for n in names:
        try:
            return django_apps.get_model(app_label, n)
        except LookupError:
            continue
    return None


# -------------------------------------------------------------------
# 공용 모델 빌더
# -------------------------------------------------------------------
class _ModelBuilder:
    def __init__(
        self,
        user,
        account_model=None,
        context: Optional[Dict[Type[models.Model], models.Model]] = None,
    ):
        self.user = user
        self.account_model = account_model
        self.context = context or {}
        self.context.setdefault(type(user), user)

    def create(
        self, model: Type[models.Model], extra: Optional[Dict[str, Any]] = None
    ) -> models.Model:
        data: Dict[str, Any] = {}
        extra = extra or {}

        # context 재사용
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
                rel_model = field.remote_field.model  # type: ignore
                if rel_model in self.context and isinstance(
                    self.context[rel_model], rel_model
                ):
                    data[field.name] = self.context[rel_model]
                    continue
                if rel_model == get_user_model():
                    data[field.name] = self.user
                    continue
                # Account 모델 강제 주입
                if (
                    self.account_model
                    and rel_model == self.account_model
                    and self.account_model in self.context
                ):
                    data[field.name] = self.context[self.account_model]
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

    def _create_minimal_related(self, rel_model: type[models.Model]) -> models.Model:
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
            base = f"u{uuid4().hex}"
            return (
                base[: field.max_length] if getattr(field, "max_length", None) else base
            )
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
            return (
                Decimal("1").scaleb(-field.decimal_places)
                if field.decimal_places > 0
                else Decimal("1")
            )
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
        return f"{field.name}-{uuid4().hex[:6]}"


# -------------------------------------------------------------------
# CRUD 모델 테스트
# -------------------------------------------------------------------
class AccountAndTransactionCRUDTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()
        cls.user = cls.User.objects.create_user(
            email="tester@example.com", password="pass1234!"
        )

        cls.AccountModel = _get_model("accounts", "Account", "Accounts")
        cls.TransactionModel = _get_model(
            "accounts",
            "Transaction",
            "Transactions",
            "TransactionHistory",
            "transactions",
            "Transaction",
            "Transactions",
        )

        if cls.AccountModel is None:
            raise AssertionError("Account 모델을 찾지 못했습니다.")
        if cls.TransactionModel is None:
            raise AssertionError("Transaction 모델을 찾지 못했습니다.")

        cls.builder = _ModelBuilder(user=cls.user, account_model=cls.AccountModel)
        cls.account = cls.builder.create(cls.AccountModel, extra={"owner": cls.user})
        cls.builder.context[cls.AccountModel] = cls.account

    def test_accounts_crud(self):
        # Create
        acc = self.builder.create(self.AccountModel, extra={"owner": self.user})
        self.assertIsNotNone(acc.pk)
        # Read
        obj = self.AccountModel.objects.get(pk=acc.pk)
        self.assertEqual(obj.pk, acc.pk)
        # Update
        obj_name = getattr(obj, obj._meta.fields[1].name, None)
        if isinstance(obj_name, str):
            setattr(obj, obj._meta.fields[1].name, obj_name + "_x")
        obj.save()
        obj.refresh_from_db()
        # Delete
        pk = acc.pk
        acc.delete()
        self.assertFalse(self.AccountModel.objects.filter(pk=pk).exists())

    def test_transactions_crud(self):
        tx = self.builder.create(self.TransactionModel)
        self.assertIsNotNone(tx.pk)
        got = self.TransactionModel.objects.get(pk=tx.pk)
        self.assertEqual(got.pk, tx.pk)
        # Delete
        pk = tx.pk
        tx.delete()
        self.assertFalse(self.TransactionModel.objects.filter(pk=pk).exists())


# -------------------------------------------------------------------
# Services 모듈 스모크 테스트
# -------------------------------------------------------------------
class ServicesSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="svc@example.com", password="pass1234!", is_active=True
        )

        cls.AccountModel = _get_model("accounts", "Account", "Accounts")
        cls.TransactionModel = _get_model(
            "accounts", "Transaction", "Transactions", "TransactionHistory"
        ) or _get_model("transactions", "Transaction", "Transactions")

        cls.builder = _ModelBuilder(user=cls.user)
        cls.account = cls.builder.create(cls.AccountModel) if cls.AccountModel else None
        cls.transaction = (
            cls.builder.create(cls.TransactionModel) if cls.TransactionModel else None
        )

    def _assert_callable_signatures_bindable(self, mod):
        candidates = [
            (n, fn)
            for n, fn in vars(mod).items()
            if callable(fn) and not n.startswith("_")
        ]
        if not candidates:
            self.skipTest(f"{mod.__name__} 모듈에 public 함수 없음")
        for name, fn in candidates:
            sig = inspect.signature(fn)
            kwargs = {}
            for p in sig.parameters.values():
                if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                    continue
                if p.default is not inspect._empty:
                    continue
                lname = p.name.lower()
                if lname in ("user", "request_user", "current_user"):
                    kwargs[p.name] = self.user
                elif "account" in lname and self.account is not None:
                    kwargs[p.name] = self.account
                elif "transaction" in lname and self.transaction is not None:
                    kwargs[p.name] = self.transaction
                else:
                    kwargs[p.name] = 1
            sig.bind_partial(**kwargs)

    def test_accounts_services_module(self):
        mod = _maybe_import("accounts.services")
        if mod is None:
            self.skipTest("accounts.services 없음")
        self._assert_callable_signatures_bindable(mod)

    def test_transactions_services_module(self):
        mod = _maybe_import("transactions.services")
        if mod is None:
            self.skipTest("transactions.services 없음")
        self._assert_callable_signatures_bindable(mod)


# -------------------------------------------------------------------
# Admin 뷰 테스트
# -------------------------------------------------------------------
class AdminViewsSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            email="admin@example.com", password="pass1234!"
        )
        cls.AccountModel = _get_model("accounts", "Account", "Accounts")
        cls.TransactionModel = _get_model(
            "accounts", "Transaction", "Transactions", "TransactionHistory"
        ) or _get_model("transactions", "Transaction", "Transactions")

        cls.builder = _ModelBuilder(user=cls.superuser)
        cls.account = cls.builder.create(cls.AccountModel) if cls.AccountModel else None
        cls.transaction = (
            cls.builder.create(cls.TransactionModel) if cls.TransactionModel else None
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def _admin_registered(self, model) -> bool:
        return model in admin.site._registry

    def _assert_admin_pages_ok(self, model, obj):
        app_label, model_name = model._meta.app_label, model._meta.model_name
        self.assertEqual(
            self.client.get(
                reverse(f"admin:{app_label}_{model_name}_changelist")
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse(f"admin:{app_label}_{model_name}_add")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse(f"admin:{app_label}_{model_name}_change", args=[obj.pk])
            ).status_code,
            200,
        )

    def test_accounts_admin_views(self):
        if not self.AccountModel or not self._admin_registered(self.AccountModel):
            self.skipTest("Account 모델 없음 또는 admin 미등록")
        self._assert_admin_pages_ok(self.AccountModel, self.account)

    def test_transactions_admin_views(self):
        if not self.TransactionModel or not self._admin_registered(
            self.TransactionModel
        ):
            self.skipTest("Transaction 모델 없음 또는 admin 미등록")
        self._assert_admin_pages_ok(self.TransactionModel, self.transaction)
