import pandas as pd
import json
import os
from backend.tri_cloud_vault.optimizer.milp_solver import solve_optimal_placement
from backend.tri_cloud_vault.optimizer.baselines import get_baseline_recommendations
from backend.tri_cloud_vault.intent.schemas import ParsedConstraints

# Load workloads
with open('research/data/workloads/experiment_workloads.json', 'r') as f:
    workloads = json.load(f)

results = []

for w in workloads:
    constraints = ParsedConstraints(
        redundancy_level=w['redundancy'],
        primary_goal=w['primary_goal'],
        access_pattern=w['access_pattern']
    )

    # Run MILP
    milp_result = solve_optimal_placement(w['file_size_bytes'], constraints)

    # Run Baselines
    baseline_result = get_baseline_recommendations(w['file_size_bytes']/(1024**3), constraints)

    res = {
        "workload_id": w['workload_id'],
        "milp_cost": milp_result.estimated_monthly_cost_usd,
        "milp_latency": milp_result.estimated_latency_ms,
        "greedy_cost": baseline_result['greedy_cheapest'],
        "aws_cost": baseline_result['single_aws'],
        "rr_cost": baseline_result['round_robin']
    }
    results.append(res)
    print(f"Processed workload {w['workload_id']}")

# Save results
os.makedirs('research/results', exist_ok=True)
pd.DataFrame(results).to_csv('research/results/experiment_comparisons.csv', index=False)
print("Experiment completed.")
