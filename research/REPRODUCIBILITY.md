# Reproducibility Documentation

This project uses a deterministic data processing pipeline to map experimental benchmark data to MILP optimization parameters.

## Pipeline
1. `clean_data.py`: Preprocesses raw `results_raw.csv`.
2. `generate_parameters.py`: Joins benchmark data with provider pricing lists to create `cloud_parameters.csv`.
3. `milp_solver.py`: Consumes `cloud_parameters.csv` for optimization.

All scripts depend on `research/data/optimizer/cloud_parameters.csv` ensuring all algorithms (MILP + Baselines) operate on the same data.
