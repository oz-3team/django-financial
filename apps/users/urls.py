from django.urls import path
from .views import (
    RegisterView,
    VerifyEmailView,
    LoginView,
    LogoutView,
    UserMeView,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("signup/", RegisterView.as_view(), name="signup"),
    path(
        "verify-email/<uidb64>/<token>/", VerifyEmailView.as_view(), name="verify_email"
    ),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", UserMeView.as_view(), name="profile"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
