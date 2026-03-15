from django.urls import path
from .views import (
    InitiatePaymentView,
    PaymentSuccessView,
    PaymentFailureView,
    PaymentStatusView,
    PaymentListView,
)

urlpatterns = [
    # Core payment flow
    path("initiate/", InitiatePaymentView.as_view(), name="payment-initiate"),
    path("success/", PaymentSuccessView.as_view(), name="payment-success"),
    path("failure/", PaymentFailureView.as_view(), name="payment-failure"),

    # Utility
    path("<int:payment_id>/status/", PaymentStatusView.as_view(), name="payment-status"),
    path("", PaymentListView.as_view(), name="payment-list"),
]
