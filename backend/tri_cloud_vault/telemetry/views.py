"""
API views for telemetry data (pricing, latency probes).
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from telemetry.pricing_table import DEFAULT_PRICING_TABLE

logger = logging.getLogger(__name__)


class PricingTableView(APIView):
    """
    Get the current cloud pricing table.

    GET /api/telemetry/pricing/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "pricing_table": DEFAULT_PRICING_TABLE,
            "metadata": {
                "last_updated": "2026-09-15",
                "currency": "USD",
                "note": "Pricing data based on published cloud provider rates for India region"
            }
        }, status=status.HTTP_200_OK)
