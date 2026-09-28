"""
Monte Carlo Benchmark Runner for Cloud Storage Placement Optimization.

Executes comparative benchmarks evaluating MILP vs. 4 Baseline Heuristics
across synthetic workloads, collecting statistical metrics for research publication.
"""

import time
import numpy as np
import pandas as pd
import os
import django
import sys
from typing import List, Dict, Any

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tri_cloud_vault.settings')
django.setup()

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
        cost_milp = milp_res.estimated_monthly_cost_usd

        # 2. Run Baselines
        baselines = run_all_baselines(file_size, constraints)

        is_feasible = milp_res.solver_status in ["optimal", "feasible"]
        if is_feasible:
            feasible_count += 1

        # Helper to get detailed metrics for a recommendation
        def get_detailed_metrics(rec, milp_rec):
            cost = rec.estimated_monthly_cost_usd
            latency = rec.estimated_latency_ms
            
            # Check constraints
            budget_violation = False
            if constraints.max_budget_monthly_usd and cost > constraints.max_budget_monthly_usd:
                budget_violation = True
            
            sla_violation = False
            if constraints.max_latency_ms and latency > constraints.max_latency_ms:
                sla_violation = True
                
            redundancy_achieved = len(rec.selected_clouds)
            redundancy_violation = (redundancy_achieved < constraints.redundancy_level)
            
            is_feasible = not (budget_violation or sla_violation or redundancy_violation)
            
            return {
                "feasible": is_feasible,
                "cost_usd": cost,
                "cost_diff_pct": ((milp_rec.estimated_monthly_cost_usd - cost) / cost * 100) if cost > 0 else 0,
                "latency_ms": latency,
                "latency_diff_pct": ((milp_rec.estimated_latency_ms - latency) / latency * 100) if latency > 0 else 0,
                "redundancy_requested": constraints.redundancy_level,
                "redundancy_achieved": redundancy_achieved,
                "budget_violation": budget_violation,
                "sla_violation": sla_violation
            }

        baseline_metric_log = {}
        for b_name, b_rec in baselines.items():
            baseline_metric_log[b_name] = get_detailed_metrics(b_rec, milp_res)

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
            "milp_clouds": ", ".join(milp_res.selected_clouds) if is_feasible else "None",
            **{f"{b}_{m}": v for b, metrics in baseline_metric_log.items() for m, v in metrics.items()}
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

if __name__ == "__main__":
    results = run_comprehensive_benchmark(n_samples=50)
    print("Benchmark complete.")
    from .report_exporter import export_benchmark_to_csv
    export_benchmark_to_csv(results["dataframe"], "research/data/optimizer/benchmark_results.csv")

