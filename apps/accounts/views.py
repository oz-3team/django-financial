from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Account
from .serializers import AccountSerializer


class AccountViewSet(viewsets.ModelViewSet):
    """
    사용자 계좌 API
    - GET /api/accounts/        : 본인 계좌 목록 조회
    - POST /api/accounts/       : 본인 계좌 생성
    - GET /api/accounts/<id>/   : 특정 계좌 조회
    - DELETE /api/accounts/<id>/: 계좌 삭제
    """

    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Account.objects.filter(owner=self.request.user)
            .select_related("owner")
            .prefetch_related("transactions", "counter_transactions")
        )

    def perform_create(self, serializer):
        """
        계좌 생성 시, 로그인한 사용자를 자동으로 연결
        """
        serializer.save(owner=self.request.user)
