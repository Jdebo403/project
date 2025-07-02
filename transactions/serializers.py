from rest_framework import serializers
from decimal import Decimal
from .models import Transaction
from accounts.models import Account
from accounts.serializers import AccountSerializer

class TransactionSerializer(serializers.ModelSerializer):
    from_account = AccountSerializer(read_only=True)
    to_account = AccountSerializer(read_only=True)
    
    class Meta:
        model = Transaction
        fields = ['id', 'user', 'from_account', 'to_account', 'transaction_type', 
                 'amount', 'description', 'reference_number', 'status', 
                 'created_at', 'updated_at', 'bank_name', 'beneficiary_name', 
                 'routing_number', 'beneficiary_address']  # add bank_name
        read_only_fields = ['id', 'user', 'reference_number', 'status', 
                           ]

class DepositSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.01'))
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    
    def validate_account_id(self, value):
        user = self.context['request'].user
        try:
            account = Account.objects.get(id=value, user=user)
            if not account.is_active:
                raise serializers.ValidationError("Account is not active")
            return value
        except Account.DoesNotExist:
            raise serializers.ValidationError("Account not found")

class WithdrawalSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.01'))
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    
    def validate(self, attrs):
        user = self.context['request'].user
        account_id = attrs['account_id']
        amount = attrs['amount']
        
        try:
            account = Account.objects.get(id=account_id, user=user)
            if not account.can_debit(amount):
                if not account.is_active:
                    raise serializers.ValidationError("Account is not active")
                else:
                    raise serializers.ValidationError("Insufficient balance")
            attrs['account'] = account
            return attrs
        except Account.DoesNotExist:
            raise serializers.ValidationError("Account not found")

class TransferSerializer(serializers.Serializer):
    from_account_id = serializers.IntegerField()
    to_account_number = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.01'))
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    
    def validate(self, attrs):
        user = self.context['request'].user
        from_account_id = attrs['from_account_id']
        to_account_number = attrs['to_account_number']
        amount = attrs['amount']
        
        # Validate from account
        try:
            from_account = Account.objects.get(id=from_account_id, user=user)
            if not from_account.can_debit(amount):
                if not from_account.is_active:
                    raise serializers.ValidationError("Your account is not active")
                else:
                    raise serializers.ValidationError("Insufficient balance")
            attrs['from_account'] = from_account
        except Account.DoesNotExist:
            raise serializers.ValidationError("From account not found")
        
        # Validate to account
        try:
            to_account = Account.objects.get(account_number=to_account_number)
            if not to_account.is_active:
                raise serializers.ValidationError("Destination account is not active")
            if to_account.id == from_account_id:
                raise serializers.ValidationError("Cannot transfer to the same account")
            attrs['to_account'] = to_account
        except Account.DoesNotExist:
            raise serializers.ValidationError("Destination account not found")
        
        return attrs

class ExternalTransferSerializer(serializers.Serializer):
    from_account_id = serializers.IntegerField()
    beneficiary_name = serializers.CharField(max_length=100)
    to_account_number = serializers.CharField(max_length=20)
    routing_number = serializers.CharField(max_length=50)
    beneficiary_address = serializers.CharField(max_length=255)
    bank_name = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.01'))
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        user = self.context['request'].user
        from_account_id = attrs['from_account_id']
        amount = attrs['amount']
        # Validate from account
        try:
            from_account = Account.objects.get(id=from_account_id, user=user)
            if not from_account.can_debit(amount):
                if not from_account.is_active:
                    raise serializers.ValidationError("Your account is not active")
                else:
                    raise serializers.ValidationError("Insufficient balance")
            attrs['from_account'] = from_account
        except Account.DoesNotExist:
            raise serializers.ValidationError("From account not found")
        # No to_account validation for external
        return attrs