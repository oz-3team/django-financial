from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserSignupViewSet,
    UserProfileViewSet,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    UserListViewSet,
)

router = DefaultRouter()
# 회원가입
router.register(r"signup", UserSignupViewSet, basename="signup")
# 프로필
router.register(r"profile", UserProfileViewSet, basename="profile")
# 관리자용 사용자 목록 (basename 변경)
router.register(r"users", UserListViewSet, basename="user-list")

urlpatterns = [
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path(
        "auth/password-reset/",
        UserProfileViewSet.as_view({"post": "request_password_reset"}),
        name="password_reset",
    ),
    path("", include(router.urls)),
]
