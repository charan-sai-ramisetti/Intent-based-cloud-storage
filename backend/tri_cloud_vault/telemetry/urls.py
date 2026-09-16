"""
URL routing for telemetry endpoints.
"""

from django.urls import path
from .views import PricingTableView

urlpatterns = [
    path('pricing/', PricingTableView.as_view(), name='telemetry-pricing'),
]
