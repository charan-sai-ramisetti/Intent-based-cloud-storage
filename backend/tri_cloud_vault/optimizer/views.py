"""
API views for optimization and baseline comparison.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from intent.schemas import ParsedConstraints
from optimizer.milp_solver import solve_optimal_placement
from optimizer.baselines import run_all_baselines

logger = logging.getLogger(__name__)


class CompareBaselinesView(APIView):
    """
    Compare MILP optimization against all baseline heuristics.

    POST /api/optimizer/compare-baselines/
    Body:
    {
        "file_size_bytes": 104857600,
        "constraints": {
            "redundancy_level": 2,
            "max_budget_monthly_usd": 5.0,
            "primary_goal": "COST_MINIMIZATION",
            "access_pattern": "warm"
        }
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_size_bytes = request.data.get("file_size_bytes")
        constraints_data = request.data.get("constraints")

        if not file_size_bytes or not constraints_data:
            return Response(
                {"error": "file_size_bytes and constraints are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            file_size_bytes = int(file_size_bytes)
            constraints = ParsedConstraints(**constraints_data)

            # Run MILP optimization
            milp_result = solve_optimal_placement(
                file_size_bytes=file_size_bytes,
                constraints=constraints
            )

            # Run all baseline heuristics
            baselines = run_all_baselines(
                file_size_bytes=file_size_bytes,
                constraints=constraints
            )

            # Calculate cost savings
            cost_savings = {}
            for baseline_name, baseline_rec in baselines.items():
                if baseline_rec.estimated_monthly_cost_usd > 0:
                    savings_pct = (
                        (baseline_rec.estimated_monthly_cost_usd - milp_result.estimated_monthly_cost_usd) /
                        baseline_rec.estimated_monthly_cost_usd * 100
                    )
                    cost_savings[baseline_name] = round(savings_pct, 2)

            return Response({
                "milp_optimal": milp_result.model_dump(),
                "baselines": {
                    name: rec.model_dump() for name, rec in baselines.items()
                },
                "cost_savings_percent": cost_savings,
                "analysis": {
                    "milp_cost": milp_result.estimated_monthly_cost_usd,
                    "milp_latency": milp_result.estimated_latency_ms,
                    "cheapest_baseline": min(
                        baselines.items(),
                        key=lambda x: x[1].estimated_monthly_cost_usd
                    )[0],
                    "fastest_baseline": min(
                        baselines.items(),
                        key=lambda x: x[1].estimated_latency_ms
                    )[0]
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Baseline comparison error: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to compare baselines: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
