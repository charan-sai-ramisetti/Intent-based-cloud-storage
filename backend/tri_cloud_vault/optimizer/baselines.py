import pandas as pd
import os
import random
from typing import Dict, List, Tuple
from intent.schemas import ParsedConstraints, OptimizationRecommendation
from django.conf import settings
from .cost_matrix import calculate_monthly_cost, estimate_access_operations

# Define clouds and tiers
CLOUDS = ["AWS", "AZURE", "GCP"]
TIERS = ["standard", "infrequent", "archive"]


def build_composite_baseline_recommendation(
    selected_placements: List[Tuple[str, str]],
    file_size_gb: float,
    constraints: ParsedConstraints,
    df: pd.DataFrame,
    reasoning: str
) -> OptimizationRecommendation:
    """Build a composite baseline recommendation across one or more clouds/tiers."""
    monthly_reads, monthly_writes, egress_gb = estimate_access_operations(
        file_size_gb, constraints.access_pattern, constraints.expected_monthly_reads
    )

    selected_clouds = []
    selected_tiers = {}
    cost_breakdown = {}
    total_cost = 0.0
    total_latency = 0.0

    for cloud, tier in selected_placements:
        selected_clouds.append(cloud)
        selected_tiers[cloud] = tier

        breakdown = calculate_monthly_cost(
            cloud=cloud,
            tier=tier,
            file_size_gb=file_size_gb,
            monthly_reads=monthly_reads,
            monthly_writes=monthly_writes,
            egress_gb=egress_gb
        )
        total_cost += breakdown["total"]
        cost_breakdown[f"{cloud}_{tier}"] = round(breakdown["total"], 6)

        matching = df[(df['cloud'] == cloud) & (df['storage_tier'] == tier)]
        if not matching.empty:
            total_latency += float(matching.iloc[0]['latency_ms'])
        else:
            total_latency += 50.0

    k = len(selected_placements)
    avg_latency = (total_latency / k) if k > 0 else 0.0
    durability = (1.0 - (1.0 - 0.99999999999) ** max(1, k)) * 100.0

    return OptimizationRecommendation(
        selected_clouds=selected_clouds,
        selected_tiers=selected_tiers,
        estimated_monthly_cost_usd=round(total_cost, 6),
        estimated_latency_ms=round(avg_latency, 2),
        durability_achieved=round(durability, 9),
        cost_breakdown=cost_breakdown, 
        empirical_performance_enabled=True, 
        empirical_ttfb_statistic="mean", 
        empirical_ttfb_ms=round(avg_latency, 2), 
        empirical_ttfb_available=True, 
        empirical_ttfb_source="baseline_heuristic",
        optimization_time_ms=0.0,
        solver_status="optimal",
        reasoning=reasoning
    )


def get_baseline_recommendation(
    cloud: str,
    tier: str,
    file_size_gb: float,
    constraints: ParsedConstraints,
    row: pd.Series
) -> OptimizationRecommendation:
    """Helper to calculate cost and return recommendation object for a single placement."""
    param_path = settings.BASE_DIR.parent.parent / 'research/data/optimizer/cloud_parameters.csv'
    df = pd.read_csv(param_path)
    return build_composite_baseline_recommendation(
        selected_placements=[(cloud, tier)],
        file_size_gb=file_size_gb,
        constraints=constraints,
        df=df,
        reasoning=f"Baseline: Single {cloud} in {tier} tier."
    )


def run_all_baselines(file_size_bytes: int, constraints: ParsedConstraints) -> Dict[str, OptimizationRecommendation]:
    """
    Generate placement recommendations for baseline algorithms:
    Single Cloud AWS, Round Robin, Lowest Cost Greedy, Random.
    """
    file_size_gb = file_size_bytes / (1024 ** 3)
    k = min(max(1, constraints.redundancy_level), len(CLOUDS))

    param_path = settings.BASE_DIR.parent.parent / 'research/data/optimizer/cloud_parameters.csv'
    df = pd.read_csv(param_path)

    # 1. Baseline: Single Cloud AWS (Standard)
    single_aws_rec = build_composite_baseline_recommendation(
        selected_placements=[("AWS", "standard")],
        file_size_gb=file_size_gb,
        constraints=constraints,
        df=df,
        reasoning="Baseline strategy: AWS S3 Standard (single cloud default)."
    )

    # 2. Baseline: Lowest Cost Greedy
    # For each cloud, find its cheapest allowed tier, then select k cheapest clouds
    monthly_reads, monthly_writes, egress_gb = estimate_access_operations(
        file_size_gb, constraints.access_pattern, constraints.expected_monthly_reads
    )

    allowed_tiers = TIERS.copy()
    if constraints.access_pattern == "hot":
        allowed_tiers = ["standard"]
    elif constraints.access_pattern == "archival":
        allowed_tiers = ["archive", "infrequent"]

    cloud_cheapest = []
    for cloud in CLOUDS:
        best_cost = float('inf')
        best_tier = "standard"
        for tier in allowed_tiers:
            cost = calculate_monthly_cost(
                cloud=cloud,
                tier=tier,
                file_size_gb=file_size_gb,
                monthly_reads=monthly_reads,
                monthly_writes=monthly_writes,
                egress_gb=egress_gb
            )["total"]
            if cost < best_cost:
                best_cost = cost
                best_tier = tier
        cloud_cheapest.append((cloud, best_tier, best_cost))

    cloud_cheapest.sort(key=lambda x: x[2])
    greedy_placements = [(c, t) for c, t, _ in cloud_cheapest[:k]]
    greedy_rec = build_composite_baseline_recommendation(
        selected_placements=greedy_placements,
        file_size_gb=file_size_gb,
        constraints=constraints,
        df=df,
        reasoning=f"Baseline strategy: Greedy cheapest selection across {k} cloud(s)."
    )

    # 3. Baseline: Round Robin
    # Select k distinct clouds in cyclic order using standard tier (or access pattern tier)
    rr_tier = "standard" if constraints.access_pattern != "archival" else "archive"
    rr_placements = [(cloud, rr_tier) for cloud in CLOUDS[:k]]
    rr_rec = build_composite_baseline_recommendation(
        selected_placements=rr_placements,
        file_size_gb=file_size_gb,
        constraints=constraints,
        df=df,
        reasoning=f"Baseline strategy: Round-robin distribution across {k} cloud(s) ({rr_tier} tier)."
    )

    # 4. Baseline: Random Placement
    # Randomly select k distinct clouds and an allowed tier for each
    rnd_clouds = random.sample(CLOUDS, k)
    rnd_placements = [(cloud, random.choice(allowed_tiers)) for cloud in rnd_clouds]
    random_rec = build_composite_baseline_recommendation(
        selected_placements=rnd_placements,
        file_size_gb=file_size_gb,
        constraints=constraints,
        df=df,
        reasoning=f"Baseline strategy: Random selection across {k} cloud(s)."
    )

    return {
        "single_cloud_aws": single_aws_rec,
        "greedy_cheapest": greedy_rec,
        "round_robin": rr_rec,
        "random": random_rec
    }


