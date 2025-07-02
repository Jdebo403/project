from django.contrib import admin
from .models import Transaction
import uuid

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'reference_number', 'user', 'transaction_type', 'amount', 'status',
        'bank_name', 'beneficiary_name', 'routing_number', 'beneficiary_address', 'created_at'
    ]
    list_filter = [
        'transaction_type', 'status', 'created_at', 'bank_name', 'beneficiary_name', 'created_at', 'updated_at'
    ]
    search_fields = [
        'reference_number', 'user__email', 'description', 'bank_name', 'beneficiary_name', 'routing_number', 'beneficiary_address'
    ]
    readonly_fields = ['reference_number',]
    ordering = ['-created_at']
    actions = ['approve_external_transfers', 'reject_external_transfers']

    fieldsets = (
        (None, {
            'fields': ('user', 'reference_number', 'transaction_type')
        }),
        ('Accounts', {
            'fields': ('from_account', 'to_account')
        }),
        ('Transaction Details', {
            'fields': ('amount', 'description', 'status', 'bank_name', 'beneficiary_name', 'routing_number', 'beneficiary_address')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def approve_external_transfers(self, request, queryset):
        for transaction in queryset.filter(transaction_type='external', status='pending'):
            # Move funds here if needed
            from_account = transaction.from_account
            if from_account and from_account.can_debit(transaction.amount):
                from_account.balance -= transaction.amount
                from_account.save()
                transaction.status = 'completed'
                transaction.save()
        self.message_user(request, "Selected external transfers have been approved and processed.")
    approve_external_transfers.short_description = "Approve selected pending external transfers"

    def reject_external_transfers(self, request, queryset):
        for transaction in queryset.filter(transaction_type='external', status='pending'):
            from_account = transaction.from_account
            if from_account:
                # Refund the amount if not already refunded
                from_account.balance += transaction.amount
                from_account.save()
            transaction.status = 'cancelled'
            transaction.save()
        self.message_user(request, "Selected external transfers have been rejected and refunded.")
    reject_external_transfers.short_description = "Reject selected pending external transfers and refund sender"

    def save_model(self, request, obj, form, change):
        if not obj.reference_number:
            prefix = {
                'deposit': 'DEP',
                'withdrawal': 'WTD',
                'transfer': 'TRF',
                'external': 'EXT'
            }.get(obj.transaction_type, 'TRX')
            obj.reference_number = f"{prefix}{uuid.uuid4().hex[:8].upper()}"
        super().save_model(request, obj, form, change)
        # Update account balances for deposit
        if obj.transaction_type == 'deposit' and obj.to_account and obj.status == 'completed':
            account = obj.to_account
            account.balance += obj.amount
            account.save()
        # Update account balances for withdrawal
        if obj.transaction_type == 'withdrawal' and obj.from_account and obj.status == 'completed':
            account = obj.from_account
            account.balance -= obj.amount
            account.save()