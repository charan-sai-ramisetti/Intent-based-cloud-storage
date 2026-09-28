# Data Sources

## Documented Pricing Sources

| Provider | Region | Source | Source URL | Retrieval Method |
| :--- | :--- | :--- | :--- | :--- |
| AWS | ap-south-1 | AWS Pricing API | https://api.pricing.us-east-1.amazonaws.com | boto3 pricing client |
| Azure | centralindia | Azure Retail Prices API | https://prices.azure.com/api/retail/prices | REST API |
| GCP | asia-south1 | GCP Pricing Catalog | https://cloud.google.com/storage/pricing | Official Catalog API |

## Documented SLA Sources

| Provider | Service | Availability SLA | Durability | Source |
| :--- | :--- | :--- | :--- | :--- |
| AWS | S3 | 99.99% (Standard) | 99.999999999% | Official AWS Docs |
| Azure | Blob | 99.9% (Standard) | 99.999999999% | Official Azure Docs |
| GCP | Cloud Storage | 99.95% (Standard) | 99.999999999% | Official GCP Docs |

## Empirical Performance Data

`measured_latency_ms` and `measured_throughput_mbps` are derived from the TriCloud Vault benchmarking suite (`experiments/benchmark_runner.py`).
- Source: Empirical benchmarking execution logs.
- Limitations: Documented in `research/docs/DATA_METHODOLOGY.md`.
