"""
Mixed-Integer Linear Programming (MILP) solver for optimal multi-cloud storage placement.

This module formulates and solves the cloud selection problem as an optimization model:
- Decision variables: binary placement indicators for each (cloud, tier) combination
- Objective: minimize total monthly cost OR minimize latency (based on primary goal)
- Constraints: redundancy, budget, latency SLA, durability, compliance

Critical architectural principle: The LLM never makes cloud decisions. This MILP solver
is the ONLY component that decides which clouds and tiers to use.
"""

import os
import pandas as pd
import time
import logging
from typing import Dict, List, Tuple, Optional
from pulp import LpProblem, LpMinimize, LpVariable, LpBinary, lpSum, PULP_CBC_CMD, LpStatus

from backend.tri_cloud_vault.intent.schemas import ParsedConstraints, OptimizationRecommendation
from backend.tri_cloud_vault.optimizer.cost_matrix import estimate_access_operations

logger = logging.getLogger(__name__)


def solve_optimal_placement(
    file_size_bytes: int,
    constraints: ParsedConstraints
) -> OptimizationRecommendation:
    """
    Solve the multi-cloud storage placement optimization problem using MILP.

    Args:
        file_size_bytes: Size of file to store
        constraints: Validated user constraints from intent parser

    Returns:
        OptimizationRecommendation with selected clouds, costs, and reasoning
    """
    start_time = time.perf_counter()

    file_size_gb = file_size_bytes / (1024 ** 3)

    # Estimate operations based on access pattern
    monthly_reads, monthly_writes, egress_gb = estimate_access_operations(
        file_size_gb,
        constraints.access_pattern,
        constraints.expected_monthly_reads
    )

    # Define clouds and tiers
    clouds = ["AWS", "AZURE", "GCP"]
    tiers = ["standard", "infrequent", "archive"]

    # Filter tiers based on access pattern
    if constraints.access_pattern == "hot":
        # Hot data should only use standard tier
        tiers = ["standard"]
    elif constraints.access_pattern == "archival":
        # Archival can use any tier but prefers archive
        pass  # Keep all tiers

    # Apply geographic restrictions
    available_clouds = clouds
    if constraints.geo_restriction:
        # Map regions to clouds
        region_to_cloud = {
            "ap-south-1": "AWS",
            "centralindia": "AZURE",
            "asia-south1": "GCP"
        }
        allowed_clouds = set()
        for region in constraints.geo_restriction:
            if region in region_to_cloud:
                allowed_clouds.add(region_to_cloud[region])
        if allowed_clouds:
            available_clouds = [c for c in clouds if c in allowed_clouds]

    # Load parameters from generated CSV
    param_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'research/data/optimizer/cloud_parameters.csv')
    param_df = pd.read_csv(param_path)

    # Pre-calculate costs and latencies for all combinations
    costs = {}
    latencies = {}

    for _, row in param_df.iterrows():
        cloud = row['cloud']
        tier = row['storage_tier']

        # Ensure cloud is in available_clouds
        if cloud not in available_clouds:
            continue

        # Calculate total monthly cost
        monthly_reads, monthly_writes, egress_gb = estimate_access_operations(
            file_size_gb,
            constraints.access_pattern,
            constraints.expected_monthly_reads
        )

        cost_breakdown = {
            "storage": file_size_gb * row['storage_cost_usd_gb_month'],
            "operations": (monthly_reads / 10000 * row['get_cost_usd_10k']) + (monthly_writes / 10000 * row['put_cost_usd_10k']),
            "egress": egress_gb * row['egress_cost_usd_gb']
        }
        cost_breakdown["total"] = sum(cost_breakdown.values())

        costs[(cloud, tier)] = cost_breakdown["total"]
        latencies[(cloud, tier)] = row['latency_ms']

    if not costs:
        raise ValueError("No valid cloud/tier combinations available")

    # Create the optimization problem
    prob = LpProblem("MultiCloudStoragePlacement", LpMinimize)

    # Decision variables: x[cloud, tier] = 1 if we store in that (cloud, tier), 0 otherwise
    x = {}
    for cloud in available_clouds:
        for tier in tiers:
            if (cloud, tier) in costs:
                x[(cloud, tier)] = LpVariable(f"x_{cloud}_{tier}", cat=LpBinary)

    # Objective function based on primary goal
    if constraints.primary_goal == "COST_MINIMIZATION":
        # Minimize total cost
        prob += lpSum([costs[ct] * x[ct] for ct in x]), "TotalCost"
    elif constraints.primary_goal == "LATENCY_MINIMIZATION":
        # Minimize average latency (weighted by selection)
        prob += lpSum([latencies[ct] * x[ct] for ct in x]), "AverageLatency"
    elif constraints.primary_goal == "MAX_REDUNDANCY":
        # Maximize redundancy (minimize negative count)
        prob += -lpSum([x[ct] for ct in x]), "MaxRedundancy"
    else:  # BALANCED
        # Multi-objective: normalized cost + normalized latency
        max_cost = max(costs.values())
        max_latency = max(latencies.values())
        prob += lpSum([
            (costs[ct] / max_cost + latencies[ct] / max_latency) * x[ct]
            for ct in x
        ]), "BalancedObjective"

    # Constraint 1: Redundancy requirement (minimum number of replicas)
    prob += lpSum([x[ct] for ct in x]) >= constraints.redundancy_level, "MinRedundancy"

    # Constraint 2: Budget constraint (if specified)
    if constraints.max_budget_monthly_usd is not None:
        prob += lpSum([costs[ct] * x[ct] for ct in x]) <= constraints.max_budget_monthly_usd, "BudgetLimit"

    # Constraint 3: Latency constraint (if specified)
    if constraints.max_latency_ms is not None:
        # Average latency of selected clouds must be below threshold
        # This is: sum(latency * x) / sum(x) <= max_latency
        # Reformulated: sum(latency * x) <= max_latency * sum(x)
        prob += (
            lpSum([latencies[ct] * x[ct] for ct in x]) <=
            constraints.max_latency_ms * lpSum([x[ct] for ct in x])
        ), "LatencySLA"

    # Constraint 4: Archive tier restrictions for hot data
    if constraints.access_pattern == "hot":
        # Hot data should not use archive tier
        for cloud in available_clouds:
            if (cloud, "archive") in x:
                prob += x[(cloud, "archive")] == 0, f"NoArchive_{cloud}"

    # Solve the problem
    solver = PULP_CBC_CMD(msg=0)  # Suppress solver output
    prob.solve(solver)

    optimization_time_ms = (time.perf_counter() - start_time) * 1000

    # Check solver status
    status = LpStatus[prob.status]

    if status not in ["Optimal", "Feasible"]:
        # Problem is infeasible or failed
        return OptimizationRecommendation(
            selected_clouds=[],
            selected_tiers={},
            estimated_monthly_cost_usd=float('inf'),
            estimated_latency_ms=float('inf'),
            durability_achieved=0.0,
            cost_breakdown={},
            optimization_time_ms=optimization_time_ms,
            solver_status="infeasible" if status == "Infeasible" else "timeout",
            reasoning=f"No feasible solution found. Status: {status}. "
                     f"Constraints may be too strict (budget too low, latency too strict, or geo restrictions too narrow)."
        )

    # Extract solution
    selected_clouds = []
    selected_tiers = {}
    cost_breakdown = {}
    total_cost = 0.0
    total_latency = 0.0
    count = 0

    for (cloud, tier), var in x.items():
        if var.varValue and var.varValue > 0.5:  # Binary variable is 1
            selected_clouds.append(cloud)
            selected_tiers[cloud] = tier

            cloud_cost = costs[(cloud, tier)]
            cost_breakdown[f"{cloud}_{tier}"] = cloud_cost
            total_cost += cloud_cost
            total_latency += latencies[(cloud, tier)]
            count += 1

    # Calculate achieved durability (simplified: assume independence)
    # Durability with k replicas: 1 - (1 - single_durability)^k
    if count > 0:
        single_durability = 0.99999999999  # 11 nines for all providers
        durability_achieved = (1 - (1 - single_durability) ** count) * 100
        avg_latency = total_latency / count
    else:
        durability_achieved = 0.0
        avg_latency = 0.0

    # Generate reasoning
    reasoning = _generate_reasoning(
        selected_clouds=selected_clouds,
        selected_tiers=selected_tiers,
        total_cost=total_cost,
        avg_latency=avg_latency,
        constraints=constraints,
        count=count
    )

    return OptimizationRecommendation(
        selected_clouds=selected_clouds,
        selected_tiers=selected_tiers,
        estimated_monthly_cost_usd=round(total_cost, 4),
        estimated_latency_ms=round(avg_latency, 2),
        durability_achieved=round(durability_achieved, 9),
        cost_breakdown={k: round(v, 4) for k, v in cost_breakdown.items()},
        optimization_time_ms=round(optimization_time_ms, 2),
        solver_status="optimal" if status == "Optimal" else "feasible",
        reasoning=reasoning
    )


def _generate_reasoning(
    selected_clouds: List[str],
    selected_tiers: Dict[str, str],
    total_cost: float,
    avg_latency: float,
    constraints: ParsedConstraints,
    count: int
) -> str:
    """Generate human-readable explanation of the optimization decision."""

    reasoning_parts = []

    # Opening statement
    if count == 1:
        cloud = selected_clouds[0]
        tier = selected_tiers[cloud]
        reasoning_parts.append(
            f"Selected {cloud} {tier} tier as the single storage location."
        )
    else:
        cloud_tier_strs = [f"{c} ({selected_tiers[c]})" for c in selected_clouds]
        reasoning_parts.append(
            f"Selected {count} cloud replicas: {', '.join(cloud_tier_strs)}."
        )

    # Explain primary goal
    if constraints.primary_goal == "COST_MINIMIZATION":
        reasoning_parts.append(
            f"Optimized for minimum cost: ${total_cost:.2f}/month."
        )
    elif constraints.primary_goal == "LATENCY_MINIMIZATION":
        reasoning_parts.append(
            f"Optimized for low latency: {avg_latency:.0f}ms average."
        )
    elif constraints.primary_goal == "MAX_REDUNDANCY":
        reasoning_parts.append(
            f"Maximized redundancy with {count} replicas for durability."
        )
    else:  # BALANCED
        reasoning_parts.append(
            f"Balanced cost (${total_cost:.2f}/mo) and latency ({avg_latency:.0f}ms)."
        )

    # Mention constraints that were active
    active_constraints = []
    if constraints.redundancy_level > 1:
        active_constraints.append(f"{constraints.redundancy_level}+ replicas required")
    if constraints.max_budget_monthly_usd:
        active_constraints.append(f"${constraints.max_budget_monthly_usd}/mo budget limit")
    if constraints.max_latency_ms:
        active_constraints.append(f"{constraints.max_latency_ms}ms max latency")
    if constraints.geo_restriction:
        active_constraints.append(f"geo-restricted to {len(constraints.geo_restriction)} region(s)")

    if active_constraints:
        reasoning_parts.append(
            f"Constraints: {', '.join(active_constraints)}."
        )

    # Access pattern note
    reasoning_parts.append(
        f"Access pattern: {constraints.access_pattern}."
    )

    return " ".join(reasoning_parts)
