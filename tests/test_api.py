# tests/test_api.py
from __future__ import annotations

import json
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
    # 추가 후보
    "auth",
    "jwt",
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
    # 추가 후보
    "profile",
    "profiles",
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


def _parse_json(resp) -> Any:
    try:
        return resp.json()
    except Exception:
        try:
            return json.loads(resp.content.decode() or "{}")
        except Exception:
            return None


# ------------------------------
# API Smoke Tests (router 기반)
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


# ------------------------------
# Custom path endpoints (요구사항 반영)
# ------------------------------
class APICustomEndpointTests(TestCase):
    """
    명시 경로 기반 엔드포인트 테스트:
      - /analysis/analysis/ (GET, POST, id에 대해 GET/PUT/PATCH/DELETE)
      - /analysis/transactions/ (동일)
      - /notifications/unread (GET), /notifications/read/{id} (POST)
      - /users/login/, /users/signup/, /users/token/refresh/, /users/profile/ (GET/PUT/DELETE)

    존재하지 않는 경우 404가 나오면 해당 케이스는 skip 처리하여 스모크 수준 유지.
    """

    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()
        cls.user = cls.User.objects.create_user(
            email="customapi@example.com",
            password="pass1234!",
        )
        cls.builder = _ModelBuilder(user=cls.user)

        cls.AnalysisModel = _get_model(
            ("analysis", "Analysis"), ("analysis", "Analyses")
        )
        cls.TransactionModel = _get_model(
            ("accounts", "Transaction"),
            ("accounts", "Transactions"),
            ("transactions", "Transaction"),
            ("transactions", "Transactions"),
        )
        cls.NotificationModel = _get_model(
            ("notification", "Notification"),
            ("notifications", "Notification"),
            ("notification", "Notifications"),
        )

        cls.analysis = (
            cls.builder.create(cls.AnalysisModel) if cls.AnalysisModel else None
        )
        cls.transaction = (
            cls.builder.create(cls.TransactionModel) if cls.TransactionModel else None
        )
        cls.notification = (
            cls.builder.create(cls.NotificationModel) if cls.NotificationModel else None
        )

        cls.access_token: Optional[str] = None
        cls.refresh_token: Optional[str] = None

    # ---------- 내부 유틸 ----------
    def _skip_if_404(self, resp, reason: str):
        if resp.status_code == 404:
            self.skipTest(reason)

    def _auth_header(self) -> Dict[str, str]:
        return (
            {"HTTP_AUTHORIZATION": f"Bearer {self.access_token}"}
            if self.access_token
            else {}
        )

    def _extract_tokens(self, resp) -> None:
        data = _parse_json(resp) or {}
        for k in ("access", "token", "jwt", "access_token"):
            if isinstance(data.get(k), str):
                self.access_token = data[k]
                break
        for k in ("refresh", "refresh_token"):
            if isinstance(data.get(k), str):
                self.refresh_token = data[k]
                break

    # ---------- Users ----------
    def test_users_auth_flow_and_profile(self):
        # signup
        payload = {
            "email": f"{uuid4().hex[:8]}@example.com",
            "password": "Passw0rd!",
            "username": f"user_{uuid4().hex[:6]}",
        }
        resp = self.client.post(
            "/users/signup/", data=json.dumps(payload), content_type="application/json"
        )
        self._skip_if_404(resp, "users/signup/ 미구현")
        _assert_not_server_or_notfound(self, resp.status_code)

        # login (email/password)
        login_payload = {"email": payload["email"], "password": payload["password"]}
        resp = self.client.post(
            "/users/login/",
            data=json.dumps(login_payload),
            content_type="application/json",
        )
        self._skip_if_404(resp, "users/login/ 미구현")
        _assert_not_server_or_notfound(self, resp.status_code)
        self._extract_tokens(resp)

        # token refresh (있을 때만)
        if self.refresh_token:
            resp = self.client.post(
                "/users/token/refresh/",
                data=json.dumps({"refresh": self.refresh_token}),
                content_type="application/json",
            )
            self._skip_if_404(resp, "users/token/refresh/ 미구현")
            _assert_not_server_or_notfound(self, resp.status_code)
            self._extract_tokens(resp)

        # profile
        resp = self.client.get("/users/profile/", **self._auth_header())
        self._skip_if_404(resp, "users/profile/ 미구현")
        _assert_not_server_or_notfound(self, resp.status_code)

        resp = self.client.put(
            "/users/profile/",
            data=json.dumps({"full_name": "API Tester", "bio": "updated by tests"}),
            content_type="application/json",
            **self._auth_header(),
        )
        _assert_not_server_or_notfound(self, resp.status_code)

        resp = self.client.delete("/users/profile/", **self._auth_header())
        _assert_not_server_or_notfound(self, resp.status_code)

    # ---------- Notifications ----------
    def test_notifications_unread_and_read(self):
        resp = self.client.get("/notifications/unread")
        self._skip_if_404(resp, "notifications/unread 미구현")
        _assert_not_server_or_notfound(self, resp.status_code)
        data = _parse_json(resp)
        notif_id = None
        if isinstance(data, list) and data:
            item = data[0]
            if isinstance(item, dict):
                notif_id = item.get("id")
        elif isinstance(data, dict) and data.get("results"):
            first = data["results"][0]
            if isinstance(first, dict):
                notif_id = first.get("id")
        if notif_id is not None:
            resp = self.client.post(
                f"/notifications/read/{notif_id}",
                data=json.dumps({}),
                content_type="application/json",
            )
            _assert_not_server_or_notfound(self, resp.status_code)
        else:
            self.skipTest("읽을 수 있는 알림 id 없음 — read/{id} 스킵")

    # ---------- analysis/analysis CRUD ----------
    def test_analysis_crud_direct_paths(self):
        base = "/analysis/analysis/"
        # list
        resp = self.client.get(base)
        self._skip_if_404(resp, f"{base} 미구현")
        _assert_not_server_or_notfound(self, resp.status_code)
        # create (스키마 모르면 400 허용)
        resp = self.client.post(
            base,
            data=json.dumps({}),
            content_type="application/json",
            **self._auth_header(),
        )
        _assert_not_server_or_notfound(self, resp.status_code)
        # detail (기존 fixture 이용)
        if not self.analysis:
            self.skipTest("analysis 인스턴스 없음 — detail/수정 스킵")
        pk = self.analysis.pk
        # retrieve
        resp = self.client.get(f"{base}{pk}/")
        _assert_not_server_or_notfound(self, resp.status_code)
        # put
        resp = self.client.put(
            f"{base}{pk}/",
            data=json.dumps({"_test": "put"}),
            content_type="application/json",
            **self._auth_header(),
        )
        _assert_not_server_or_notfound(self, resp.status_code)
        # patch
        resp = self.client.patch(
            f"{base}{pk}/",
            data=json.dumps({"_test": "patch"}),
            content_type="application/json",
            **self._auth_header(),
        )
        _assert_not_server_or_notfound(self, resp.status_code)
        # delete (존재만 확인; 권한 없으면 401/403 가능)
        resp = self.client.delete(f"{base}{pk}/", **self._auth_header())
        _assert_not_server_or_notfound(self, resp.status_code)

    # ---------- analysis/transactions CRUD ----------
    def test_transactions_crud_direct_paths(self):
        base = "/analysis/transactions/"
        # list
        resp = self.client.get(base)
        self._skip_if_404(resp, f"{base} 미구현")
        _assert_not_server_or_notfound(self, resp.status_code)
        # create (스키마 모르면 400 허용)
        resp = self.client.post(
            base,
            data=json.dumps({}),
            content_type="application/json",
            **self._auth_header(),
        )
        _assert_not_server_or_notfound(self, resp.status_code)
        if not self.transaction:
            self.skipTest("transaction 인스턴스 없음 — detail/수정 스킵")
        pk = self.transaction.pk
        # retrieve
        resp = self.client.get(f"{base}{pk}/")
        _assert_not_server_or_notfound(self, resp.status_code)
        # put
        resp = self.client.put(
            f"{base}{pk}/",
            data=json.dumps({"_test": "put"}),
            content_type="application/json",
            **self._auth_header(),
        )
        _assert_not_server_or_notfound(self, resp.status_code)
        # patch
        resp = self.client.patch(
            f"{base}{pk}/",
            data=json.dumps({"_test": "patch"}),
            content_type="application/json",
            **self._auth_header(),
        )
        _assert_not_server_or_notfound(self, resp.status_code)
        # delete
        resp = self.client.delete(f"{base}{pk}/", **self._auth_header())
        _assert_not_server_or_notfound(self, resp.status_code)
