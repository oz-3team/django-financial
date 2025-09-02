import pytest
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.db import models
from django.urls import reverse
from django.test import Client

from apps.users.admin import CustomUserAdmin
from apps.users.serializers import RegisterSerializer, LoginSerializer, UserSerializer
from apps.users.tokens import EmailVerificationTokenGenerator

User = get_user_model()
account_activation_token = EmailVerificationTokenGenerator()


def _minimal_user_kwargs():
    kwargs = {}

    username_field = getattr(User, "USERNAME_FIELD", "username")
    try:
        uf = User._meta.get_field(username_field)
    except Exception:
        uf = None

    if uf is not None and isinstance(uf, models.EmailField):
        kwargs[username_field] = f"user_{uuid4().hex[:8]}@example.com"
    else:
        kwargs[username_field] = f"user_{uuid4().hex[:8]}"

    for f in User._meta.get_fields():
        if not isinstance(f, models.Field):
            continue
        if f.auto_created or f.primary_key:
            continue
        if isinstance(
            f, (models.ManyToManyField, models.ForeignKey, models.OneToOneField)
        ):
            continue
        if getattr(f, "auto_now", False) or getattr(f, "auto_now_add", False):
            continue
        if f.name in kwargs:
            continue
        has_default = f.default is not models.NOT_PROVIDED
        if f.null or getattr(f, "blank", False) or has_default:
            continue
        if isinstance(f, models.CharField):
            kwargs[f.name] = f"{f.name}-{uuid4().hex[:8]}"
        elif isinstance(f, models.BooleanField):
            kwargs[f.name] = True
        elif isinstance(f, models.IntegerField):
            kwargs[f.name] = 1
        else:
            kwargs[f.name] = None
    return kwargs


def _make_user(password="pass1234!", **extra_fields):
    kwargs = _minimal_user_kwargs()
    kwargs.update(extra_fields)
    user = User(**kwargs)
    user.set_password(password)
    if hasattr(user, "is_active"):
        user.is_active = user.is_active if hasattr(user, "is_active") else True
    user.full_clean()
    user.save()
    return user


def _make_superuser(password="pass1234!"):
    user = _make_user(
        password=password, is_staff=True, is_superuser=True, is_active=True
    )
    return user


@pytest.mark.django_db
class TestCustomUserModel:
    def test_create_user(self):
        user = User.objects.create_user(
            email="testuser@example.com",
            password="strongpass123",
            nickname="tester",
            name="Test User",
            phone_number="01012345678",
        )
        assert user.email == "testuser@example.com"
        assert user.check_password("strongpass123")
        assert not user.is_staff
        assert not user.is_superuser
        assert not user.is_active  # 기본 비활성화

    def test_create_superuser(self):
        admin_user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        assert admin_user.is_staff
        assert admin_user.is_superuser
        assert admin_user.is_active


@pytest.mark.django_db
class TestRegisterSerializer:
    def test_valid_data(self):
        data = {
            "email": "newregister@example.com",
            "password": "pass123456",
            "nickname": "nick",
            "name": "New User",
            "phone_number": "01099998888",
        }
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid()
        user = serializer.save()
        assert user.email == data["email"]
        assert not user.is_active

    def test_missing_email(self):
        data = {"password": "pass123456"}
        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        assert "email" in serializer.errors


@pytest.mark.django_db
class TestLoginSerializer:
    def setup_method(self):
        self.user = User.objects.create_user(
            email="loginuser@example.com", password="loginpass123", is_active=True
        )

    def test_valid_login(self):
        data = {"email": "loginuser@example.com", "password": "loginpass123"}
        serializer = LoginSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data["user"].email == self.user.email

    def test_invalid_password(self):
        data = {"email": "loginuser@example.com", "password": "wrongpass"}
        serializer = LoginSerializer(data=data)
        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors


@pytest.mark.django_db
class TestUserSerializer:
    def setup_method(self):
        self.user = User.objects.create_user(
            email="userserializer@example.com", password="userpass", is_active=True
        )

    def test_serialize(self):
        serializer = UserSerializer(instance=self.user)
        data = serializer.data
        assert data["email"] == self.user.email
        assert "id" in data
        assert "is_active" in data
        assert "password" not in data


@pytest.mark.django_db
class TestEmailVerificationToken:
    def test_token_generation_and_check(self):
        user = _make_user(email="tokenuser@example.com", password="tokenpass")
        token = account_activation_token.make_token(user)
        assert account_activation_token.check_token(user, token)

    def test_token_invalid_after_activation(self):
        user = _make_user(
            email="tokenuser2@example.com", password="tokenpass", is_active=False
        )
        token = account_activation_token.make_token(user)

        user.is_active = True
        user.save()

        assert not account_activation_token.check_token(user, token)


@pytest.mark.django_db
class TestCustomUserAdmin:
    def setup_method(self):
        self.site = AdminSite()
        self.admin_user = _make_superuser()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.admin = CustomUserAdmin(User, self.site)
        self.normal_user = _make_user(nickname="tester", name="Test User")

    def test_admin_pages_access(self):
        from django.contrib import admin

        if User not in admin.site._registry:
            pytest.skip("User 모델이 admin에 등록되어 있지 않습니다.")
        app_label = User._meta.app_label
        model_name = User._meta.model_name

        url = reverse(f"admin:{app_label}_{model_name}_changelist")
        resp = self.client.get(url)
        assert resp.status_code == 200

        url = reverse(f"admin:{app_label}_{model_name}_add")
        resp = self.client.get(url)
        assert resp.status_code == 200

        url = reverse(
            f"admin:{app_label}_{model_name}_change", args=[self.normal_user.pk]
        )
        resp = self.client.get(url)
        assert resp.status_code == 200

    def test_list_display_fields(self):
        list_display = self.admin.get_list_display(None)
        expected_fields = [
            "id",
            "email",
            "nickname",
            "phone_number",
            "is_active",
            "is_staff",
            "is_superuser",
            "created_at",
        ]
        for field in expected_fields:
            # _has 메서드가 없는 CustomUserAdmin에 맞춰 바로 체크
            assert field in list_display

    def test_readonly_fields_for_superuser(self):
        request = type("Request", (), {"user": self.admin_user})()
        readonly_fields = self.admin.get_readonly_fields(request)
        assert "created_at" in readonly_fields
        assert "last_login" in readonly_fields
        assert "is_staff" not in readonly_fields

    def test_readonly_fields_for_normal_user(self):
        normal_user = _make_user(is_staff=True)
        request = type("Request", (), {"user": normal_user})()
        readonly_fields = self.admin.get_readonly_fields(request)
        assert "is_staff" in readonly_fields
