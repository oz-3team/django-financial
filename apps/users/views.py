from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from apps.users.serializers import UserSignupSerializer, CustomTokenObtainPairSerializer, UserProfileSerializer, UserUpdateSerializer
from apps.users.services import UserService
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf import settings
from apps.users.jwt import set_token_cookies

class UserSignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = UserService.create_user(**serializer.validated_data)
                return Response(UserSignupSerializer(user).data, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CustomTokenObtainPairSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.user
            refresh = serializer.get_token(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            response = Response({'message': 'Login successful'}, status=status.HTTP_200_OK)
            set_token_cookies(response, access_token, refresh_token)
            return response

        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
        if not refresh_token:
            return Response({'error': 'Refresh token not found in cookies'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = self.get_serializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)

        access_token = serializer.validated_data['access']
        response = Response({'message': 'Token refreshed'}, status=status.HTTP_200_OK)
        set_token_cookies(response, access_token=access_token)
        return response

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            user = UserService.update_user(request.user, serializer.validated_data)
            return Response(UserProfileSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        UserService.delete_user(request.user)
        response = Response({'message': 'Deleted successfully'}, status=status.HTTP_200_OK)
        response.delete_cookie(settings.SIMPLE_JWT['AUTH_COOKIE_ACCESS'])
        response.delete_cookie(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
        return response