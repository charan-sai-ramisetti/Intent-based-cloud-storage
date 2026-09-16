"""
Baseline heuristic solvers for empirical comparison against MILP optimization.

These baselines represent common cloud placement strategies that do NOT use
mathematical optimization. They serve as control groups in research experiments.
"""

from typing import List, Dict
from intent.schemas import ParsedConstraints, OptimizationRecommendation
from telemetry.pricing_table import get_pricing_for_cloud
from optimizer.cost_matrix import calculate_monthly_cost, estimate_access_operations


def baseline_single_cloud_aws(
    file_size_bytes: int,
    constraints: ParsedConstraints
) -> OptimizationRecommendation:
    """
    Baseline 1: Always use AWS S3 Standard (single cloud default).

    Represents the simplest strategy: pick one cloud provider and stick with it.
    """
    file_size_gb = file_size_bytes / (1024 ** 3)
    monthly_reads, monthly_writes, egress_gb = estimate_access_operations(
        file_size_gb, constraints.access_pattern, constraints.expected_monthly_reads
    )

    pricing = get_pricing_for_cloud("AWS", "standard")
    cost_breakdown_dict = calculate_monthly_cost(
        cloud="AWS",
        tier="standard",
        file_size_gb=file_size_gb,
        monthly_reads=monthly_reads,
        monthly_writes=monthly_writes,
        egress_gb=egress_gb
    )

    return OptimizationRecommendation(
        selected_clouds=["AWS"],
        selected_tiers={"AWS": "standard"},
        estimated_monthly_cost_usd=cost_breakdown_dict["total"],
        estimated_latency_ms=pricing["latency_typical_ms"],
        durability_achieved=99.999999999,
        cost_breakdown={"AWS_standard": cost_breakdown_dict["total"]},
        optimization_time_ms=0.0,
        solver_status="optimal",
        reasoning="Baseline strategy: AWS S3 Standard (single cloud default)."
    )


def baseline_greedy_cheapest(
    file_size_bytes: int,
    constraints: ParsedConstraints
) -> OptimizationRecommendation:
    """
    Baseline 2: Greedy selection of the single cheapest (cloud, tier) combination.

    Minimizes cost without considering redundancy, latency, or other constraints.
    """
    file_size_gb = file_size_bytes / (1024 ** 3)
    monthly_reads, monthly_writes, egress_gb = estimate_access_operations(
        file_size_gb, constraints.access_pattern, constraints.expected_monthly_reads
    )

    clouds = ["AWS", "AZURE", "GCP"]
    tiers = ["standard", "infrequent", "archive"]

    min_cost = float('inf')
    best_cloud = None
    best_tier = None
    best_pricing = None
    best_breakdown = None

    for cloud in clouds:
        for tier in tiers:
            try:
                pricing = get_pricing_for_cloud(cloud, tier)
                breakdown = calculate_monthly_cost(
                    cloud=cloud,
                    tier=tier,
                    file_size_gb=file_size_gb,
                    monthly_reads=monthly_reads,
                    monthly_writes=monthly_writes,
                    egress_gb=egress_gb
                )

                if breakdown["total"] < min_cost:
                    min_cost = breakdown["total"]
                    best_cloud = cloud
                    best_tier = tier
                    best_pricing = pricing
                    best_breakdown = breakdown
            except:
                continue

    return OptimizationRecommendation(
        selected_clouds=[best_cloud],
        selected_tiers={best_cloud: best_tier},
        estimated_monthly_cost_usd=best_breakdown["total"],
        estimated_latency_ms=best_pricing["latency_typical_ms"],
        durability_achieved=99.999999999,
        cost_breakdown={f"{best_cloud}_{best_tier}": best_breakdown["total"]},
        optimization_time_ms=0.0,
        solver_status="optimal",
        reasoning=f"Baseline strategy: Greedy cheapest selection ({best_cloud} {best_tier})."
    )


def baseline_round_robin(
    file_size_bytes: int,
    constraints: ParsedConstraints
) -> OptimizationRecommendation:
    """
    Baseline 3: Round-robin distribution across all three clouds using standard tier.

    Provides redundancy but ignores cost optimization and tier selection.
    """
    file_size_gb = file_size_bytes / (1024 ** 3)
    monthly_reads, monthly_writes, egress_gb = estimate_access_operations(
        file_size_gb, constraints.access_pattern, constraints.expected_monthly_reads
    )

    clouds = ["AWS", "AZURE", "GCP"]
    total_cost = 0.0
    total_latency = 0.0
    cost_breakdown = {}

    for cloud in clouds:
        pricing = get_pricing_for_cloud(cloud, "standard")
        breakdown = calculate_monthly_cost(
            cloud=cloud,
            tier="standard",
            file_size_gb=file_size_gb,
            monthly_reads=monthly_reads,
            monthly_writes=monthly_writes,
            egress_gb=egress_gb
        )

        cost_breakdown[f"{cloud}_standard"] = breakdown["total"]
        total_cost += breakdown["total"]
        total_latency += pricing["latency_typical_ms"]

    avg_latency = total_latency / len(clouds)
    durability = (1 - (1 - 0.99999999999) ** 3) * 100

    return OptimizationRecommendation(
        selected_clouds=clouds,
        selected_tiers={cloud: "standard" for cloud in clouds},
        estimated_monthly_cost_usd=total_cost,
        estimated_latency_ms=avg_latency,
        durability_achieved=durability,
        cost_breakdown=cost_breakdown,
        optimization_time_ms=0.0,
        solver_status="optimal",
        reasoning="Baseline strategy: Round-robin across all 3 clouds (standard tier)."
    )


def baseline_random(
    file_size_bytes: int,
    constraints: ParsedConstraints,
    seed: int = 42
) -> OptimizationRecommendation:
    """
    Baseline 4: Random selection of cloud and tier.

    Control baseline for statistical significance testing.
    """
    import random
    random.seed(seed)

    clouds = ["AWS", "AZURE", "GCP"]
    tiers = ["standard", "infrequent", "archive"]

    selected_cloud = random.choice(clouds)
    selected_tier = random.choice(tiers)

    file_size_gb = file_size_bytes / (1024 ** 3)
    monthly_reads, monthly_writes, egress_gb = estimate_access_operations(
        file_size_gb, constraints.access_pattern, constraints.expected_monthly_reads
    )

    pricing = get_pricing_for_cloud(selected_cloud, selected_tier)
    breakdown = calculate_monthly_cost(
        cloud=selected_cloud,
        tier=selected_tier,
        file_size_gb=file_size_gb,
        monthly_reads=monthly_reads,
        monthly_writes=monthly_writes,
        egress_gb=egress_gb
    )

    return OptimizationRecommendation(
        selected_clouds=[selected_cloud],
        selected_tiers={selected_cloud: selected_tier},
        estimated_monthly_cost_usd=breakdown["total"],
        estimated_latency_ms=pricing["latency_typical_ms"],
        durability_achieved=99.999999999,
        cost_breakdown={f"{selected_cloud}_{selected_tier}": breakdown["total"]},
        optimization_time_ms=0.0,
        solver_status="optimal",
        reasoning=f"Baseline strategy: Random selection ({selected_cloud} {selected_tier})."
    )


def run_all_baselines(
    file_size_bytes: int,
    constraints: ParsedConstraints
) -> Dict[str, OptimizationRecommendation]:
    """
    Run all baseline strategies and return results for comparison.

    Returns:
        Dict mapping baseline name to its recommendation.
    """
    return {
        "single_cloud_aws": baseline_single_cloud_aws(file_size_bytes, constraints),
        "greedy_cheapest": baseline_greedy_cheapest(file_size_bytes, constraints),
        "round_robin": baseline_round_robin(file_size_bytes, constraints),
        "random": baseline_random(file_size_bytes, constraints),
    }
