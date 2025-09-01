from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AnalysisViewSet, TransactionHistoryViewSet

router = DefaultRouter()
router.register(r"analysis", AnalysisViewSet, basename="analysis")
router.register(r"transactions", TransactionHistoryViewSet, basename="transaction")

urlpatterns = [
    path("", include(router.urls)),  # /api/analysis/ + /api/transactions/ 자동 매핑
]

# 트랜잭션은 Viewset이기 때문에 라우터 설정 한 줄로 엔드포인트 생성에 RESTful URL 구조까지 유지가능
# ex)
# HTTP Method	URL	Action
# GET	/api/analysis/transactions/	TransactionHistory 리스트 조회
# POST	/api/analysis/transactions/	새로운 거래 내역 생성
# GET	/api/analysis/transactions/<pk>/	개별 거래 내역 조회
# PUT	/api/analysis/transactions/<pk>/	개별 거래 내역 전체 수정
# PATCH	/api/analysis/transactions/<pk>/	개별 거래 내역 부분 수정
# DELETE	/api/analysis/transactions/<pk>/	개별 거래 내역 삭제
