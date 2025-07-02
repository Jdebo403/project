from django.urls import path
from . import views

urlpatterns = [
    path('', views.AccountListView.as_view(), name='account-list'),
    path('<int:pk>/', views.AccountDetailView.as_view(), name='account-detail'),
    path('<int:account_id>/balance/', views.account_balance, name='account-balance'),
    path('my-accounts/', views.user_accounts, name='user-accounts'),
]