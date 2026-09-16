"""
URL routing for intent parsing and optimization execution endpoints.
"""

from django.urls import path
from .views import ParseIntentView, ExecuteOptimizedUploadView

urlpatterns = [
    path('parse/', ParseIntentView.as_view(), name='intent-parse'),
    path('execute-upload/', ExecuteOptimizedUploadView.as_view(), name='intent-execute-upload'),
]
