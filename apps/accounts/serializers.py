from rest_framework import serializers
from .models import Account

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'account_number', 'bank_name', 'balance', 'created_at']
        read_only_fields = ['id', 'balance', 'created_at']
