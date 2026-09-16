"""
Monte Carlo Benchmark Runner for Cloud Storage Placement Optimization.

Executes comparative benchmarks evaluating MILP vs. 4 Baseline Heuristics
across synthetic workloads, collecting statistical metrics for research publication.
"""

import time
import numpy as np
import pandas as pd
from typing import List, Dict, Any

from optimizer.milp_solver import solve_optimal_placement
from optimizer.baselines import run_all_baselines
from .workload_generator import generate_synthetic_workload


def run_comprehensive_benchmark(
    n_samples: int = 100,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Run complete Monte Carlo benchmark over N synthetic workloads.

    Args:
        n_samples: Number of workload trials
        seed: Random seed for workload generation

    Returns:
        Dictionary containing raw trial logs, aggregate statistics, and summary metrics.
    """
    workloads = generate_synthetic_workload(n_samples=n_samples, seed=seed)

    results_log = []
    milp_runtimes = []
    savings_vs_single_aws = []
    savings_vs_round_robin = []
    savings_vs_random = []
    savings_vs_greedy = []

    feasible_count = 0

    for item in workloads:
        file_size = item["file_size_bytes"]
        constraints = item["constraints"]

        # 1. Run MILP Optimization
        t0 = time.perf_counter()
        milp_res = solve_optimal_placement(file_size, constraints)
        t_milp = (time.perf_counter() - t0) * 1000
        milp_runtimes.append(t_milp)

        # 2. Run Baselines
        baselines = run_all_baselines(file_size, constraints)

        is_feasible = milp_res.solver_status in ["optimal", "feasible"]
        if is_feasible:
            feasible_count += 1

        cost_milp = milp_res.estimated_monthly_cost_usd
        cost_aws = baselines["single_cloud_aws"].estimated_monthly_cost_usd
        cost_rr = baselines["round_robin"].estimated_monthly_cost_usd
        cost_rnd = baselines["random"].estimated_monthly_cost_usd
        cost_greedy = baselines["greedy_cheapest"].estimated_monthly_cost_usd

        # Calculate percentage savings (where baseline cost > 0 and MILP is feasible)
        if is_feasible and cost_milp < float('inf'):
            if cost_aws > 0:
                s_aws = max(0.0, (cost_aws - cost_milp) / cost_aws * 100)
                savings_vs_single_aws.append(s_aws)
            if cost_rr > 0:
                s_rr = max(0.0, (cost_rr - cost_milp) / cost_rr * 100)
                savings_vs_round_robin.append(s_rr)
            if cost_rnd > 0:
                s_rnd = max(0.0, (cost_rnd - cost_milp) / cost_rnd * 100)
                savings_vs_random.append(s_rnd)
            if cost_greedy > 0:
                s_greedy = (cost_greedy - cost_milp) / cost_greedy * 100
                savings_vs_greedy.append(s_greedy)

        results_log.append({
            "workload_id": item["workload_id"],
            "file_size_mb": item["file_size_mb"],
            "redundancy": constraints.redundancy_level,
            "access_pattern": constraints.access_pattern,
            "primary_goal": constraints.primary_goal,
            "milp_status": milp_res.solver_status,
            "milp_time_ms": round(t_milp, 2),
            "milp_cost_usd": cost_milp if cost_milp < float('inf') else None,
            "milp_latency_ms": milp_res.estimated_latency_ms if milp_res.estimated_latency_ms < float('inf') else None,
            "single_aws_cost_usd": cost_aws,
            "round_robin_cost_usd": cost_rr,
            "random_cost_usd": cost_rnd,
            "greedy_cost_usd": cost_greedy,
            "milp_clouds": ", ".join(milp_res.selected_clouds) if is_feasible else "None"
        })

    # Summary Statistics
    summary = {
        "n_samples": n_samples,
        "feasibility_rate_pct": round((feasible_count / n_samples) * 100, 2),
        "solver_latency": {
            "mean_ms": round(float(np.mean(milp_runtimes)), 2),
            "median_ms": round(float(np.median(milp_runtimes)), 2),
            "p90_ms": round(float(np.percentile(milp_runtimes, 90)), 2),
            "p99_ms": round(float(np.percentile(milp_runtimes, 99)), 2),
            "max_ms": round(float(np.max(milp_runtimes)), 2)
        },
        "mean_cost_savings_pct": {
            "vs_single_cloud_aws": round(float(np.mean(savings_vs_single_aws)), 2) if savings_vs_single_aws else 0.0,
            "vs_round_robin": round(float(np.mean(savings_vs_round_robin)), 2) if savings_vs_round_robin else 0.0,
            "vs_random": round(float(np.mean(savings_vs_random)), 2) if savings_vs_random else 0.0,
            "vs_greedy_cheapest": round(float(np.mean(savings_vs_greedy)), 2) if savings_vs_greedy else 0.0
        }
    }

    return {
        "summary": summary,
        "dataframe": pd.DataFrame(results_log),
        "raw_log": results_log
    }
