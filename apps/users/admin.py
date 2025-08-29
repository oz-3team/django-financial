# apps/users/admin.py
from __future__ import annotations

from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth import get_user_model

User = get_user_model()


class SafeUserAdmin(admin.ModelAdmin):
    """
    커스텀/기본 User 모델 모두 안전하게 등록하기 위한 Admin.
    - 검색: username, email, first_name, last_name(있는 것만)
    - 필터: is_active, is_staff, is_superuser, date_joined, last_login(있는 것만)
    - 읽기 전용: last_login, date_joined, password(있는 것만)
    - 리스트 컬럼: id, username, email, is_active, is_staff, is_superuser, last_login, date_joined(있는 것만)
    """

    def _has(self, name: str) -> bool:
        return any(
            getattr(f, "name", None) == name for f in self.model._meta.get_fields()
        )

    # 목록 컬럼
    def get_list_display(self, request):
        cols = []
        for f in (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
            "date_joined",
        ):
            if self._has(f):
                cols.append(f)
        return tuple(cols) or ("pk",)

    # 검색 필드
    def get_search_fields(self, request):
        fields = []
        for f in ("username", "email", "first_name", "last_name"):
            if self._has(f):
                fields.append(f)
        return tuple(fields) or ("pk",)

    # 오른쪽 필터
    def get_list_filter(self, request):
        fields = []
        for f in ("is_active", "is_staff", "is_superuser", "date_joined", "last_login"):
            if self._has(f):
                fields.append(f)
        return tuple(fields)

    # 읽기 전용 필드
    def get_readonly_fields(self, request, obj=None):
        fields = []
        for f in ("last_login", "date_joined", "password"):
            if self._has(f):
                fields.append(f)
        return tuple(fields)

    ordering = ("-id",)
    list_per_page = 50


# 기본 UserAdmin이 이미 등록돼 있을 수 있으므로 안전하게 언레지스터 후 등록
try:
    admin.site.unregister(User)
except (admin.sites.NotRegistered, AlreadyRegistered):  # 둘 중 어떤 예외가 오든 무시
    pass

admin.site.register(User, SafeUserAdmin)
