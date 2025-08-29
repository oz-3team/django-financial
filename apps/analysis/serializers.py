from rest_framework import serializers
from .models import Analysis
from apps.accounts.models import TransactionHistory


class AnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analysis
        fields = "__all__"


class TransactionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionHistory
        fields = "__all__"
        read_only_fields = ("id", "running_balance", "posted_at")
