
import pandas as pd
import numpy as np

def calculate_stats():
    bench = pd.read_csv('research/data/optimizer/benchmark_results.csv')
    ablation = pd.read_csv('research/data/optimizer/ablation_results.csv')

    print('=== BENCHMARK OVERVIEW ===')
    print(f'Total workloads: {len(bench)}')
    print('Feasibility counts:')
    print(bench['milp_status'].value_counts())

    feasible = bench[bench['milp_status'] == 'optimal']
    print(f'Feasible count: {len(feasible)} ({len(feasible)/len(bench)*100:.2f}%)')

    print('\n--- SOLVER RUNTIME (ms) ---')
    print(bench['milp_time_ms'].describe(percentiles=[0.5, 0.9, 0.95, 0.99]))

    print('\n--- BASELINE FEASIBILITY / VIOLATIONS (across all 500 workloads) ---')
    baselines = ['single_cloud_aws', 'round_robin', 'random', 'greedy_cheapest']
    for b in baselines:
        feas = bench[f'{b}_feasible'].sum()
        budget_v = bench[f'{b}_budget_violation'].sum()
        sla_v = bench[f'{b}_sla_violation'].sum()
        print(f'{b}: Feasible={feas} ({feas/len(bench)*100:.1f}%), Budget Violations={budget_v} ({budget_v/len(bench)*100:.1f}%), SLA Violations={sla_v} ({sla_v/len(bench)*100:.1f}%)')

    print('\n--- COST COMPARISON (on MILP feasible workloads) ---')
    for b in baselines:
        milp_c = feasible['milp_cost_usd']
        base_c = feasible[f'{b}_cost_usd']
        savings = (base_c - milp_c) / base_c * 100
        print(f'{b}: Mean Savings={savings.mean():.2f}%, Median Savings={savings.median():.2f}%, Min={savings.min():.2f}%, Max={savings.max():.2f}%')
        print(f'   Mean Baseline Cost=${base_c.mean():.4f}, Mean MILP Cost=${milp_c.mean():.4f}')

    print('\n--- LATENCY COMPARISON (on MILP feasible workloads) ---')
    for b in baselines:
        milp_l = feasible['milp_latency_ms']
        base_l = feasible[f'{b}_latency_ms']
        diff_pct = (milp_l - base_l) / base_l * 100
        print(f'{b}: Mean Latency Diff={diff_pct.mean():.2f}%, Base Latency Mean={base_l.mean():.2f}ms, MILP Latency Mean={milp_l.mean():.2f}ms')

    print('\n=== ABLATION ANALYSIS ===')
    print(ablation.groupby('config')['status'].value_counts())
    for cfg, group in ablation.groupby('config'):
        valid = group[group['status'] == 'optimal']
        print(f'Config {cfg}: Feasible={len(valid)}/500, Mean Cost=${valid["cost_usd"].mean():.4f}, Mean Latency={valid["latency_ms"].mean():.2f}ms')

if __name__ == '__main__':
    calculate_stats()
