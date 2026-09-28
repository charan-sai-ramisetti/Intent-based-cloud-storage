"""
Ablation Runner for Cloud Storage Placement Optimization.
Runs benchmarks across 5 configurations:
1. Greedy-only (heuristic)
2. Cost-only MILP
3. Cost+Latency MILP
4. Cost+Latency+Redundancy MILP
5. Full Multi-Objective (Balanced)
"""

import os
import sys
import pandas as pd
import numpy as np
import time

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tri_cloud_vault.settings')
import django
django.setup()

from intent.schemas import ParsedConstraints
from optimizer.milp_solver import solve_optimal_placement
from experiments.workload_generator import generate_synthetic_workload
from optimizer.baselines import run_all_baselines

def run_ablation_experiment():
    print("Running Ablation Experiment...")
    
    # Generate common workloads
    n_samples = 50
    workloads = generate_synthetic_workload(n_samples=n_samples, seed=42)
    
    # Ablation Configurations
    configurations = [
        {"name": "greedily_cheapest", "type": "baseline"},
        {"name": "cost_only", "goal": "COST_MINIMIZATION", "type": "milp"},
        {"name": "cost_latency", "goal": "BALANCED", "type": "milp"},
        {"name": "cost_latency_redundancy", "goal": "BALANCED", "type": "milp"},
        {"name": "full_balanced", "goal": "BALANCED", "type": "milp"}
    ]
    
    results = []
    
    for item in workloads:
        file_size = item["file_size_bytes"]
        base_constraints = item["constraints"]
        workload_id = item["workload_id"]
        
        for config in configurations:
            row = {
                "workload_id": workload_id,
                "config": config["name"]
            }
            
            if config["type"] == "baseline":
                # Assuming greedily_cheapest baselines
                baselines = run_all_baselines(file_size, base_constraints)
                rec = baselines["greedy_cheapest"]
            else:
                # Setup constraints for MILP
                # Need to construct new ParsedConstraints to avoid mutating base
                constraints = ParsedConstraints(
                    redundancy_level=config.get("redundancy", base_constraints.redundancy_level),
                    durability_target=base_constraints.durability_target,
                    max_budget_monthly_usd=base_constraints.max_budget_monthly_usd,
                    max_latency_ms=base_constraints.max_latency_ms,
                    geo_restriction=base_constraints.geo_restriction,
                    compliance_requirements=base_constraints.compliance_requirements,
                    primary_goal=config["goal"],
                    access_pattern=base_constraints.access_pattern,
                    expected_monthly_reads=base_constraints.expected_monthly_reads,
                    expected_monthly_writes=base_constraints.expected_monthly_writes,
                    data_sensitivity=base_constraints.data_sensitivity
                )
                rec = solve_optimal_placement(file_size, constraints)
            
            row["cost_usd"] = rec.estimated_monthly_cost_usd
            row["latency_ms"] = rec.estimated_latency_ms
            row["status"] = rec.solver_status
            
            results.append(row)
            
    df = pd.DataFrame(results)
    
    # Save results
    os.makedirs('research/data/optimizer', exist_ok=True)
    df.to_csv('research/data/optimizer/ablation_results.csv', index=False)
    print("Ablation Complete. Results saved to research/data/optimizer/ablation_results.csv")

if __name__ == "__main__":
    run_ablation_experiment()
