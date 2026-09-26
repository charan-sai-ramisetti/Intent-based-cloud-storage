import pandas as pd
import numpy as np
import os
from telemetry.pricing_table import DEFAULT_PRICING_TABLE

def generate_optimizer_parameters():
    # 1. Load processed benchmark data
    df = pd.read_csv('research/data/processed/clean_benchmark_data.csv')

    # 2. Aggregate benchmark measurements
    # Group by cloud and method
    profiles = df.groupby(['provider', 'method']).agg({
        'total_time_s': ['mean', 'median', 'std', lambda x: x.quantile(0.95)],
        'throughput_MBps': ['mean', 'median']
    }).reset_index()

    # Flatten columns
    profiles.columns = ['cloud', 'method', 'mean_time_s', 'median_time_s', 'std_time_s', 'p95_time_s', 'mean_throughput_mbps', 'median_throughput_mbps']

    # 3. Join with pricing data
    # Create a list of all cloud/tier combinations
    params = []
    for cloud, info in DEFAULT_PRICING_TABLE.items():
        for tier, tier_info in info['tiers'].items():
            # Get performance for this cloud
            cloud_perf = profiles[profiles['cloud'] == cloud]

            # Map tier latencies from pricing table, and throughput if available from benchmarks
            # For this MVP, we map latency directly from pricing table as it is verified

            param = {
                'cloud': cloud,
                'storage_tier': tier,
                'latency_ms': tier_info.get('latency_typical_ms', 0),
                'storage_cost_usd_gb_month': tier_info.get('storage_per_gb_month', 0),
                'put_cost_usd_10k': tier_info.get('put_per_10k', 0),
                'get_cost_usd_10k': tier_info.get('get_per_10k', 0),
                'egress_cost_usd_gb': tier_info.get('egress_per_gb', 0),
                'availability': tier_info.get('availability', 0),
                'durability': info.get('durability', 0),
                'source': 'provider_pricing'
            }
            params.append(param)

    param_df = pd.DataFrame(params)

    # 4. Save
    os.makedirs('research/data/optimizer', exist_ok=True)
    param_df.to_csv('research/data/optimizer/cloud_parameters.csv', index=False)

if __name__ == "__main__":
    generate_optimizer_parameters()
    print("Optimizer parameters generated successfully.")
