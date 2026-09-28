import pandas as pd
import sys
import os

def validate_parameters(csv_path: str):
    print(f"Validating {csv_path}...")
    df = pd.read_csv(csv_path)

    # Basic validations
    assert (df['latency_ms'] >= 0).all(), "Latency must be non-negative"
    assert (df['storage_cost_usd_gb_month'] >= 0).all(), "Storage cost must be non-negative"
    assert (df['availability'] > 0).all(), "Availability must be positive"

    print("Validation successful.")

if __name__ == "__main__":
    validate_parameters('research/data/optimizer/cloud_parameters.csv')
