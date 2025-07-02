from django.db import models
from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer', 'Transfer'),
        ('external', 'External Transfer'),  # Added external transfer type
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    from_account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='sent_transactions', null=True, blank=True)
    to_account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='received_transactions', null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    description = models.TextField(blank=True)
    reference_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    bank_name = models.CharField(max_length=100, blank=True, null=True)  # Added for external transfers
    beneficiary_name = models.CharField(max_length=100, blank=True, null=True)
    routing_number = models.CharField(max_length=50, blank=True, null=True)
    beneficiary_address = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_type.title()} - ${self.amount} - {self.reference_number}"
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def can_be_cancelled(self):
        return self.status == 'pending'