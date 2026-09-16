"""
API views for FSM orchestration status and control.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from celery.result import AsyncResult

from .fsm import StorageFSM, StorageFSMState

logger = logging.getLogger(__name__)


class FSMStatusView(APIView):
    """
    Get the current state and transition history of an orchestration FSM.

    GET /api/orchestration/fsm-status/<operation_id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, operation_id):
        cache_key = f"fsm:{operation_id}"
        fsm_data = cache.get(cache_key)

        if not fsm_data:
            return Response(
                {"error": f"No active FSM found for operation_id: {operation_id}"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(fsm_data, status=status.HTTP_200_OK)


class TaskStatusView(APIView):
    """
    Get the status of a Celery async task.

    GET /api/orchestration/task-status/<task_id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        res = AsyncResult(task_id)
        response_data = {
            "task_id": task_id,
            "status": res.status,
            "ready": res.ready(),
            "successful": res.successful() if res.ready() else False,
        }

        if res.ready():
            if res.successful():
                response_data["result"] = res.result
            else:
                response_data["error"] = str(res.result)

        return Response(response_data, status=status.HTTP_200_OK)
