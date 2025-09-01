# # apps/notification/tests.py
# from __future__ import annotations
#
# from decimal import Decimal
# from typing import Any, Dict, Optional, Tuple, Type
# from uuid import uuid4
# import importlib
# import inspect
#
# from django.apps import apps as django_apps
# from django.contrib import admin
# from django.contrib.auth import get_user_model
# from django.db import models
# from django.test import TestCase
# from django.urls import reverse
# from django.utils import timezone
#
#
# def _get_model(*candidates: Tuple[str, str]):
#     for app_label, model_name in candidates:
#         try:
#             return django_apps.get_model(app_label, model_name)
#         except LookupError:
#             continue
#     return None
#
#
# class _ModelBuilder:
#     def __init__(
#         self, user, context: Optional[Dict[Type[models.Model], models.Model]] = None
#     ):
#         self.user = user
#         self.context = context or {}
#         self.context.setdefault(type(user), user)
#
#     def create(
#         self, model: Type[models.Model], extra: Optional[Dict[str, Any]] = None
#     ) -> models.Model:
#         data: Dict[str, Any] = {}
#         extra = extra or {}
#
#         if model in self.context and isinstance(self.context[model], model):
#             return self.context[model]
#
#         for field in model._meta.get_fields():
#             if not isinstance(field, models.Field):
#                 continue
#             if field.auto_created or field.primary_key:
#                 continue
#             if isinstance(field, models.ManyToManyField):
#                 continue
#             if getattr(field, "auto_now", False) or getattr(
#                 field, "auto_now_add", False
#             ):
#                 continue
#
#             if field.name in extra:
#                 data[field.name] = extra[field.name]
#                 continue
#
#             has_default = field.default is not models.NOT_PROVIDED
#             if field.null or getattr(field, "blank", False) or has_default:
#                 continue
#
#             if isinstance(field, models.ForeignKey):
#                 rel_model = field.remote_field.model  # type: ignore
#                 if rel_model in self.context and isinstance(
#                     self.context[rel_model], rel_model
#                 ):
#                     data[field.name] = self.context[rel_model]
#                     continue
#                 if rel_model == get_user_model():
#                     data[field.name] = self.user
#                     continue
#                 data[field.name] = self._create_minimal_related(rel_model)
#                 continue
#
#             if field.choices:
#                 data[field.name] = field.choices[0][0]
#                 continue
#
#             data[field.name] = self._default_for(field)
#
#         data.update(extra)
#         obj = model(**data)
#         try:
#             obj.full_clean()
#         except Exception:
#             pass
#         obj.save()
#         return obj
#
#     def _create_minimal_related(self, rel_model: Type[models.Model]) -> models.Model:
#         data: Dict[str, Any] = {}
#         for field in rel_model._meta.get_fields():
#             if not isinstance(field, models.Field):
#                 continue
#             if field.auto_created or field.primary_key:
#                 continue
#             if getattr(field, "auto_now", False) or getattr(
#                 field, "auto_now_add", False
#             ):
#                 continue
#             if (
#                 field.null
#                 or getattr(field, "blank", False)
#                 or (field.default is not models.NOT_PROVIDED)
#             ):
#                 continue
#             if (
#                 isinstance(field, models.ForeignKey)
#                 and field.remote_field.model == get_user_model()
#             ):
#                 data[field.name] = self.user
#                 continue
#             if field.choices:
#                 data[field.name] = field.choices[0][0]
#                 continue
#             data[field.name] = self._default_for(field)
#
#         obj = rel_model(**data)
#         try:
#             obj.full_clean()
#         except Exception:
#             pass
#         obj.save()
#         return obj
#
#     @staticmethod
#     def _default_for(field: models.Field) -> Any:
#         if isinstance(field, (models.CharField, models.SlugField)):
#             base = f"u{uuid4().hex}"
#             return (
#                 base[: field.max_length] if getattr(field, "max_length", None) else base
#             )
#         if isinstance(field, models.TextField):
#             return f"{field.name} text"
#         if isinstance(
#             field,
#             (
#                 models.IntegerField,
#                 models.SmallIntegerField,
#                 models.BigIntegerField,
#                 models.PositiveIntegerField,
#                 models.PositiveSmallIntegerField,
#             ),
#         ):
#             return 1
#         if isinstance(field, models.FloatField):
#             return 1.0
#         if isinstance(field, models.DecimalField):
#             q = "1" + ("0" * field.decimal_places) if field.decimal_places > 0 else "1"
#             return Decimal(q)
#         if isinstance(field, models.BooleanField):
#             return True
#         if isinstance(field, models.DateTimeField):
#             return timezone.now()
#         if isinstance(field, models.DateField):
#             return timezone.now().date()
#         if hasattr(models, "JSONField") and isinstance(field, models.JSONField):  # type: ignore
#             return {}
#         if isinstance(field, models.EmailField):
#             return f"{uuid4().hex[:8]}@example.com"
#         return f"{field.name}-{uuid4().hex[:8]}"
#
#
# class NotificationCRUDTests(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         cls.User = get_user_model()
#         cls.user = cls.User.objects.create_user(
#             email="notify@example.com",
#             password="pass1234!",
#             is_active=True,
#         )
#         cls.NotificationModel = _get_model(
#             ("notification", "Notification"),
#             ("notifications", "Notification"),
#             ("notification", "Notifications"),
#         )
#         if cls.NotificationModel is None:
#             raise AssertionError("notification.Notification 모델을 찾지 못했습니다.")
#
#         cls.builder = _ModelBuilder(user=cls.user)
#         cls.notification = cls.builder.create(cls.NotificationModel)
#
#     def test_create(self):
#         obj = self.builder.create(self.NotificationModel)
#         self.assertIsNotNone(obj.pk)
#
#     def test_read(self):
#         obj = self.NotificationModel.objects.get(pk=self.notification.pk)
#         self.assertEqual(obj.pk, self.notification.pk)
#
#     def test_update(self):
#         obj = self.NotificationModel.objects.get(pk=self.notification.pk)
#         changed = self._mutate_one_field(obj)
#         obj.save()
#         obj.refresh_from_db()
#         self.assertTrue(changed)
#
#     def test_delete(self):
#         pk = self.notification.pk
#         self.notification.delete()
#         self.assertFalse(self.NotificationModel.objects.filter(pk=pk).exists())
#
#     def _mutate_one_field(self, obj: models.Model) -> bool:
#         changed = False
#         for field in obj._meta.get_fields():
#             if not isinstance(field, models.Field):
#                 continue
#             if field.auto_created or field.primary_key:
#                 continue
#             if isinstance(field, models.ForeignKey):
#                 continue
#             if getattr(field, "auto_now", False) or getattr(
#                 field, "auto_now_add", False
#             ):
#                 continue
#             if isinstance(field, (models.DateTimeField, models.DateField)):
#                 continue
#
#             try:
#                 current = getattr(obj, field.name)
#             except Exception:
#                 continue
#
#             try:
#                 if isinstance(
#                     field, (models.CharField, models.SlugField, models.TextField)
#                 ):
#                     base = f"u{uuid4().hex}"
#                     setattr(
#                         obj,
#                         field.name,
#                         base[: field.max_length]
#                         if getattr(field, "max_length", None)
#                         else base,
#                     )
#                     changed = True
#                     break
#                 if isinstance(
#                     field,
#                     (
#                         models.IntegerField,
#                         models.SmallIntegerField,
#                         models.BigIntegerField,
#                         models.PositiveIntegerField,
#                         models.PositiveSmallIntegerField,
#                     ),
#                 ):
#                     setattr(obj, field.name, (current or 0) + 1)
#                     changed = True
#                     break
#                 if isinstance(field, models.DecimalField):
#                     from decimal import Decimal
#
#                     inc = (
#                         Decimal("1").scaleb(-field.decimal_places)
#                         if field.decimal_places > 0
#                         else Decimal("1")
#                     )
#                     setattr(obj, field.name, (current or Decimal("0")) + inc)
#                     changed = True
#                     break
#                 if isinstance(field, models.FloatField):
#                     setattr(obj, field.name, (current or 0.0) + 1.0)
#                     changed = True
#                     break
#                 if isinstance(field, models.BooleanField):
#                     setattr(obj, field.name, not bool(current))
#                     changed = True
#                     break
#             except Exception:
#                 continue
#         return changed
#
#
# class NotificationAdminSmokeTests(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         cls.User = get_user_model()
#         cls.admin_user = cls.User.objects.create_superuser(
#             email="admin@example.com",
#             password="pass1234!",
#         )
#         cls.NotificationModel = _get_model(
#             ("notification", "Notification"),
#             ("notifications", "Notification"),
#             ("notification", "Notifications"),
#         )
#         if cls.NotificationModel is None:
#             raise AssertionError("notification.Notification 모델을 찾지 못했습니다.")
#         cls.obj = _ModelBuilder(cls.admin_user).create(cls.NotificationModel)
#
#     def setUp(self):
#         self.client.force_login(self.admin_user)
#
#     def test_admin_pages(self):
#         if self.NotificationModel not in admin.site._registry:
#             self.skipTest("Notification 모델이 admin에 등록되어 있지 않음")
#         app_label = self.NotificationModel._meta.app_label
#         model_name = self.NotificationModel._meta.model_name
#         self.assertEqual(
#             self.client.get(
#                 reverse(f"admin:{app_label}_{model_name}_changelist")
#             ).status_code,
#             200,
#         )
#         self.assertEqual(
#             self.client.get(reverse(f"admin:{app_label}_{model_name}_add")).status_code,
#             200,
#         )
#         self.assertEqual(
#             self.client.get(
#                 reverse(f"admin:{app_label}_{model_name}_change", args=[self.obj.pk])
#             ).status_code,
#             200,
#         )
#
#
# class NotificationServicesSmokeTests(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         cls.module = _maybe_import("notification.services") or _maybe_import(
#             "notifications.services"
#         )
#
#     def test_import_and_signatures(self):
#         if self.module is None:
#             self.skipTest("notification.services 모듈 없음")
#         funcs = [
#             (n, f)
#             for n, f in vars(self.module).items()
#             if callable(f) and not n.startswith("_")
#         ]
#         if not funcs:
#             self.skipTest("notification.services 내 public 함수 없음")
#         for name, fn in funcs:
#             sig = inspect.signature(fn)
#             kwargs = {}
#             for p in sig.parameters.values():
#                 if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
#                     continue
#                 if p.default is not inspect._empty:
#                     continue
#                 kwargs[p.name] = 1
#             sig.bind_partial(**kwargs)
#
#
# def _maybe_import(modname: str):
#     try:
#         return importlib.import_module(modname)
#     except Exception:
#         return None
import pytest
from unittest import mock
from apps.users.models import CustomUser
from apps.notification.models import Notification
from apps.notification.serializers import NotificationSerializer


@pytest.mark.django_db
class TestNotificationUnit:
    def setup_method(self):
        self.user = CustomUser.objects.create_user(
            email="unituser@test.com", password="pass1234!"
        )

    def test_notification_str(self):
        notif = Notification.objects.create(user=self.user, message="테스트")
        assert notif.__str__().startswith(f"User {notif.user_id}")

    def test_serializer_valid(self):
        data = {"message": "안녕하세요"}
        serializer = NotificationSerializer(data=data)
        assert serializer.is_valid()
        instance = serializer.save(user=self.user)
        assert instance.pk

    def test_notify_signal_called_on_create(self):
        with mock.patch("builtins.print") as mock_print:
            Notification.objects.create(user=self.user, message="시그널 테스트")
            mock_print.assert_called_with("새 알림 생성: 시그널 테스트")
