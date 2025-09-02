from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Notification


@receiver(post_save, sender=Notification)
def notify_on_create(sender, instance, created, **kwargs):
    if created:
        print(f"새 알림 생성: {instance.message}")
