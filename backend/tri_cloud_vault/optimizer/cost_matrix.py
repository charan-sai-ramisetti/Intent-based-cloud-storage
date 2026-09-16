"""
Cost calculation matrix for multi-cloud storage optimization.

This module computes monthly storage costs given file characteristics,
access patterns, and cloud provider pricing.
"""

from typing import Dict, Tuple
from telemetry.pricing_table import get_pricing_for_cloud


def calculate_monthly_cost(
    cloud: str,
    tier: str,
    file_size_gb: float,
    monthly_reads: int = 0,
    monthly_writes: int = 0,
    egress_gb: float = 0.0
) -> Dict[str, float]:
    """
    Calculate total monthly cost for storing a file in a specific cloud and tier.

    Args:
        cloud: "AWS", "AZURE", or "GCP"
        tier: "standard", "infrequent", or "archive"
        file_size_gb: File size in gigabytes
        monthly_reads: Number of GET requests per month
        monthly_writes: Number of PUT requests per month
        egress_gb: Expected egress (data transfer out) in GB per month

    Returns:
        Dictionary with cost breakdown:
        {
            "storage": float,
            "operations": float,
            "egress": float,
            "total": float
        }
    """
    pricing = get_pricing_for_cloud(cloud, tier)

    # Storage cost
    storage_cost = file_size_gb * pricing["storage_per_gb_month"]

    # Operations cost
    read_cost = (monthly_reads / 10000) * pricing["get_per_10k"]
    write_cost = (monthly_writes / 10000) * pricing["put_per_10k"]
    operations_cost = read_cost + write_cost

    # Egress cost
    egress_cost = egress_gb * pricing["egress_per_gb"]

    total_cost = storage_cost + operations_cost + egress_cost

    return {
        "storage": storage_cost,
        "operations": operations_cost,
        "egress": egress_cost,
        "total": total_cost
    }


def estimate_access_operations(
    file_size_gb: float,
    access_pattern: str,
    expected_monthly_reads: int = None
) -> Tuple[int, int, float]:
    """
    Estimate monthly read/write operations and egress based on access pattern.

    Args:
        file_size_gb: File size in GB
        access_pattern: "hot", "warm", "cold", or "archival"
        expected_monthly_reads: Optional explicit read count

    Returns:
        (monthly_reads, monthly_writes, egress_gb)
    """
    if expected_monthly_reads is not None:
        monthly_reads = expected_monthly_reads
    else:
        # Heuristic estimates based on access pattern
        pattern_reads = {
            "hot": 1000,      # Multiple times daily
            "warm": 100,      # Weekly access
            "cold": 10,       # Monthly access
            "archival": 1     # Rare access
        }
        monthly_reads = pattern_reads.get(access_pattern, 100)

    # Writes are typically much less frequent (1-10% of reads)
    monthly_writes = max(1, int(monthly_reads * 0.05))

    # Egress estimate: assume 10% of reads actually transfer the full file
    egress_gb = (monthly_reads * 0.1) * file_size_gb

    return monthly_reads, monthly_writes, egress_gb


def build_cost_matrix(
    file_size_bytes: int,
    access_pattern: str,
    expected_monthly_reads: int = None
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Build complete cost matrix for all cloud/tier combinations.

    Args:
        file_size_bytes: File size in bytes
        access_pattern: Access frequency pattern
        expected_monthly_reads: Optional explicit read count

    Returns:
        Nested dict: {cloud: {tier: {cost_breakdown}}}
    """
    file_size_gb = file_size_bytes / (1024 ** 3)

    monthly_reads, monthly_writes, egress_gb = estimate_access_operations(
        file_size_gb, access_pattern, expected_monthly_reads
    )

    clouds = ["AWS", "AZURE", "GCP"]
    tiers = ["standard", "infrequent", "archive"]

    matrix = {}

    for cloud in clouds:
        matrix[cloud] = {}
        for tier in tiers:
            try:
                cost = calculate_monthly_cost(
                    cloud=cloud,
                    tier=tier,
                    file_size_gb=file_size_gb,
                    monthly_reads=monthly_reads,
                    monthly_writes=monthly_writes,
                    egress_gb=egress_gb
                )
                matrix[cloud][tier] = cost
            except Exception as e:
                # If pricing not available, set to infinity
                matrix[cloud][tier] = {
                    "storage": float('inf'),
                    "operations": float('inf'),
                    "egress": float('inf'),
                    "total": float('inf')
                }

    return matrix
