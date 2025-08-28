from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Analysis
import os

@receiver(post_delete, sender=Analysis)
def delete_analysis_file(sender, instance, **kwargs):
    """Analysis 인스턴스 삭제 시 result_image 파일도 제거"""
    if instance.result_image and os.path.isfile(instance.result_image.path):
        os.remove(instance.result_image.path)