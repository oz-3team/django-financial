from rest_framework_simplejwt.tokens import RefreshToken


def set_token_cookies(response, user):
    """
    Refresh / Access 토큰을 생성해서 response 쿠키에 담아주는 함수
    """
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    # 쿠키에 토큰 저장
    response.set_cookie(
        key="access_token",
        value=str(access),
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=3600,  # 1시간
    )
    response.set_cookie(
        key="refresh_token",
        value=str(refresh),
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=7 * 24 * 3600,  # 7일
    )

    return response
