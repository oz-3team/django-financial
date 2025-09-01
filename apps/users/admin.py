# from django.contrib import admin
# from django.contrib.admin.sites import AlreadyRegistered
# from django.contrib.auth import get_user_model
# from django.utils.translation import gettext_lazy as _
#
# User = get_user_model()
#
#
# class SafeUserAdmin(admin.ModelAdmin):
#     """
#     커스텀/기본 User 모델 모두 안전하게 등록하기 위한 Admin.
#     - 검색: username, email, first_name, last_name(있는 것만)
#     - 필터: is_active, is_staff, is_superuser, date_joined, last_login(있는 것만)
#     - 읽기 전용: last_login, date_joined, password(있는 것만)
#     - 리스트 컬럼: id, username, email, is_active, is_staff, is_superuser, last_login, date_joined(있는 것만)
#     """
#
#     def _has(self, name: str) -> bool:
#         return any(
#             getattr(f, "name", None) == name for f in self.model._meta.get_fields()
#         )
#
#     # 목록 컬럼
#     def get_list_display(self, request):
#         cols = []
#         for f in (
#             "id",
#             "username",
#             "email",
#             "first_name",
#             "last_name",
#             "is_active",
#             "is_staff",
#             "is_superuser",
#             "last_login",
#             "created_at",
#         ):
#             if self._has(f):
#                 cols.append(f)
#         return tuple(cols) or ("pk",)
#
#     # 검색 필드
#     def get_search_fields(self, request):
#         fields = []
#         for f in ("email", "nickname", "name", "phone_number"):
#             if self._has(f):
#                 fields.append(f)
#         return tuple(fields) or ("pk",)
#
#     # 오른쪽 필터
#     def get_list_filter(self, request):
#         fields = []
#         for f in ("is_active", "is_staff", "is_superuser"):
#             if self._has(f):
#                 fields.append(f)
#         return tuple(fields)
#
#     # 읽기 전용 필드
#     def get_readonly_fields(self, request, obj=None):
#         fields = [f for f in ("last_login", "created_at", "password") if self._has(f)]
#         if not request.user.is_superuser and self._has("is_staff"):
#             fields.append("is_staff")
#         return tuple(fields)
#
#     def get_fieldsets(self, request, obj=None):
#         basic_fields = [f for f in ("email", "password") if self._has(f)]
#         personal_fields = [
#             f for f in ("nickname", "name", "phone_number") if self._has(f)
#         ]
#         permission_fields = [
#             f
#             for f in (
#                 "is_active",
#                 "is_staff",
#                 "is_superuser",
#                 "groups",
#                 "user_permissions",
#             )
#             if self._has(f)
#         ]
#         date_fields = [f for f in ("last_login", "created_at") if self._has(f)]
#
#         fieldsets = []
#         if basic_fields:
#             fieldsets.append((None, {"fields": basic_fields}))
#         if personal_fields:
#             fieldsets.append((_("개인 정보"), {"fields": personal_fields}))
#         if permission_fields:
#             fieldsets.append((_("권한"), {"fields": permission_fields}))
#         if date_fields:
#             fieldsets.append((_("중요 일시"), {"fields": date_fields}))
#
#         return tuple(fieldsets)
#
#     add_fieldsets = (
#         (
#             None,
#             {
#                 "classes": ("wide",),
#                 "fields": (
#                     "email",
#                     "nickname",
#                     "name",
#                     "phone_number",
#                     "password1",
#                     "password2",
#                     "is_active",
#                 ),
#             },
#         ),
#     )
#
#     filter_horizontal = ("groups", "user_permissions")
#     ordering = ("-id",)
#     list_per_page = 50
#
#
# # 기본 UserAdmin이 이미 등록돼 있을 수 있으므로 안전하게 언레지스터 후 등록
# try:
#     admin.site.unregister(User)
# except (admin.sites.NotRegistered, AlreadyRegistered):  # 둘 중 어떤 예외가 오든 무시
#     pass
#
# admin.site.register(User, SafeUserAdmin)
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        "id",
        "email",
        "nickname",
        "phone_number",
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    )
    search_fields = ("email", "nickname", "phone_number")
    list_filter = ("is_staff", "is_active", "created_at")
    readonly_fields = ("created_at", "last_login")

    # 슈퍼유저가 아니면 is_staff 필드는 읽기 전용
    def get_readonly_fields(self, request, obj=None):
        ro = list(self.readonly_fields)
        if not request.user.is_superuser:
            ro.append("is_staff")
        return ro

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("개인 정보"), {"fields": ("nickname", "name", "phone_number")}),
        (
            _("권한"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("중요 일시"), {"fields": ("last_login", "created_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "nickname",
                    "name",
                    "phone_number",
                    "password1",
                    "password2",
                    "is_active",
                ),
            },
        ),
    )

    ordering = ("-created_at",)
    filter_horizontal = ("groups", "user_permissions")
