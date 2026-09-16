"""
Synthetic Workload Generator for Empirical Cloud Placement Research.

Generates representative enterprise storage workloads following empirical
distributions (Zipfian access frequencies, log-normal file sizes, multi-tenant SLA profiles).
"""

import random
import numpy as np
from typing import List, Dict, Tuple
from intent.schemas import ParsedConstraints


def generate_synthetic_workload(
    n_samples: int = 100,
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
    # mu=17.5, sigma=2.0 gives realistic file sizes in bytes
    raw_sizes = np.random.lognormal(mean=17.5, sigma=2.0, size=n_samples)
    file_sizes = np.clip(raw_sizes, 1024, 50 * 1024 * 1024 * 1024).astype(int)

    # Access frequencies following Zipfian distribution
    ranks = np.arange(1, n_samples + 1)
    zipf_weights = 1.0 / (ranks ** zipf_alpha)
    zipf_probs = zipf_weights / np.sum(zipf_weights)

    access_patterns = ["hot", "warm", "cold", "archival"]
    primary_goals = ["COST_MINIMIZATION", "LATENCY_MINIMIZATION", "MAX_REDUNDANCY", "BALANCED"]
    regions = ["ap-south-1", "centralindia", "asia-south1"]

    workload = []

    for i in range(n_samples):
        size_bytes = int(file_sizes[i])

        # Access pattern selection weighted by Zipfian popularity
        if i < n_samples * 0.15:
            pattern = "hot"
            monthly_reads = int(np.random.uniform(500, 5000))
        elif i < n_samples * 0.45:
            pattern = "warm"
            monthly_reads = int(np.random.uniform(50, 500))
        elif i < n_samples * 0.80:
            pattern = "cold"
            monthly_reads = int(np.random.uniform(2, 50))
        else:
            pattern = "archival"
            monthly_reads = int(np.random.uniform(0, 2))

        # Redundancy distribution: 1 (60%), 2 (30%), 3 (10%)
        redundancy = random.choices([1, 2, 3], weights=[0.60, 0.30, 0.10])[0]

        # Primary goal distribution
        goal = random.choices(primary_goals, weights=[0.45, 0.25, 0.15, 0.15])[0]

        # Latency SLA constraint (optional, 40% of workloads have an explicit SLA)
        has_latency_sla = random.random() < 0.40
        max_latency = random.choice([30, 50, 100, 250]) if has_latency_sla else None

        # Budget constraint (optional, 30% of workloads)
        has_budget = random.random() < 0.30
        estimated_gb = size_bytes / (1024 ** 3)
        max_budget = round(float(estimated_gb * random.uniform(0.015, 0.08) * redundancy), 2) if has_budget else None

        # Geo-restriction (optional, 20% of workloads have sovereign data residency)
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
