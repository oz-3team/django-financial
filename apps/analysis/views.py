from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.accounts.models import TransactionHistory
from .models import Analysis
from .serializers import AnalysisSerializer, TransactionHistorySerializer


# ----------------------------
# Analysis API (ViewSet)
# ----------------------------
class AnalysisViewSet(viewsets.ModelViewSet):
    """
    분석 데이터 CRUD API
    - 로그인 유저의 분석 데이터만 접근 가능
    - period_type, analysis_target으로 필터링 지원
    """

    serializer_class = AnalysisSerializer
    permission_classes = [IsAuthenticated]

    filterset_fields = {
        "period_type": ["exact"],
        "analysis_target": ["exact"],
    }

    def get_queryset(self):
        return Analysis.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ----------------------------
# TransactionHistory API
# ----------------------------
class TransactionHistoryViewSet(viewsets.ModelViewSet):
    """
    거래내역 CRUD API
    - 로그인 유저의 계정에 속한 거래내역만 조회 가능
    - 거래유형, 금액범위, 날짜범위, 계정별 필터링 지원
    - 금액, 날짜순 정렬 지원
    - 설명(description) 검색 지원
    """

    serializer_class = TransactionHistorySerializer
    permission_classes = [IsAuthenticated]

    filterset_fields = {
        "tx_type": ["exact"],
        "amount": ["gte", "lte"],
        "occurred_at": ["gte", "lte"],
        "account": ["exact"],
    }
    ordering_fields = ["amount", "occurred_at"]
    ordering = ["-occurred_at"]  # 기본 정렬: 최신순
    search_fields = ["description"]

    def get_queryset(self):
        return TransactionHistory.objects.filter(
            account__owner=self.request.user
        ).select_related("account")


# request.GET으로 수동처리하기보다 DjangoFilterBackend 를 채택했고 준 필수적인 녀석이라고함
# base.py에 각각 설정해뒀기 때문에 filterset_fields으로 url필터링,
# ordering_fields로 정렬, 페이지네이션도 설정해뒀기 때문에 적용중임.
# 해당 설정들은 전역으로 Viewset과 ListAPIView에 자동 적용되니 임포트 해서 사용만하면 기본적으로 사용가능
# DRF 쪽 페이징,sort등의 기능도 호환되고 코드도 깔끔하며, 여러 경우의 수가 늘어나더라도
# 더욱 용이하다고함

# 트랜잭션 히스토리 테스트 순서

# docker-compose exec web python manage.py shell
# from apps.accounts.models import Account
# from django.contrib.auth import get_user_model
# import uuid
#
# User = get_user_model()
# user = User.objects.get(id=1)  # 로그인 유저
#
# # 테스트용 계좌 생성
# acc = Account.objects.create(
#     owner=user,
#     name="테스트 계좌",
#     number=str(uuid.uuid4())[:16],
#     currency="KRW",
#     balance=0
# )
# print(acc.id)  # 이 UUID를 TransactionHistory POST에 사용
