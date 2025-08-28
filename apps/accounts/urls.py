from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AccountViewSet, TransactionHistoryViewSet  # ✅ TransactionHistoryViewSet 추가

router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='accounts')
router.register(r'transactions', TransactionHistoryViewSet, basename='transactions')  # ✅ 거래 내역 추가

urlpatterns = [
    path('', include(router.urls)),
]
