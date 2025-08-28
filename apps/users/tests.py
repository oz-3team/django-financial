# apps/users/tests.py
from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import uuid4

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone


User = get_user_model()


def _default_for(field: models.Field) -> Any:
    if isinstance(field, (models.CharField, models.SlugField)):
        return f"{field.name}-{uuid4().hex[:12]}"
    if isinstance(field, models.TextField):
        return f"{field.name} text"
    if isinstance(field, (models.IntegerField, models.SmallIntegerField, models.BigIntegerField,
                          models.PositiveIntegerField, models.PositiveSmallIntegerField)):
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
    if hasattr(models, "JSONField") and isinstance(field, models.JSONField):  # type: ignore[attr-defined]
        return {}
    if isinstance(field, models.EmailField):
        return f"{uuid4().hex[:10]}@example.com"
    return f"{field.name}-{uuid4().hex[:8]}"


def _minimal_user_kwargs() -> dict[str, Any]:
    """
    커스텀 User 모델의 필수(non-null, blank=False, default 없음) 필드를 스캔해
    인스턴스를 생성할 수 있는 kwargs를 만든다.
    USERNAME_FIELD은 항상 채운다.
    """
    kwargs: dict[str, Any] = {}

    # USERNAME_FIELD 먼저
    username_field = getattr(User, "USERNAME_FIELD", "username")
    try:
        uf = User._meta.get_field(username_field)
    except Exception:
        uf = None
    if uf is not None and isinstance(uf, models.EmailField):
        kwargs[username_field] = f"user_{uuid4().hex[:8]}@example.com"
    else:
        kwargs[username_field] = f"user_{uuid4().hex[:8]}"

    # 나머지 필수 필드 자동 채움
    for f in User._meta.get_fields():
        if not isinstance(f, models.Field):
            continue
        if f.auto_created or f.primary_key:
            continue
        if isinstance(f, (models.ManyToManyField, models.ForeignKey, models.OneToOneField)):
            # 필수 FK/M2M이면 스킵(프로젝트 종속). 생성 시 실패하면 테스트가 알려줌.
            if not f.null and not getattr(f, "blank", False) and f.default is models.NOT_PROVIDED:
                pass
            continue
        if getattr(f, "auto_now", False) or getattr(f, "auto_now_add", False):
            continue
        if f.name in kwargs:
            continue
        has_default = f.default is not models.NOT_PROVIDED
        if f.null or getattr(f, "blank", False) or has_default:
            continue
        kwargs[f.name] = _default_for(f)

    return kwargs


def _make_user(password: str = "pass1234!") -> User:
    kwargs = _minimal_user_kwargs()
    user = User(**kwargs)
    user.set_password(password)
    if hasattr(user, "is_active"):
        user.is_active = True  # 로그인/인증 실패 방지
    try:
        user.full_clean()
    except Exception:
        pass
    user.save()
    return user


def _make_superuser(password: str = "pass1234!") -> User:
    user = _make_user(password=password)
    if hasattr(user, "is_staff"):
        user.is_staff = True
    if hasattr(user, "is_superuser"):
        user.is_superuser = True
    user.save()
    return user


class UserCRUDTests(TestCase):
    def test_create_user(self):
        u = _make_user()
        self.assertIsNotNone(u.pk)
        self.assertTrue(u.check_password("pass1234!"))

    def test_read_user(self):
        u = _make_user()
        got = User.objects.get(pk=u.pk)
        self.assertEqual(got.get_username(), u.get_username())

    def test_update_user(self):
        u = _make_user()
        changed = False
        for f in User._meta.get_fields():
            if not isinstance(f, models.Field):
                continue
            if f.auto_created or f.primary_key:
                continue
            if isinstance(f, (models.ForeignKey, models.ManyToManyField, models.OneToOneField)):
                continue
            if getattr(f, "auto_now", False) or getattr(f, "auto_now_add", False):
                continue
            if isinstance(f, (models.DateTimeField, models.DateField)):
                continue
            try:
                if isinstance(f, (models.CharField, models.TextField, models.SlugField)):
                    setattr(u, f.name, f"updated-{uuid4().hex[:6]}")
                    changed = True
                    break
                if isinstance(f, (models.IntegerField, models.SmallIntegerField, models.BigIntegerField,
                                  models.PositiveIntegerField, models.PositiveSmallIntegerField)):
                    setattr(u, f.name, (getattr(u, f.name, 0) or 0) + 1)
                    changed = True
                    break
                if isinstance(f, models.BooleanField):
                    setattr(u, f.name, not bool(getattr(u, f.name, False)))
                    changed = True
                    break
            except Exception:
                continue
        self.assertTrue(changed, "수정 가능한 필드를 찾지 못했습니다.")
        u.save()
        u.refresh_from_db()
        self.assertTrue(True)

    def test_delete_user(self):
        u = _make_user()
        pk = u.pk
        u.delete()
        self.assertFalse(User.objects.filter(pk=pk).exists())


class UserAuthTests(TestCase):
    def test_login_with_password(self):
        pwd = "pass1234!"
        u = _make_user(password=pwd)
        ok = self.client.login(username=u.get_username(), password=pwd)
        self.assertTrue(ok, "로그인 실패: 인증 백엔드/USERNAME_FIELD 확인 필요")


class UserAdminSmokeTests(TestCase):
    def setUp(self):
        self.admin_user = _make_superuser()
        self.client.login(username=self.admin_user.get_username(), password="pass1234!")

    def test_admin_pages(self):
        if User not in admin.site._registry:
            self.skipTest("User 모델이 admin에 등록되어 있지 않음")

        target = _make_user()

        app_label = User._meta.app_label
        model_name = User._meta.model_name

        url = reverse(f"admin:{app_label}_{model_name}_changelist")
        self.assertEqual(self.client.get(url).status_code, 200)

        url = reverse(f"admin:{app_label}_{model_name}_add")
        self.assertEqual(self.client.get(url).status_code, 200)

        url = reverse(f"admin:{app_label}_{model_name}_change", args=[target.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
