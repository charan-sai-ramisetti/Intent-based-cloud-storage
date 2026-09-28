import pandas as pd
import numpy as np
import os

def process_performance_data():
    raw_path = 'research/data/raw/performance/results.csv'
    df = pd.read_csv(raw_path)

    group_cols = ['provider', 'file_size_mb', 'method']
    metrics = ['ttfb_s', 'throughput_MBps']

    results = []

    for metric in metrics:
        # Aggregate
        agg = df.groupby(group_cols)[metric].agg(
            mean='mean',
            median='median',
            stddev='std',
            p95=lambda x: np.percentile(x, 95),
            sample_count='count',
            min='min',
            max='max'
        ).reset_index()

        # Add metric name
        agg['metric'] = metric
        agg['source'] = 'results.csv'
        agg['region'] = 'unknown'

        results.append(agg)

    processed_df = pd.concat(results, ignore_index=True)

    # Reorder columns
    cols = ['provider', 'region', 'file_size_mb', 'method', 'metric', 'mean', 'median', 'stddev', 'p95', 'sample_count', 'source']
    processed_df = processed_df[cols]

    # Ensure processed directory exists
    os.makedirs('research/data/processed', exist_ok=True)
    processed_df.to_csv('research/data/processed/performance_parameters.csv', index=False)

    print("Aggregation complete. Processed data saved.")

    # Print summary for user
    print(processed_df.head())
    print(processed_df.info())

    return processed_df

if __name__ == "__main__":
    process_performance_data()
