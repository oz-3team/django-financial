from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse
from django.core.mail import send_mail

from drf_yasg.utils import swagger_auto_schema

from .models import CustomUser
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from .tokens import account_activation_token


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=RegisterSerializer)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = serializer.save(is_active=False)  # 이메일 인증 전 비활성화
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = account_activation_token.make_token(user)
        activation_link = self.request.build_absolute_uri(
            reverse("verify_email", kwargs={"uidb64": uid, "token": token})
        )
        send_mail(
            subject="이메일 인증을 완료해주세요.",
            message=f"다음 링크를 클릭하면 계정이 활성화됩니다:\n{activation_link}",
            from_email="no-reply@yourapp.com",
            recipient_list=[user.email],
        )


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            user = None
        if user and account_activation_token.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({"msg": "Email verified successfully"}, status=200)
        else:
            return Response({"error": "Invalid or expired token"}, status=400)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=LoginSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)

        response = Response(
            {
                "msg": "Login success",
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )
        response.set_cookie("access", str(refresh.access_token), httponly=True)
        response.set_cookie("refresh", str(refresh), httponly=True)
        return response


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.COOKIES.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"error": "Invalid token"}, status=400)
        response = Response({"msg": "Logout success"}, status=200)
        response.delete_cookie("access")
        response.delete_cookie("refresh")
        return response


class UserMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(responses={200: UserSerializer})
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @swagger_auto_schema(request_body=UserSerializer, responses={200: UserSerializer})
    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(request_body=UserSerializer, responses={200: UserSerializer})
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(responses={200: "Deleted successfully"})
    def delete(self, request):
        request.user.delete()
        return Response({"msg": "Deleted successfully"}, status=200)
