# apps/notification/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Notification
from .serializers import NotificationSerializer


class UnreadNotificationList(generics.ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        # 요청한 유저의 읽지 않은 알림만 조회
        return (
            Notification.objects.filter(user=self.request.user, is_read=False)
            .select_related("user")
            .only("id", "message", "is_read", "created_at", "user__email")
        )


class MarkNotificationRead(APIView):
    def post(self, request, pk):
        try:
            notif = Notification.objects.select_related("user").get(
                pk=pk, user=request.user
            )
        except Notification.DoesNotExist:
            return Response(
                {"detail": "알림이 존재하지 않습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        notif.is_read = True
        notif.save(update_fields=["is_read"])

        return Response({"detail": "알림 읽음 처리 완료"}, status=status.HTTP_200_OK)
