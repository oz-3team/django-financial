from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions, mixins
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from .serializers import (
    UserSignupSerializer,
    UserProfileSerializer,
    CustomTokenObtainPairSerializer,
)
from .services import UserService
from .utils import set_token_cookies
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


# ------------------------------
# ✅ 커스텀 페이징 클래스
# ------------------------------
class UserListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


# ------------------------------
# ✅ SUPERUSER 전용 유저 리스트
# ------------------------------
class UserListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    superuser 또는 staff 전용 유저 목록 조회
    """

    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = UserListPagination
    throttle_classes = [UserRateThrottle]


# ------------------------------
# ✅ 회원가입
# ------------------------------
class UserSignupViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = UserSignupSerializer
    throttle_classes = [AnonRateThrottle]

    @swagger_auto_schema(
        request_body=UserSignupSerializer, responses={201: UserSignupSerializer}
    )
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = UserService.create_user(**serializer.validated_data)
            UserService.send_verification_email(user)
            logger.info(f"User {user.email} signed up successfully.")
            return Response(
                UserSignupSerializer(user).data, status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Signup failed: {str(e)}")
            return Response(
                {"error": "회원가입에 실패했습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ------------------------------
# ✅ JWT 로그인
# ------------------------------
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    @swagger_auto_schema(request_body=CustomTokenObtainPairSerializer)
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user
        refresh = serializer.get_token(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        response = Response(
            {"message": "로그인에 성공했습니다."}, status=status.HTTP_200_OK
        )
        set_token_cookies(
            response, access_token, refresh_token, secure=True, samesite="Strict"
        )
        logger.info(f"User {user.email} logged in successfully.")
        return response


# ------------------------------
# ✅ JWT 토큰 갱신
# ------------------------------
class CustomTokenRefreshView(TokenRefreshView):
    throttle_classes = [UserRateThrottle]

    @swagger_auto_schema(request_body=None)
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"])
        if not refresh_token:
            logger.warning("Refresh token not found.")
            return Response(
                {"error": "리프레시 토큰이 없습니다."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = self.get_serializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
            access_token = serializer.validated_data["access"]
            response = Response(
                {"message": "토큰이 갱신되었습니다."}, status=status.HTTP_200_OK
            )
            set_token_cookies(
                response, access_token=access_token, secure=True, samesite="Strict"
            )
            logger.info("Token refreshed successfully.")
            return response
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            return Response(
                {"error": "토큰 갱신에 실패했습니다."},
                status=status.HTTP_401_UNAUTHORIZED,
            )


# ------------------------------
# ✅ 프로필 조회/수정/삭제
# ------------------------------
class UserProfileViewSet(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer
    throttle_classes = [UserRateThrottle]

    def get_object(self):
        return self.request.user

    @swagger_auto_schema(
        method="post",
        request_body=UserProfileSerializer,
        responses={200: "Password reset link sent"},
    )
    @action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny])
    def request_password_reset(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "이메일을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            UserService.request_password_reset(email)
            logger.info(f"Password reset requested for {email}.")
            return Response(
                {"message": "비밀번호 재설정 링크가 전송되었습니다."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Password reset request failed: {str(e)}")
            return Response(
                {"error": "비밀번호 재설정 요청에 실패했습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
