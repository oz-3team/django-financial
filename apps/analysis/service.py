from apps.accounts.models import TransactionHistory, Account
from django.db.models import Sum, Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear


class AnalysisService:
    @staticmethod
    def get_transaction_queryset(analysis):
        """분석 대상 거래 내역 조회"""
        user_accounts = Account.objects.filter(user=analysis.user)
        qs = TransactionHistory.objects.filter(
            account__in=user_accounts,
            occurred_at__date__range=[analysis.start_date, analysis.end_date],
        ).select_related("account")  # 1:1 관계 N+1 문제 해결

        return qs  # ⚡ 반환 추가

    @staticmethod
    def get_analysis_data(analysis):
        """분석 데이터 생성"""
        qs = AnalysisService.get_transaction_queryset(analysis)
        total_amount = sum(t.amount for t in qs)
        transaction_count = qs.count()

        trunc_func = {
            "DAILY": TruncDay,
            "WEEKLY": TruncWeek,
            "MONTHLY": TruncMonth,
            "YEARLY": TruncYear,
        }[analysis.period_type]

        period_data = (
            qs.annotate(period=trunc_func("occurred_at"))
            .values("period")
            .annotate(total_amount=Sum("amount"), transaction_count=Count("id"))
            .order_by("period")
        )

        return {
            "total_amount": total_amount,
            "transaction_count": transaction_count,
            "period_data": list(period_data),
            "currency": qs.first().currency if qs.exists() else "KRW",
        }
