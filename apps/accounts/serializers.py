from rest_framework import serializers
from .models import Account


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "name", "number", "balance", "created_at"]
        read_only_fields = ["id", "balance", "created_at"]


# model 과 테이블 이름 일치하게 수정
