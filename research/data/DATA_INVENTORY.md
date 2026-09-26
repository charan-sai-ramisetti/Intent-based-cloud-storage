---
name: data-audit
---
# Data Audit: TriCloud Vault Benchmarks

## 1. Existing Datasets

| Filename | Type | Description |
| :--- | :--- | :--- |
| `results.csv` | CSV | Raw benchmark results of cloud uploads. |

## 2. Inventory: `results.csv`

- **Total Rows**: 3900
- **Cloud Providers**: AWS, AZURE, GCP
- **Columns**: `provider`, `method`, `mode`, `file_size_mb`, `chunk_size_mb`, `trial`, `total_time_s`, `throughput_MBps`, `ttfb_s`, `url_gen_s`, `chunk_mean_s`, `chunk_std_s`, `retries`, `failed_chunks`, `cpu_mean_pct`, `cpu_max_pct`, `ram_mean_pct`, `ram_max_pct`, `ram_used_mean_mb`, `ram_total_mb`, `metrics_start_ts`, `metrics_end_ts`, `status`
- **Data Quality**: All 3900 rows have `status` = 'ok'. No null providers detected.
