from rest_framework import serializers
from .models import Analysis
from apps.accounts.models import TransactionHistory


class AnalysisSerializer(serializers.ModelSerializer):
    # 클라이언트가 보낼 필요 없이, 현재 요청을 보낸 사용자를 자동으로 할당
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Analysis
        fields = "__all__"


class TransactionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionHistory
        fields = "__all__"
        read_only_fields = ("id", "running_balance", "posted_at")
