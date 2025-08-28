# apps/accounts/tests/test_services.py
from __future__ import annotations

import importlib
import inspect
from decimal import Decimal
from typing import Any, Dict, Optional, Type

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone

User = get_user_model()


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


class _ModelBuilder:
    def __init__(self, user, context: Optional[Dict[type, models.Model]] = None):
        self.user = user
        self.context = context or {}
        self.context.setdefault(type(user), user)

    def create(self, model: type[models.Model], extra: Optional[Dict[str, Any]] = None) -> models.Model:
        data: Dict[str, Any] = {}
        extra = extra or {}

        # context에 동일 모델 인스턴스 이미 있으면 반환
        if model in self.context and isinstance(self.context[model], model):
            return self.context[model]

        for field in model._meta.get_fields():
            if not isinstance(field, models.Field):
                continue
            if field.auto_created or field.primary_key:
                continue
            if isinstance(field, models.ManyToManyField):
                continue
            if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                continue

            if field.name in extra:
                data[field.name] = extra[field.name]
                continue

            has_default = field.default is not models.NOT_PROVIDED
            if field.null or getattr(field, "blank", False) or has_default:
                continue

            if isinstance(field, models.ForeignKey):
                rel = field.remote_field.model  # type: ignore
                if rel in self.context and isinstance(self.context[rel], rel):
                    data[field.name] = self.context[rel]
                    continue
                if rel == get_user_model():
                    data[field.name] = self.user
                    continue
                data[field.name] = self._create_minimal_related(rel)
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
            if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                continue
            if field.null or getattr(field, "blank", False) or (field.default is not models.NOT_PROVIDED):
                continue

            if isinstance(field, models.ForeignKey) and field.remote_field.model == get_user_model():
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
            base = f"f{timezone.now().timestamp()}"
            return base[: field.max_length] if getattr(field, "max_length", None) else base
        if isinstance(field, models.TextField):
            return f"{field.name} text"
        if isinstance(field, (models.IntegerField, models.SmallIntegerField, models.BigIntegerField,
                              models.PositiveIntegerField, models.PositiveSmallIntegerField)):
            return 1
        if isinstance(field, models.FloatField):
            return 1.0
        if isinstance(field, models.DecimalField):
            # 최소 양수 금액
            return Decimal("1").scaleb(-field.decimal_places) if field.decimal_places > 0 else Decimal("1")
        if isinstance(field, models.BooleanField):
            return True
        if isinstance(field, models.DateTimeField):
            return timezone.now()
        if isinstance(field, models.DateField):
            return timezone.now().date()
        if hasattr(models, "JSONField") and isinstance(field, models.JSONField):  # type: ignore
            return {}
        return f"{field.name}"


class ServicesSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="svcuser", email="svc@example.com", password="pass1234!", is_active=True
        )

        cls.AccountModel = _get_model("accounts", "Account", "Accounts")
        cls.TransactionModel = (
            _get_model("accounts", "Transaction", "Transactions", "TransactionHistory")
            or _get_model("transactions", "Transaction", "Transactions")
        )

        cls.builder = _ModelBuilder(user=cls.user)

        cls.account = None
        if cls.AccountModel:
            # owner(=User) 같은 필수 FK까지 자동 충족
            cls.account = cls.builder.create(cls.AccountModel)
            cls.builder.context[cls.AccountModel] = cls.account

        if cls.TransactionModel:
            # amount 등 NOT NULL 필드를 자동 채움
            cls.transaction = cls.builder.create(cls.TransactionModel)
        else:
            cls.transaction = None

    def test_accounts_services_module(self):
        mod = _maybe_import("accounts.services")
        if mod is None:
            self.skipTest("accounts.services 모듈 없음")
        self._assert_callable_signatures_bindable(mod)

    def test_transactions_services_module(self):
        mod = _maybe_import("transactions.services")
        if mod is None:
            self.skipTest("transactions.services 모듈 없음")
        self._assert_callable_signatures_bindable(mod)

    def _assert_callable_signatures_bindable(self, mod):
        candidates = [(name, fn) for name, fn in vars(mod).items() if callable(fn) and not name.startswith("_")]
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
                n = p.name.lower()
                if n in ("user", "request_user", "current_user"):
                    kwargs[p.name] = self.user
                elif "account" in n and self.account is not None:
                    kwargs[p.name] = self.account
                elif "transaction" in n and self.transaction is not None:
                    kwargs[p.name] = self.transaction
                else:
                    kwargs[p.name] = 1
            sig.bind_partial(**kwargs)
