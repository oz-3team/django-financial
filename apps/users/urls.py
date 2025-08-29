from django.urls import path
from apps.users.views import (
    UserSignupView,
    CustomTokenObtainPairView,
    UserProfileView,
    CustomTokenRefreshView,
)

app_name = "users"

urlpatterns = [
    path("signup/", UserSignupView.as_view(), name="signup"),
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("profile/", UserProfileView.as_view(), name="profile"),
]
