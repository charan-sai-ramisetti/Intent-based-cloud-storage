import pandas as pd
import os
from intent.schemas import ParsedConstraints, OptimizationRecommendation

# Define clouds and tiers
CLOUDS = ["AWS", "AZURE", "GCP"]
TIERS = ["standard", "infrequent", "archive"]

def get_baseline_recommendation(
    cloud: str,
    tier: str,
    file_size_gb: float,
    constraints: ParsedConstraints,
    row: pd.Series
) -> OptimizationRecommendation:
    """Helper to calculate cost and return recommendation object."""
    from .cost_matrix import calculate_monthly_cost, estimate_access_operations

    monthly_reads, monthly_writes, egress_gb = estimate_access_operations(
        file_size_gb, constraints.access_pattern, constraints.expected_monthly_reads
    )

    cost_breakdown = calculate_monthly_cost(
        cloud=cloud,
        tier=tier,
        file_size_gb=file_size_gb,
        monthly_reads=monthly_reads,
        monthly_writes=monthly_writes,
        egress_gb=egress_gb
    )

    return OptimizationRecommendation(
        selected_clouds=[cloud],
        selected_tiers={cloud: tier},
        estimated_monthly_cost_usd=round(cost_breakdown["total"], 4),
        estimated_latency_ms=row['latency_ms'],
        durability_achieved=99.999999999,
        cost_breakdown={f"{cloud}_{tier}": round(cost_breakdown["total"], 4)},
        optimization_time_ms=0.0,
        solver_status="optimal",
        reasoning=f"Baseline: Single {cloud} in {tier} tier."
    )

def run_all_baselines(file_size_bytes: int, constraints: ParsedConstraints) -> dict[str, OptimizationRecommendation]:
    """
    Generate placement recommendations for baseline algorithms:
    Single Cloud AWS, Round Robin, Lowest Cost Greedy.
    """
    file_size_gb = file_size_bytes / (1024 ** 3)

    # Load parameters
    param_path = os.path.join(os.path.dirname(__file__), '..', '..', 'research/data/optimizer/cloud_parameters.csv')
    df = pd.read_csv(param_path)

    # Baseline 1: Single Cloud AWS (Standard)
    aws_std = df[(df['cloud'] == 'AWS') & (df['storage_tier'] == 'standard')].iloc[0]
    single_aws_rec = get_baseline_recommendation("AWS", "standard", file_size_gb, constraints, aws_std)

    # Baseline 2: Lowest Cost Greedy (simplification for now: take cheapest based on storage cost)
    cheapest = df.nsmallest(1, 'storage_cost_usd_gb_month').iloc[0]
    greedy_rec = get_baseline_recommendation(cheapest['cloud'], cheapest['storage_tier'], file_size_gb, constraints, cheapest)

    # Baseline 3: Round Robin (simplified: just use standard/cheapest available)
    # The original implementation was just returning total costs, but now we need full objects.
    # We will pick the first one and call it RR.
    rr = df[df['storage_tier'] == 'standard'].iloc[0]
    rr_rec = get_baseline_recommendation(rr['cloud'], rr['storage_tier'], file_size_gb, constraints, rr)

    return {
        "single_aws": single_aws_rec,
        "greedy_cheapest": greedy_rec,
        "round_robin": rr_rec
    }
