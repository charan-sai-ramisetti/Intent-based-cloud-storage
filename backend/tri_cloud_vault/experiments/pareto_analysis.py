"""
Multi-Objective Pareto Analysis for Cloud Storage Placement.

Computes non-dominated solutions on the (Cost vs. Latency vs. Durability) frontier
by systematically varying objective trade-off weights in the MILP solver.
"""

from typing import List, Dict, Tuple
from intent.schemas import ParsedConstraints, OptimizationRecommendation
from optimizer.cost_matrix import calculate_monthly_cost, estimate_access_operations
from telemetry.pricing_table import get_pricing_for_cloud


def compute_pareto_frontier(
    file_size_bytes: int = 100 * 1024 * 1024,
    access_pattern: str = "warm",
    expected_monthly_reads: int = 100,
    redundancy_level: int = 2
) -> List[Dict]:
    """
    Exhaustively evaluate all valid placement combinations to compute the empirical Pareto frontier.

    Args:
        file_size_bytes: File size under evaluation
        access_pattern: Data temperature (hot/warm/cold/archival)
        expected_monthly_reads: Expected monthly read count
        redundancy_level: Required number of cloud replicas

    Returns:
        List of Pareto-optimal configurations with cost and latency
    """
    import itertools

    file_size_gb = file_size_bytes / (1024 ** 3)
    monthly_reads, monthly_writes, egress_gb = estimate_access_operations(
        file_size_gb, access_pattern, expected_monthly_reads
    )

    clouds = ["AWS", "AZURE", "GCP"]
    tiers = ["standard", "infrequent", "archive"]

    # Generate all possible (cloud, tier) options
    all_options = []
    for cloud in clouds:
        for tier in tiers:
            pricing = get_pricing_for_cloud(cloud, tier)
            breakdown = calculate_monthly_cost(
                cloud=cloud,
                tier=tier,
                file_size_gb=file_size_gb,
                monthly_reads=monthly_reads,
                monthly_writes=monthly_writes,
                egress_gb=egress_gb
            )
            all_options.append({
                "cloud": cloud,
                "tier": tier,
                "cost": breakdown["total"],
                "latency": pricing["latency_typical_ms"]
            })

    # Generate all combinations of k distinct clouds
    evaluated_combinations = []
    cloud_combos = list(itertools.combinations(clouds, redundancy_level))

    for combo in cloud_combos:
        # For each cloud in the combination, test each tier
        tier_combos = list(itertools.product(tiers, repeat=redundancy_level))
        for t_combo in tier_combos:
            total_cost = 0.0
            total_latency = 0.0
            allocations = {}

            for c, t in zip(combo, t_combo):
                opt = next(o for o in all_options if o["cloud"] == c and o["tier"] == t)
                total_cost += opt["cost"]
                total_latency += opt["latency"]
                allocations[c] = t

            avg_latency = total_latency / redundancy_level

            evaluated_combinations.append({
                "clouds": list(combo),
                "tiers": allocations,
                "cost_usd": round(total_cost, 4),
                "latency_ms": round(avg_latency, 2),
                "redundancy": redundancy_level
            })

    # Identify non-dominated solutions (Pareto Frontier)
    # A point P1 dominates P2 if: Cost(P1) <= Cost(P2) and Latency(P1) <= Latency(P2) and strictly better in at least one
    pareto_frontier = []
    for candidate in evaluated_combinations:
        is_dominated = False
        for other in evaluated_combinations:
            if candidate == other:
                continue
            if (other["cost_usd"] <= candidate["cost_usd"] and
                other["latency_ms"] <= candidate["latency_ms"] and
                (other["cost_usd"] < candidate["cost_usd"] or other["latency_ms"] < candidate["latency_ms"])):
                is_dominated = True
                break

        candidate["is_pareto_optimal"] = not is_dominated
        if not is_dominated:
            pareto_frontier.append(candidate)

    # Sort frontier by cost ascending
    pareto_frontier.sort(key=lambda x: x["cost_usd"])
    return {
        "pareto_points": pareto_frontier,
        "all_evaluated_points": evaluated_combinations,
        "total_combinations": len(evaluated_combinations),
        "pareto_count": len(pareto_frontier)
    }
