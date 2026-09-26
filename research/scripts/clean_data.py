import pandas as pd
import numpy as np

def clean_data():
    # Load raw data
    df = pd.read_csv('research/data/raw/results_raw.csv')

    initial_rows = len(df)

    # 1. Validation (Example: ensure positive values)
    df = df[df['total_time_s'] > 0]
    df = df[df['file_size_mb'] > 0]

    # 2. Duplicate Check
    df = df.drop_duplicates()

    # 3. Missing/Failed (Based on 'status' == 'ok' audit, but kept for robustness)
    valid_df = df[df['status'] == 'ok'].copy()
    failed_df = df[df['status'] != 'ok'].copy()

    # Summary
    report = {
        "total_rows": initial_rows,
        "valid_rows": len(valid_df),
        "invalid_rows": initial_rows - len(valid_df),
        "failed_trials": len(failed_df)
    }

    # Save
    valid_df.to_csv('research/data/processed/clean_benchmark_data.csv', index=False)
    failed_df.to_csv('research/data/processed/failed_benchmark_data.csv', index=False)

    return report

if __name__ == "__main__":
    report = clean_data()
    print(f"Cleaning Report: {report}")
