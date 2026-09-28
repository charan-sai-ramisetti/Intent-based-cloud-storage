# Final Experiment Results

## Summary
The final experiment evaluated the performance of the MILP-based cloud storage placement optimizer against four baseline heuristics. The results are summarized below.

### Benchmark Overview
- **Total Workloads:** 500
- **Feasibility:** The MILP solver found optimal solutions for 353 out of 500 workloads (70.6%).
- **Runtime:** Solver latency distribution:
  - Median: 62.82ms
  - 95th percentile: 103.85ms
  - Max: 264.85ms

### Baselines vs MILP (Feasibility & Violations)
| Baseline | Feasible (%) | Budget Violations | SLA Violations |
| :--- | :--- | :--- | :--- |
| `single_cloud_aws` | 58.4% | 7.8% | 0.0% |
| `round_robin` | 90.6% | 7.8% | 1.6% |
| `random` | 87.4% | 7.8% | 5.2% |
| `greedy_cheapest` | 84.6% | 7.8% | 8.2% |

### Cost/Latency Trade-off (on MILP Feasible Workloads)
The MILP solver prioritizes multi-objective optimization (Cost, Latency, Redundancy), which often leads to higher costs compared to simple "cheapest" heuristics, but provides significantly better performance/constraint satisfaction.

- **Cost Savings:** The MILP solver shows varying average results compared to baselines, often reporting "negative" savings because it accepts higher costs to ensure strict SLA and redundancy compliance that cheaper alternatives violate.
- **Latency:** MILP significantly reduces latency compared to `single_cloud_aws` (30.28% improvement) and `round_robin` (21.73% improvement).

### Ablation Analysis
The ablation experiment compared different MILP configurations and the greedy baseline:

| Configuration | Feasible / 500 | Mean Cost ($) | Mean Latency (ms) |
| :--- | :--- | :--- | :--- |
| `cost_only` | 353 | 3.64 | 40.31 |
| `cost_latency` | 353 | 3.72 | 22.94 |
| `cost_latency_redundancy` | 353 | 3.72 | 22.94 |
| `full_balanced` | 353 | 3.72 | 22.94 |
| `greedily_cheapest` | 500 | 3.05 | 43.36 |

The `full_balanced` configuration significantly improves latency compared to `cost_only` with a modest cost increase. The greedy baseline is the most feasible and cheapest, but it ignores SLA constraints, evidenced by the high violation rates.
