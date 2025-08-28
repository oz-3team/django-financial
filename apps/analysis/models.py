from django.db import models
from django.conf import settings
from datetime import datetime
from uuid import uuid4

def analysis_result_upload_to(instance, filename):
    """MEDIA_ROOT/YYYY/MM/DD/uuid.jpg 형태로 저장"""


    today = datetime.now()
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"  # 유니크 이름 생성

    # 문자열 포맷 사용: MEDIA_ROOT 기준 상대경로
    return f"{today.year}/{today.month:02}/{today.day:02}/{filename}"

class Analysis(models.Model):
    PERIOD_CHOICES = [
        ('DAILY', '일간'),
        ('WEEKLY', '주간'),
        ('MONTHLY', '월간'),
        ('YEARLY', '연간'),
    ]

    ANALYSIS_TARGET_CHOICES = [
        ('INCOME', '수입'),
        ('EXPENSE', '지출'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='analyses'
    )
    analysis_target = models.CharField(max_length=10, choices=ANALYSIS_TARGET_CHOICES)
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    description = models.TextField(blank=True, null=True)
    result_image = models.ImageField(
        upload_to=analysis_result_upload_to,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'analysis_target', 'period_type', 'start_date', 'end_date'],
                name='unique_analysis'
            )
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.get_analysis_target_display()} ({self.get_period_type_display()})"
