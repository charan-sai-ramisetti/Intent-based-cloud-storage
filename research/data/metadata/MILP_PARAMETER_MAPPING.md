---
name: milp-parameter-mapping
---
# MILP Parameter Mapping

| Parameter | MILP Variable | Source | Dataset/Location | Unit | Aggregation | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Latency | `latencies` | provider pricing | `cloud_parameters.csv` | ms | direct | From verified pricing table |
| Storage Cost | `costs` | provider pricing | `cloud_parameters.csv` | USD/GB-month | direct | From verified pricing table |
| operations Cost | `costs` | provider pricing | `cloud_parameters.csv` | USD/10k | direct | From verified pricing table |
| egress Cost | `costs` | provider pricing | `cloud_parameters.csv` | USD/GB | direct | From verified pricing table |
| Availability | - | provider pricing | `cloud_parameters.csv` | % | direct | From verified pricing table |
| Durability | - | provider pricing | `cloud_parameters.csv` | % | direct | From verified pricing table |
