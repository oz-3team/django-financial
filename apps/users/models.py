from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

# 1️⃣ 커스텀 User 매니저
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """
        일반 사용자 생성
        """
        if not email:
            raise ValueError("이메일은 필수입니다.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        슈퍼유저 생성
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('슈퍼유저는 is_staff=True 이어야 합니다.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('슈퍼유저는 is_superuser=True 이어야 합니다.')

        return self.create_user(email, password, **extra_fields)


# 2️⃣ 커스텀 User 모델
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, max_length=255)
    username = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=False)  # 계정 활성화 여부
    is_staff = models.BooleanField(default=False)   # 관리자 권한
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # email 외 필수 필드

    def __str__(self):
        return self.email
