from django.urls import path
from . import views

urlpatterns = [
    path('', views.TransactionListView.as_view(), name='transaction-list'),
    path('<int:pk>/', views.TransactionDetailView.as_view(), name='transaction-detail'),
    path('deposit/', views.DepositView.as_view(), name='deposit'),
    path('withdraw/', views.WithdrawView.as_view(), name='withdraw'),
    path('transfer/', views.TransferView.as_view(), name='transfer'),
    path('external-transfer/', views.ExternalTransferView.as_view(), name='external-transfer'),
    path('summary/', views.TransactionSummaryView.as_view(), name='transaction-summary'),
    path('lookup/', views.LookupRecipientView.as_view(), name='lookup-recipient'),
]