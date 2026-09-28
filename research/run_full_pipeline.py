"""
TriCloud Vault Research Pipeline Runner.
Orchestrates: Workload Gen -> Benchmark -> Ablation -> Exporters
"""

import os
import subprocess
import json

def run_pipeline():
    print("Running Pipeline...")

    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(os.getcwd(), "backend/tri_cloud_vault")

    # Phase 2: Data Preparation
    print("Preparing cloud parameters...")
    subprocess.run(["python", "research/scripts/prepare_cloud_parameters.py"], check=True, env=env)
    subprocess.run(["python", "research/scripts/validate_cloud_parameters.py"], check=True, env=env)

    # Phase 2.5: Process Performance Data
    print("Processing performance data...")
    subprocess.run(["python", "research/scripts/process_performance_data.py"], check=True, env=env)

    # Phase 3: Workload Generation
    print("Generating workloads...")
    subprocess.run(["python", "backend/tri_cloud_vault/experiments/workload_generator.py", "--count", "500", "--seed", "42"], check=True, env=env)

    # Phase 4: Benchmark Runner
    print("Running benchmarks...")
    subprocess.run(["python", "-m", "experiments.benchmark_runner"], check=True, env=env)

    # Phase 5: Ablation Study
    print("Running ablation study...")
    subprocess.run(["python", "-m", "experiments.ablation_runner"], check=True, env=env)

    print("Pipeline complete.")

if __name__ == "__main__":
    run_pipeline()
