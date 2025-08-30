# apps/notification/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Notification
from .serializers import NotificationSerializer


class UnreadNotificationList(generics.ListAPIView):
    """
    요청한 유저의 읽지 않은 알림 리스트를 반환.
    최신 알림 순으로 정렬됨
    """

    serializer_class = NotificationSerializer

    def get_queryset(self):
        return (
            Notification.objects.filter(user=self.request.user, is_read=False)
            .select_related("user")
            .only("id", "message", "is_read", "created_at", "user__email")
            .order_by("-created_at")  # 최신 알림 먼저
        )


class MarkNotificationRead(APIView):
    """
    특정 알림을 읽음 처리하는 API.
    URL Parameter: pk (알림 ID)
    """

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
