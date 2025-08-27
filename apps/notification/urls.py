# notification/urls.py
from django.urls import path
from .views import UnreadNotificationList, MarkNotificationRead

urlpatterns = [
    path('unread/', UnreadNotificationList.as_view(), name='unread-notifications'),
    path('read/<int:pk>/', MarkNotificationRead.as_view(), name='mark-notification-read'),
]
