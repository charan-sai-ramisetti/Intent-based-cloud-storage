"""
URL routing for optimizer endpoints.
"""

from django.urls import path
from .views import CompareBaselinesView

urlpatterns = [
    path('compare-baselines/', CompareBaselinesView.as_view(), name='optimizer-compare-baselines'),
]
