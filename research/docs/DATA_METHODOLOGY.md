# Data Methodology and Reproducibility

## Architecture
This pipeline enforces a strict separation between raw data collection, normalization (processing), and optimization usage:
1.  **Collection (`scripts/collect_*.py`):** Fetches raw snapshots into `research/data/raw/`.
2.  **Preparation (`scripts/prepare_cloud_parameters.py`):** Normalizes raw data into `research/data/optimizer/cloud_parameters.csv`.
3.  **Validation (`scripts/validate_cloud_parameters.py`):** Guaranteed constraint adherence.
4.  **Optimization:** MILP and Baselines consume exactly `cloud_parameters.csv`.

## Data Normalization Rules
- **Pricing:** Costs are converted to normalized units (USD/GB-month for storage; USD/10k for operations; USD/GB for egress).
- **Latency Sentinels:** Invalid values (e.g., historical 3600000ms placeholders) are mapped to `NaN` during normalization.
- **Missing Values:** Infeasibility is reported for missing critical data rather than utilizing fabrication.
- **Baseline Alignment:** All algorithms (MILP, Single Cloud AWS, Round Robin, Lowest Cost Greedy) work over identical input parameters, workloads, and constraints.
