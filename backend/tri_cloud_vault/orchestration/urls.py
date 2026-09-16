"""
URL routing for orchestration endpoints.
"""

from django.urls import path
from .views import FSMStatusView, TaskStatusView

urlpatterns = [
    path('fsm-status/<str:operation_id>/', FSMStatusView.as_view(), name='orchestration-fsm-status'),
    path('task-status/<str:task_id>/', TaskStatusView.as_view(), name='orchestration-task-status'),
]
