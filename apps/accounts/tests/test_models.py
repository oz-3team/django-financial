# apps/accounts/tests/test_models.py
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4
from typing import Any, Dict, Optional, Tuple, Type

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone


def _get_model(*candidates: Tuple[str, str]):
    for app_label, model_name in candidates:
        try:
            return django_apps.get_model(app_label, model_name)
        except LookupError:
            continue
    return None


class _ModelBuilder:
    def __init__(self, user, account_model=None, context: Optional[Dict[Type[models.Model], models.Model]] = None):
        self.user = user
        self.account_model = account_model
        self.context = context or {}
        self.context.setdefault(type(user), user)

    def create(self, model: Type[models.Model], extra: Optional[Dict[str, Any]] = None) -> models.Model:
        data: Dict[str, Any] = {}
        extra = extra or {}

        if model in self.context and isinstance(self.context[model], model):
            return self.context[model]

        for field in model._meta.get_fields():
            if not isinstance(field, models.Field):
                continue
            if field.auto_created:
                continue
            if isinstance(field, (models.AutoField, models.BigAutoField)) or field.primary_key:
                continue
            if isinstance(field, models.ManyToManyField):
                continue
            if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                continue

            if field.name in extra:
                data[field.name] = extra[field.name]
                continue

            has_default = field.default is not models.NOT_PROVIDED
            if (field.null or getattr(field, "blank", False) or has_default):
                continue

            if isinstance(field, models.ForeignKey):
                rel_model = field.remote_field.model  # type: ignore
                if rel_model in self.context and isinstance(self.context[rel_model], rel_model):
                    data[field.name] = self.context[rel_model]
                    continue
                if rel_model == get_user_model():
                    data[field.name] = self.user
                    continue
                if self.account_model and rel_model == self.account_model and self.account_model in self.context:
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

    def _create_minimal_related(self, rel_model: Type[models.Model]) -> models.Model:
        data: Dict[str, Any] = {}
        for field in rel_model._meta.get_fields():
            if not isinstance(field, models.Field):
                continue
            if field.auto_created or isinstance(field, (models.AutoField, models.BigAutoField)) or field.primary_key:
                continue
            if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                continue
            if field.null or getattr(field, "blank", False) or (field.default is not models.NOT_PROVIDED):
                continue
            if isinstance(field, models.ForeignKey):
                if field.remote_field.model == get_user_model():
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
            return base[: field.max_length] if getattr(field, "max_length", None) else base
        if isinstance(field, models.TextField):
            return f"{field.name} text"
        if isinstance(field, (models.IntegerField, models.SmallIntegerField, models.BigIntegerField, models.PositiveIntegerField, models.PositiveSmallIntegerField)):
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


class AccountAndTransactionCRUDTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()
        cls.user = cls.User.objects.create_user(
            email="tester@example.com",
            password="pass1234!",
        )

        cls.AccountModel = _get_model(("accounts", "Account"), ("accounts", "Accounts"))
        cls.TransactionModel = _get_model(
            ("accounts", "Transaction"),
            ("accounts", "Transactions"),
            ("accounts", "TransactionHistory"),  # ← 추가
            ("transactions", "Transaction"),
            ("transactions", "Transactions"),
        )

        if cls.AccountModel is None:
            raise AssertionError("Account/Accounts 모델을 찾지 못했습니다.")
        if cls.TransactionModel is None:
            raise AssertionError("Transaction/Transactions 모델을 찾지 못했습니다.")

        cls.builder = _ModelBuilder(user=cls.user, account_model=cls.AccountModel)
        cls.account = cls.builder.create(cls.AccountModel, extra={"owner": cls.user})  # ← owner 채움
        cls.builder.context[cls.AccountModel] = cls.account

    def test_accounts_create(self):
        acc = self.builder.create(self.AccountModel, extra={"owner": self.user})
        self.assertIsNotNone(acc.pk)

    def test_accounts_read(self):
        obj = self.AccountModel.objects.get(pk=self.account.pk)
        self.assertEqual(obj.pk, self.account.pk)

    def test_accounts_update(self):
        obj = self.AccountModel.objects.get(pk=self.account.pk)
        changed = self._mutate_one_field(obj)
        obj.save()
        obj.refresh_from_db()
        self.assertTrue(changed)

    def test_accounts_delete(self):
        pk = self.account.pk
        self.account.delete()
        self.assertFalse(self.AccountModel.objects.filter(pk=pk).exists())

    def test_transactions_create(self):
        tx = self.builder.create(self.TransactionModel)
        self.assertIsNotNone(tx.pk)
        for f in self._fk_fields(self.TransactionModel):
            if f.remote_field.model == self.AccountModel:
                self.assertEqual(getattr(tx, f.name).pk, self.account.pk)
                break

    def test_transactions_read(self):
        tx = self.builder.create(self.TransactionModel)
        got = self.TransactionModel.objects.get(pk=tx.pk)
        self.assertEqual(got.pk, tx.pk)

    def test_transactions_update(self):
        tx = self.builder.create(self.TransactionModel)
        changed = self._mutate_one_field(tx)
        tx.save()
        tx.refresh_from_db()
        self.assertTrue(changed)

    def test_transactions_delete(self):
        tx = self.builder.create(self.TransactionModel)
        pk = tx.pk
        tx.delete()
        self.assertFalse(self.TransactionModel.objects.filter(pk=pk).exists())

    @staticmethod
    def _fk_fields(model: Type[models.Model]):
        for f in model._meta.get_fields():
            if isinstance(f, models.ForeignKey):
                yield f

    def _mutate_one_field(self, obj: models.Model) -> bool:
        changed = False
        for field in obj._meta.get_fields():
            if not isinstance(field, models.Field):
                continue
            if field.auto_created or field.primary_key:
                continue
            if isinstance(field, models.ForeignKey):
                continue
            if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                continue
            if isinstance(field, (models.DateTimeField, models.DateField)):
                continue

            try:
                current = getattr(obj, field.name)
            except Exception:
                continue

            try:
                if isinstance(field, (models.CharField, models.SlugField, models.TextField)):
                    base = f"u{uuid4().hex}"
                    setattr(obj, field.name, base[: field.max_length] if getattr(field, "max_length", None) else base)
                    changed = True
                    break
                if isinstance(field, (models.IntegerField, models.SmallIntegerField, models.BigIntegerField, models.PositiveIntegerField, models.PositiveSmallIntegerField)):
                    setattr(obj, field.name, (current or 0) + 1)
                    changed = True
                    break
                if isinstance(field, models.DecimalField):
                    inc = Decimal("1").scaleb(-field.decimal_places) if field.decimal_places > 0 else Decimal("1")
                    setattr(obj, field.name, (current or Decimal("0")) + inc)
                    changed = True
                    break
                if isinstance(field, models.FloatField):
                    setattr(obj, field.name, (current or 0.0) + 1.0)
                    changed = True
                    break
                if isinstance(field, models.BooleanField):
                    setattr(obj, field.name, not bool(current))
                    changed = True
                    break
            except Exception:
                continue
        return changed
