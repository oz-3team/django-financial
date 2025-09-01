import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import CustomUser
from apps.notification.models import Notification
from datetime import date, timedelta


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestAllAPIs:
    def test_user_signup_and_email_verify(self, api_client):
        user_data = {
            "email": "testuser@example.com",
            "password": "strongpass123",
            "nickname": "tester",
            "name": "Test User",
            "phone_number": "01012345678",
        }
        signup_url = reverse("signup")
        resp = api_client.post(signup_url, user_data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        user = CustomUser.objects.get(email=user_data["email"])
        assert not user.is_active

        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from apps.users.tokens import account_activation_token

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = account_activation_token.make_token(user)
        verify_url = reverse("verify_email", kwargs={"uidb64": uidb64, "token": token})
        resp2 = api_client.get(verify_url)
        assert resp2.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_active

    def test_user_login_and_profile_logout(self, api_client):
        email = "loginuser@example.com"
        password = "testpass123"
        CustomUser.objects.create_user(email=email, password=password, is_active=True)

        login_url = reverse("login")
        resp = api_client.post(
            login_url, {"email": email, "password": password}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "access" in resp.data
        tokens = resp.data

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        profile_url = reverse("profile")
        resp2 = api_client.get(profile_url)
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.data["email"] == email

        api_client.cookies["refresh"] = tokens["refresh"]
        logout_url = reverse("logout")
        resp3 = api_client.post(logout_url)
        assert resp3.status_code == status.HTTP_200_OK
        assert "msg" in resp3.data

    def test_account_crud(self, api_client):
        user = CustomUser.objects.create_user(
            email="accuser@test.com", password="testpass", is_active=True
        )
        login_url = reverse("login")
        resp = api_client.post(
            login_url, {"email": user.email, "password": "testpass"}, format="json"
        )
        token = resp.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        create_url = reverse("accounts-list")
        acc_data = {"name": "테스트계좌", "number": "5555", "currency": "KRW"}
        resp = api_client.post(create_url, acc_data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

        resp2 = api_client.get(create_url)
        assert resp2.status_code == status.HTTP_200_OK
        results = (
            resp2.data
            if isinstance(resp2.data, list)
            else resp2.data.get("results", [])
        )
        assert any(acc["number"] == "5555" for acc in results)

        acc_id = resp.data["id"]
        detail_url = reverse("accounts-detail", args=[acc_id])
        resp3 = api_client.get(detail_url)
        assert resp3.status_code == status.HTTP_200_OK
        assert resp3.data["number"] == "5555"

        resp4 = api_client.delete(detail_url)
        assert resp4.status_code == status.HTTP_204_NO_CONTENT

    def test_analysis_crud(self, api_client):
        user = CustomUser.objects.create_user(
            email="analysisuser@test.com", password="testpass", is_active=True
        )
        login_url = reverse("login")
        resp = api_client.post(
            login_url, {"email": user.email, "password": "testpass"}, format="json"
        )
        token = resp.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("analysis-list")
        start_date = date.today()
        end_date = start_date + timedelta(days=30)
        data = {
            "analysis_target": "INCOME",
            "period_type": "MONTHLY",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "description": "API 테스트 생성",
        }
        post_resp = api_client.post(url, data, format="json")
        print("Response status:", post_resp.status_code)
        print("Response data:", post_resp.data)
        assert post_resp.status_code == status.HTTP_201_CREATED

        assert post_resp.status_code == status.HTTP_201_CREATED
        analysis_id = post_resp.data["id"]

        get_resp = api_client.get(url)
        assert get_resp.status_code == status.HTTP_200_OK
        results = get_resp.data.get("results", [])
        assert any(item["id"] == analysis_id for item in results)

        detail_url = reverse("analysis-detail", args=[analysis_id])
        detail_resp = api_client.get(detail_url)
        assert detail_resp.status_code == status.HTTP_200_OK
        assert detail_resp.data["description"] == "API 테스트 생성"

        patch_resp = api_client.patch(
            detail_url, {"description": "수정 완료"}, format="json"
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.data["description"] == "수정 완료"

        del_resp = api_client.delete(detail_url)
        assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    def test_notification_unread_and_mark_read(self, api_client):
        user = CustomUser.objects.create_user(
            email="notifyuser@test.com", password="testpass", is_active=True
        )
        login_url = reverse("login")
        resp = api_client.post(
            login_url, {"email": user.email, "password": "testpass"}, format="json"
        )
        token = resp.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        notif = Notification.objects.create(user=user, message="미확인 알림 테스트")

        unread_url = reverse("unread-notifications")
        unread_resp = api_client.get(unread_url)
        assert unread_resp.status_code == status.HTTP_200_OK
        assert isinstance(unread_resp.data, dict)
        assert unread_resp.data["count"] >= 1
        assert any(n["id"] == notif.id for n in unread_resp.data["results"])

        mark_read_url = reverse("mark-notification-read", args=[notif.id])
        mark_resp = api_client.post(mark_read_url)
        assert mark_resp.status_code == status.HTTP_200_OK

        notif.refresh_from_db()
        assert notif.is_read is True
