import pandas as pd
import numpy as np
import os

# Load the raw results
df = pd.read_csv('research/data/optimizer/ablation_results.csv')

# Filter out infeasible results for metric calculation
feasible_df = df[df['status'] == 'optimal']

# Calculate aggregates grouped by configuration
configs = df['config'].unique()
stats = []

for config in configs:
    config_df = feasible_df[feasible_df['config'] == config]

    # Basic metrics
    row = {
        'config': config,
        'count': len(config_df),
        'mean_cost': config_df['cost_usd'].mean(),
        'median_cost': config_df['cost_usd'].median(),
        'std_cost': config_df['cost_usd'].std(),
        'mean_latency': config_df['latency_ms'].mean(),
        'median_latency': config_df['latency_ms'].median(),
        'std_latency': config_df['latency_ms'].std(),
        'feasibility_rate': len(config_df) / 50 * 100
    }
    stats.append(row)

stats_df = pd.DataFrame(stats)

# Save summary
os.makedirs('research/data/optimizer', exist_ok=True)
stats_df.to_csv('research/data/optimizer/ablation_summary.csv', index=False)

print("Ablation Summary Stats:")
print(stats_df)
