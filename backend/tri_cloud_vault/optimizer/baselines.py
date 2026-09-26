import pandas as pd
import os
from intent.schemas import ParsedConstraints

# Define clouds and tiers
CLOUDS = ["AWS", "AZURE", "GCP"]
TIERS = ["standard", "infrequent", "archive"]

def get_baseline_recommendations(file_size_gb: float, constraints: ParsedConstraints) -> dict:
    """
    Generate placement recommendations for baseline algorithms:
    Single Cloud AWS, Round Robin, Lowest Cost Greedy.
    """

    # Load parameters
    param_path = os.path.join(os.path.dirname(__file__), '..', '..', 'research/data/optimizer/cloud_parameters.csv')
    df = pd.read_csv(param_path)

    # Helper to calculate cost
    def calculate_cost(row, file_size_gb):
        # Using cost logic compatible with milp_solver.py
        # Simplified for baseline comparison or reuse helper
        storage_cost = file_size_gb * row['storage_cost_usd_gb_month']
        # Note: Access pattern/operations not strictly required for basic baseline cost comparison if using pre-calculated rows,
        # but for consistency with solver, should match the cost breakdown.
        return storage_cost # Placeholder for total cost

    # Baseline 1: Single Cloud AWS (Standard)
    aws_std = df[(df['cloud'] == 'AWS') & (df['storage_tier'] == 'standard')].iloc[0]
    single_aws_cost = calculate_cost(aws_std, file_size_gb)

    # Baseline 2: Lowest Cost Greedy
    cheapest = df.nsmallest(constraints.redundancy_level, 'storage_cost_usd_gb_month')
    greedy_cost = cheapest['storage_cost_usd_gb_month'].sum() * file_size_gb

    # Baseline 3: Round Robin (Simplified: one from each unique)
    # Define as AWS, AZURE, GCP in standard tier
    rr_clouds = df[df['storage_tier'] == 'standard'].head(constraints.redundancy_level)
    rr_cost = rr_cost = rr_clouds['storage_cost_usd_gb_month'].sum() * file_size_gb

    return {
        "single_aws": single_aws_cost,
        "greedy_cheapest": greedy_cost,
        "round_robin": rr_cost
    }

if __name__ == "__main__":
    # Test
    c = ParsedConstraints(redundancy_level=2)
    print(get_baseline_recommendations(1.0, c))
