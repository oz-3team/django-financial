from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from apps.users.admin import SafeUserAdmin
from apps.users.serializers import RegisterSerializer, LoginSerializer, UserSerializer
from apps.users.tokens import EmailVerificationTokenGenerator

User = get_user_model()
account_activation_token = EmailVerificationTokenGenerator()


class CustomUserModelTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            email="testuser@example.com",
            password="strongpass123",
            nickname="tester",
            name="Test User",
            phone_number="01012345678",
        )
        self.assertEqual(user.email, "testuser@example.com")
        self.assertTrue(user.check_password("strongpass123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_active)  # 비활성화 기본

    def test_create_superuser(self):
        admin_user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)


class RegisterSerializerTests(TestCase):
    def test_valid_data(self):
        data = {
            "email": "newregister@example.com",
            "password": "pass123456",
            "nickname": "nick",
            "name": "New User",
            "phone_number": "01099998888",
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.email, data["email"])
        self.assertFalse(user.is_active)

    def test_missing_email(self):
        data = {"password": "pass123456"}
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)


class LoginSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="loginuser@example.com", password="loginpass123", is_active=True
        )

    def test_valid_login(self):
        data = {"email": "loginuser@example.com", "password": "loginpass123"}
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["user"].email, self.user.email)

    def test_invalid_password(self):
        data = {"email": "loginuser@example.com", "password": "wrongpass"}
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)


class UserSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="userserializer@example.com", password="userpass", is_active=True
        )

    def test_serialize(self):
        serializer = UserSerializer(instance=self.user)
        data = serializer.data
        self.assertEqual(data["email"], self.user.email)
        self.assertIn("id", data)
        self.assertIn("is_active", data)
        self.assertNotIn("password", data)


class AccountActivationTokenTests(TestCase):
    def test_token_generation_and_check(self):
        user = User.objects.create_user(
            email="tokenuser@example.com", password="tokenpass"
        )
        token = account_activation_token.make_token(user)
        self.assertTrue(account_activation_token.check_token(user, token))

    def test_token_invalid_after_activation(self):
        # 토큰 생성 시는 비활성 상태
        user = User.objects.create_user(
            email="tokenuser2@example.com", password="tokenpass", is_active=False
        )
        token = account_activation_token.make_token(user)

        # 유저가 활성화됨
        user.is_active = True
        user.save()

        # 토큰 검증 시 False가 되어야 함
        self.assertFalse(account_activation_token.check_token(user, token))


class AdminTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = SafeUserAdmin(User, AdminSite())
        self.user = User.objects.create_user(
            email="staffuser@example.com", password="pass1234", is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            email="superuser@example.com", password="pass1234"
        )

    def test_get_list_display(self):
        request = self.factory.get("/")
        list_display = self.admin.get_list_display(request)
        self.assertIn("email", list_display)
        self.assertIn("id", list_display)

    def test_get_readonly_fields_for_non_superuser(self):
        request = self.factory.get("/")
        request.user = self.user
        readonly_fields = self.admin.get_readonly_fields(request)
        self.assertIn("password", readonly_fields)
        self.assertIn("last_login", readonly_fields)
        self.assertIn("created_at", readonly_fields)

    def test_get_readonly_fields_for_superuser(self):
        request = self.factory.get("/")
        request.user = self.superuser
        readonly_fields = self.admin.get_readonly_fields(request)
        self.assertNotIn("is_staff", readonly_fields)
