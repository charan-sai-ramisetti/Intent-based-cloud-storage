"""
API views for intent parsing, optimization preview, and execution.
"""

import time
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .schemas import StorageIntentInput
from .llm_parser import parse_storage_intent
from .models import IntentLog
from optimizer.milp_solver import solve_optimal_placement
from optimizer.baselines import run_all_baselines
from orchestration.tasks import prepare_multicloud_upload_task

logger = logging.getLogger(__name__)


class ParseIntentView(APIView):
    """
    Parse natural language intent into structured constraints and return
    the MILP optimal placement recommendation with cost preview.

    POST /api/intent/parse/
    Body:
    {
        "user_text": "Store my critical database backup with 2 copies under $5/mo",
        "file_size_bytes": 104857600,
        "file_type": "application/sql"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_text = request.data.get("user_text")
        file_size_bytes = request.data.get("file_size_bytes")
        file_type = request.data.get("file_type")

        if not user_text:
            return Response(
                {"error": "user_text is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not file_size_bytes or int(file_size_bytes) <= 0:
            return Response(
                {"error": "file_size_bytes must be a positive integer"},
                status=status.HTTP_400_BAD_REQUEST
            )

        file_size_bytes = int(file_size_bytes)

        try:
            # 1. Step 1: LLM extracts constraints (never selects clouds)
            intent_input = StorageIntentInput(
                user_text=user_text,
                file_size_bytes=file_size_bytes,
                file_type=file_type
            )
            parse_result = parse_storage_intent(intent_input)

            # 2. Step 2: MILP solver computes optimal placement
            opt_start = time.perf_counter()
            recommendation = solve_optimal_placement(
                file_size_bytes=file_size_bytes,
                constraints=parse_result.parsed_constraints
            )
            opt_latency_ms = (time.perf_counter() - opt_start) * 1000
            parse_result.recommendation = recommendation

            # 3. Step 3: Run baselines for comparison
            baselines = run_all_baselines(
                file_size_bytes=file_size_bytes,
                constraints=parse_result.parsed_constraints
            )

            # 4. Step 4: Persist IntentLog for research telemetry
            intent_log = IntentLog.objects.create(
                user=request.user,
                original_text=user_text,
                file_name=request.data.get("file_name", "unnamed_file"),
                file_size_bytes=file_size_bytes,
                parsed_constraints=parse_result.parsed_constraints.model_dump(),
                recommendation=recommendation.model_dump(),
                llm_provider=parse_result.llm_provider,
                llm_model=parse_result.llm_model or "",
                parse_latency_ms=parse_result.parse_latency_ms,
                optimization_latency_ms=opt_latency_ms,
                confidence_score=parse_result.confidence_score
            )

            # Format response
            return Response({
                "intent_log_id": intent_log.id,
                "parsed_constraints": parse_result.parsed_constraints.model_dump(),
                "recommendation": recommendation.model_dump(),
                "baselines_comparison": {
                    name: rec.model_dump() for name, rec in baselines.items()
                },
                "meta": {
                    "llm_provider": parse_result.llm_provider,
                    "llm_model": parse_result.llm_model,
                    "parse_latency_ms": round(parse_result.parse_latency_ms, 2),
                    "optimization_latency_ms": round(opt_latency_ms, 2),
                    "confidence_score": parse_result.confidence_score
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Intent parse view error: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to process intent: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExecuteOptimizedUploadView(APIView):
    """
    Execute the optimal placement policy by triggering Celery FSM orchestration
    and returning presigned upload endpoints.

    POST /api/intent/execute-upload/
    Body:
    {
        "intent_log_id": 12,
        "file_name": "backup.sql",
        "file_size_bytes": 104857600,
        "file_type": "application/sql"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        intent_log_id = request.data.get("intent_log_id")
        file_name = request.data.get("file_name")
        file_size_bytes = request.data.get("file_size_bytes")
        file_type = request.data.get("file_type", "application/octet-stream")

        if not intent_log_id or not file_name or not file_size_bytes:
            return Response(
                {"error": "intent_log_id, file_name, and file_size_bytes are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            intent_log = IntentLog.objects.get(id=intent_log_id, user=request.user)
            rec = intent_log.recommendation

            if not rec or not rec.get("selected_clouds"):
                return Response(
                    {"error": "No valid optimization recommendation found for this intent"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            selected_clouds = rec["selected_clouds"]
            selected_tiers = rec["selected_tiers"]

            # Trigger Celery asynchronous FSM orchestration
            task = prepare_multicloud_upload_task.delay(
                user_id=request.user.id,
                file_name=file_name,
                file_size_bytes=int(file_size_bytes),
                file_type=file_type,
                selected_clouds=selected_clouds,
                selected_tiers=selected_tiers
            )

            return Response({
                "message": "Optimization execution started",
                "task_id": task.id,
                "selected_clouds": selected_clouds,
                "selected_tiers": selected_tiers,
                "estimated_monthly_cost_usd": rec["estimated_monthly_cost_usd"],
                "reasoning": rec["reasoning"]
            }, status=status.HTTP_202_ACCEPTED)

        except IntentLog.DoesNotExist:
            return Response(
                {"error": "Intent log not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Execute upload error: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to execute upload: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
