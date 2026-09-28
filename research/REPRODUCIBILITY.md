# Reproducibility Guide

## 1. Setup

### Dependencies
- Python 3.10+
- Requirements listed in `requirements.txt` (including PuLP and pandas).

### Environment
Ensure the following PYTHONPATH is set:
`export PYTHONPATH=$PYTHONPATH:$(pwd)/backend/tri_cloud_vault`

## 2. Executing the Pipeline

To run the complete experiment and generate the final dataset:

```bash
python research/run_full_pipeline.py
```

This will:
1. Prepare parameters.
2. Validate parameters.
3. Generate workloads.
4. Run benchmarks and ablation studies.
5. Create summary tables.

## 3. Configuration

- Workload count: 500
- Random seed: 42
- Solver: CBC (via PuLP)

## 4. Output Data
- All datasets are stored in `research/data/optimizer/`.
