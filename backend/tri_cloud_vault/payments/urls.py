from django.urls import path
from .views import (
    SubscriptionStatusView,
    CreateOrderView,
    VerifyPaymentView,
    RazorpayWebhookView
)

urlpatterns = [
    path("subscription/status/", SubscriptionStatusView.as_view()),
    path("create-order/", CreateOrderView.as_view()),
    path("verify/", VerifyPaymentView.as_view()),
    path("webhook/", RazorpayWebhookView.as_view()),
]
