from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction, models
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
import uuid
from decimal import Decimal

from .models import Transaction
from .serializers import (
    TransactionSerializer, 
    DepositSerializer, 
    WithdrawalSerializer, 
    TransferSerializer,
    ExternalTransferSerializer
)
from accounts.models import Account
from users.serializers import UserSerializer
from rest_framework.views import APIView

class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['transaction_type', 'status']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']
    search_fields = ['description', 'reference_number']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Transaction.objects.all()
        # Show transactions where user is sender or recipient
        return Transaction.objects.filter(
            models.Q(user=user) | models.Q(to_account__user=user)
        ).distinct()

class TransactionDetailView(generics.RetrieveAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_admin:
            return Transaction.objects.all()
        return Transaction.objects.filter(user=self.request.user)

class DepositView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        serializer = DepositSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            account_id = serializer.validated_data['account_id']
            amount = serializer.validated_data['amount']
            description = serializer.validated_data.get('description', '')
            with transaction.atomic():
                account = Account.objects.select_for_update().get(id=account_id, user=request.user)
                trans = Transaction.objects.create(
                    user=request.user,
                    to_account=account,
                    transaction_type='deposit',
                    amount=amount,
                    description=description,
                    reference_number=f"DEP{uuid.uuid4().hex[:8].upper()}",
                    status='completed'
                )
                account.balance += amount
                account.save()
                return Response({
                    'message': 'Deposit successful',
                    'transaction': TransactionSerializer(trans).data,
                    'new_balance': account.balance
                }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WithdrawView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        serializer = WithdrawalSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            account = serializer.validated_data['account']
            amount = serializer.validated_data['amount']
            description = serializer.validated_data.get('description', '')
            with transaction.atomic():
                account = Account.objects.select_for_update().get(id=account.id)
                if not account.can_debit(amount):
                    return Response({'error': 'Insufficient balance or account not active'}, status=status.HTTP_400_BAD_REQUEST)
                trans = Transaction.objects.create(
                    user=request.user,
                    from_account=account,
                    transaction_type='withdrawal',
                    amount=amount,
                    description=description,
                    reference_number=f"WTD{uuid.uuid4().hex[:8].upper()}",
                    status='completed'
                )
                account.balance -= amount
                account.save()
                return Response({
                    'message': 'Withdrawal successful',
                    'transaction': TransactionSerializer(trans).data,
                    'new_balance': account.balance
                }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TransferView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        print('TRANSFER REQUEST DATA:', request.data)  # Debug print for Postman testing
        print('AUTH USER:', request.user)
        print('AUTH TOKEN:', request.auth)
        print('HEADERS:', dict(request.headers))
        serializer = TransferSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            from_account = serializer.validated_data['from_account']
            to_account = serializer.validated_data['to_account']
            amount = serializer.validated_data['amount']
            description = serializer.validated_data.get('description', '')
            with transaction.atomic():
                from_account = Account.objects.select_for_update().get(id=from_account.id)
                to_account = Account.objects.select_for_update().get(id=to_account.id)
                if not from_account.can_debit(amount):
                    return Response({'error': 'Insufficient balance or account not active'}, status=status.HTTP_400_BAD_REQUEST)
                if not to_account.can_credit(amount):
                    return Response({'error': 'Destination account cannot receive funds'}, status=status.HTTP_400_BAD_REQUEST)
                trans = Transaction.objects.create(
                    user=request.user,
                    from_account=from_account,
                    to_account=to_account,
                    transaction_type='transfer',
                    amount=amount,
                    description=description,
                    reference_number=f"TRF{uuid.uuid4().hex[:8].upper()}",
                    status='completed'
                )
                from_account.balance -= amount
                to_account.balance += amount
                from_account.save()
                to_account.save()
                return Response({
                    'message': 'Transfer successful',
                    'transaction': TransactionSerializer(trans).data,
                    'new_balance': from_account.balance
                }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ExternalTransferView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        serializer = ExternalTransferSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            from_account = serializer.validated_data['from_account']
            amount = serializer.validated_data['amount']
            bank_name = serializer.validated_data['bank_name']
            to_account_number = serializer.validated_data['to_account_number']
            beneficiary_name = serializer.validated_data['beneficiary_name']
            routing_number = serializer.validated_data['routing_number']
            beneficiary_address = serializer.validated_data['beneficiary_address']
            description = serializer.validated_data.get('description', '')
            # Deduct funds immediately for pending external transfer
            from_account.balance -= amount
            from_account.save()
            trans = Transaction.objects.create(
                user=request.user,
                from_account=from_account,
                transaction_type='external',
                amount=amount,
                description=description,
                reference_number=f"EXT{uuid.uuid4().hex[:8].upper()}",
                status='pending',
                bank_name=bank_name,
                beneficiary_name=beneficiary_name,
                routing_number=routing_number,
                beneficiary_address=beneficiary_address
            )
            return Response({
                'message': 'External transfer initiated and pending admin approval.',
                'transaction': TransactionSerializer(trans).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TransactionSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        user_transactions = Transaction.objects.filter(user=request.user, status='completed')
        summary = {
            'total_deposits': user_transactions.filter(transaction_type='deposit').aggregate(
                total=models.Sum('amount'))['total'] or Decimal('0.00'),
            'total_withdrawals': user_transactions.filter(transaction_type='withdrawal').aggregate(
                total=models.Sum('amount'))['total'] or Decimal('0.00'),
            'total_transfers_sent': user_transactions.filter(transaction_type='transfer').aggregate(
                total=models.Sum('amount'))['total'] or Decimal('0.00'),
            'transaction_count': user_transactions.count(),
        }
        return Response(summary)

class LookupRecipientView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        account_number = request.GET.get('account_number')
        try:
            account = Account.objects.get(account_number=account_number)
            user = account.user
            return Response({
                'name': f"{user.first_name} {user.last_name}",
                'email': user.email,
                'account_number': account.account_number,
            })
        except Account.DoesNotExist:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)