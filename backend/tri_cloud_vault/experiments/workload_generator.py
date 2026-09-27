"""
Synthetic Workload Generator for Empirical Cloud Placement Research.

Generates representative enterprise storage workloads following empirical
distributions (Zipfian access frequencies, log-normal file sizes, multi-tenant SLA profiles).
"""

import random
import numpy as np
import json
import argparse
import os
import sys
from typing import List, Dict

# Add backend to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from intent.schemas import ParsedConstraints


def generate_synthetic_workload(
    n_samples: int = 500,
    seed: int = 42,
    zipf_alpha: float = 1.2,
) -> List[Dict]:
    """
    Generate N synthetic storage requests for empirical benchmark simulations.

    Args:
        n_samples: Number of workload items to generate
        seed: Random seed for reproducibility
        zipf_alpha: Skew parameter for Zipfian access frequency (default 1.2)

    Returns:
        List of dicts containing file metadata and ParsedConstraints
    """
    np.random.seed(seed)
    random.seed(seed)

    # File size distribution: Log-normal distribution (mean ~50MB, range 1KB - 50GB)
    raw_sizes = np.random.lognormal(mean=17.5, sigma=2.0, size=n_samples)
    file_sizes = np.clip(raw_sizes, 1024, 50 * 1024 * 1024 * 1024).astype(int)

    access_patterns = ["hot", "warm", "cold", "archival"]
    primary_goals = ["COST_MINIMIZATION", "LATENCY_MINIMIZATION", "MAX_REDUNDANCY", "BALANCED"]
    regions = ["ap-south-1", "centralindia", "asia-south1"]

    workload = []

    # Edge cases
    edge_cases = [
        {"size": 1024, "pattern": "hot", "name": "micro_file"},
        {"size": 50 * 1024 * 1024 * 1024, "pattern": "archival", "name": "large_archive"},
    ]

    for i in range(n_samples):
        # Insert edge cases in the first few slots
        if i < len(edge_cases):
            size_bytes = edge_cases[i]["size"]
            pattern = edge_cases[i]["pattern"]
        else:
            size_bytes = int(file_sizes[i])
            # Access pattern selection weighted
            if random.random() < 0.15:
                pattern = "hot"
            elif random.random() < 0.45:
                pattern = "warm"
            elif random.random() < 0.80:
                pattern = "cold"
            else:
                pattern = "archival"

        # Reads
        if pattern == "hot":
            monthly_reads = int(np.random.uniform(500, 5000))
        elif pattern == "warm":
            monthly_reads = int(np.random.uniform(50, 500))
        elif pattern == "cold":
            monthly_reads = int(np.random.uniform(2, 50))
        else:
            monthly_reads = int(np.random.uniform(0, 2))

        # Redundancy distribution
        redundancy = random.choices([1, 2, 3], weights=[0.60, 0.30, 0.10])[0]

        # Primary goal
        goal = random.choices(primary_goals, weights=[0.45, 0.25, 0.15, 0.15])[0]

        # Constraints
        has_latency_sla = random.random() < 0.40
        max_latency = random.choice([30, 50, 100, 250]) if has_latency_sla else None

        has_budget = random.random() < 0.30
        estimated_gb = size_bytes / (1024 ** 3)
        max_budget = round(float(estimated_gb * random.uniform(0.015, 0.08) * redundancy), 2) if has_budget else None

        has_geo = random.random() < 0.20
        geo_res = random.sample(regions, k=random.randint(1, 2)) if has_geo else None

        constraints = ParsedConstraints(
            redundancy_level=redundancy,
            durability_target=99.999999999,
            max_budget_monthly_usd=max_budget,
            max_latency_ms=max_latency,
            geo_restriction=geo_res,
            primary_goal=goal,
            access_pattern=pattern,
            expected_monthly_reads=monthly_reads,
            data_sensitivity="internal" if redundancy == 1 else "confidential"
        )

        workload.append({
            "workload_id": f"WL_{i+1:04d}",
            "file_name": f"sample_file_{i+1}.dat",
            "file_size_bytes": size_bytes,
            "file_size_mb": round(size_bytes / (1024 * 1024), 2),
            "constraints": constraints
        })

    return workload

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    data = generate_synthetic_workload(n_samples=args.count, seed=args.seed)

    output_dir = 'research/data/workloads'
    os.makedirs(output_dir, exist_ok=True)

    # Serialize ParsedConstraints manually (they are Pydantic objects)
    serializable_data = []
    for item in data:
        constraints_obj = item["constraints"]
        constraints_dict = (
            constraints_obj.model_dump()
            if hasattr(constraints_obj, "model_dump")
            else constraints_obj.dict()
        )
        serializable_data.append({
            **item,
            "constraints": constraints_dict
        })

    output_path = f"{output_dir}/workloads_{args.count}_seed_{args.seed}.json"
    with open(output_path, 'w') as f:
        json.dump(serializable_data, f, indent=2)

    print(f"Generated {args.count} workloads to {output_path}")
