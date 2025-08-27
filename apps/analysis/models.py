from django.db import models
from django.conf import settings  # 커스텀 유저 모델 참조

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
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True, null=True)
    result_image = models.ImageField(upload_to='analysis_results/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.analysis_target} ({self.period_type})"
