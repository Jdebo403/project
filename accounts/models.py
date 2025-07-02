from django.db import models
from django.conf import settings
from decimal import Decimal
import random

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('savings', 'Savings'),
        ('checking', 'Checking'),
        ('business', 'Business'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('frozen', 'Frozen'),
        ('closed', 'Closed'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='accounts')
    account_number = models.CharField(max_length=20, unique=True, blank=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='savings')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.account_number} - {self.user.full_name}"
    
    @property
    def is_active(self):
        return self.status == 'active'
    
    def can_debit(self, amount):
        """Check if account can be debited with the given amount"""
        return self.is_active and self.balance >= amount
    
    def can_credit(self, amount):
        """Check if account can be credited with the given amount"""
        return self.is_active and amount > 0
    
    def save(self, *args, **kwargs):
        if not self.account_number:
            while True:
                number = str(random.randint(10**9, 10**10 - 1))  # 10 digits
                if not Account.objects.filter(account_number=number).exists():
                    self.account_number = number
                    break
        super().save(*args, **kwargs)