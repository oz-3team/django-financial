# apps/accounts/tests/test_views.py
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.apps import apps as django_apps
from django.db import models
from django.utils import timezone

User = get_user_model()


def _get_model(app_label, *names):
    for name in names:
        try:
            return django_apps.get_model(app_label, name)
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


class AdminViewsSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="pass1234!",
        )
        cls.AccountModel = _get_model("accounts", "Account", "Accounts")
        cls.TransactionModel = (
            _get_model("accounts", "Transaction", "Transactions", "TransactionHistory")
            or _get_model("transactions", "Transaction", "Transactions")
        )

        cls.builder = _ModelBuilder(user=cls.superuser)

        if cls.AccountModel:
            cls.account = cls.builder.create(cls.AccountModel)
            cls.builder.context[cls.AccountModel] = cls.account

        if cls.TransactionModel:
            cls.transaction = cls.builder.create(cls.TransactionModel)

    def setUp(self):
        self.client.force_login(self.superuser)

    def _admin_registered(self, model) -> bool:
        return model in admin.site._registry

    def _assert_admin_pages_ok(self, model, obj):
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        # changelist
        url = reverse(f"admin:{app_label}_{model_name}_changelist")
        self.assertEqual(self.client.get(url).status_code, 200)
        # add
        url = reverse(f"admin:{app_label}_{model_name}_add")
        self.assertEqual(self.client.get(url).status_code, 200)
        # change
        url = reverse(f"admin:{app_label}_{model_name}_change", args=[obj.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_accounts_admin_views(self):
        if not self.AccountModel:
            self.skipTest("Account 모델 없음")
        if not self._admin_registered(self.AccountModel):
            self.skipTest("Account 모델이 admin에 등록되어 있지 않음")
        self._assert_admin_pages_ok(self.AccountModel, self.account)

    def test_transactions_admin_views(self):
        if not self.TransactionModel:
            self.skipTest("Transaction 모델 없음")
        if not self._admin_registered(self.TransactionModel):
            self.skipTest("Transaction 모델이 admin에 등록되어 있지 않음")
        self._assert_admin_pages_ok(self.TransactionModel, self.transaction)
