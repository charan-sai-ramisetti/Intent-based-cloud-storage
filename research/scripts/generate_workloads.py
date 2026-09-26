import pandas as pd
import numpy as np
import os
import json

def generate_workloads(n_workloads=100):
    """
    Generate reproducible synthetic workloads.
    """
    workloads = []

    for i in range(n_workloads):
        # Access patterns
        pattern = np.random.choice(["hot", "warm", "cold", "archival"])
        # File sizes: log-normal distribution for file sizes
        file_size_gb = np.random.lognormal(mean=np.log(1), sigma=1)

        workload = {
            "workload_id": i,
            "access_pattern": pattern,
            "file_size_bytes": int(file_size_gb * 1024**3),
            "redundancy": np.random.randint(1, 4),
            "primary_goal": np.random.choice(["COST_MINIMIZATION", "LATENCY_MINIMIZATION", "BALANCED"])
        }
        workloads.append(workload)

    os.makedirs('research/data/workloads', exist_ok=True)
    with open('research/data/workloads/experiment_workloads.json', 'w') as f:
        json.dump(workloads, f, indent=4)

if __name__ == "__main__":
    generate_workloads()
    print("Workloads generated successfully.")
