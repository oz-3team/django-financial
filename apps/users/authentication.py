from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings


class JWTCookieAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Authorization 헤더보다 쿠키 토큰 우선 사용
        raw_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE_ACCESS"])
        if raw_token is None:
            header = self.get_header(request)
            if header is None:
                return None
            raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
