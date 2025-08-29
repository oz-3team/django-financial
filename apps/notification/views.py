# notification/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Notification
from .serializers import NotificationSerializer


class UnreadNotificationList(generics.ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        # user 정보 미리 가져오기 + 필요한 필드만 조회
        return (
            Notification.objects.filter(user=self.request.user, is_read=False)
            .select_related("user")
            .only("id", "message", "is_read", "created_at", "user__email")
        )


class MarkNotificationRead(APIView):
    def post(self, request, pk):
        try:
            # 단건 조회 시 select_related 적용 가능
            notif = Notification.objects.select_related("user").get(
                pk=pk, user=request.user
            )
        except Notification.DoesNotExist:
            return Response(
                {"detail": "알림이 존재하지 않습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 단일 알림 읽음 처리
        notif.is_read = True
        notif.save()

        return Response({"detail": "알림 읽음 처리 완료"}, status=status.HTTP_200_OK)
