from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from apps.users.models import CustomUser
from apps.users.tokens import account_activation_token


class AuthFlowTests(APITestCase):
    def test_signup_verify_login_logout(self):
        # 1. 회원가입: 이메일 인증 전 is_active == False
        signup_url = reverse("signup")
        signup_data = {
            "email": "testuser@example.com",
            "password": "strongpassword123",
            "nickname": "testnick",
            "name": "Test User",
            "phone_number": "01012345678",
        }
        response = self.client.post(signup_url, signup_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = CustomUser.objects.get(email="testuser@example.com")
        self.assertFalse(user.is_active)  # 미인증 상태

        # 2. 이메일 인증
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = account_activation_token.make_token(user)
        verify_url = reverse("verify_email", kwargs={"uidb64": uid, "token": token})
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        self.assertTrue(user.is_active)

        # 3. 로그인
        login_url = reverse("login")
        login_data = {"email": "testuser@example.com", "password": "strongpassword123"}
        response = self.client.post(login_url, login_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        access_token = response.data["access"]
        refresh_token = response.data["refresh"]

        # 4. 프로필 조회 (인증 헤더를 달고)
        profile_url = reverse("profile")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "testuser@example.com")

        # 5. 로그아웃
        logout_url = reverse("logout")
        self.client.cookies["refresh"] = refresh_token  # 로그아웃에 refresh 토큰 필요
        response = self.client.post(logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("msg", response.data)
