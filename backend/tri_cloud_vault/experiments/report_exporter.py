"""
Research Report & Artifact Exporter for TriCloud Vault Optimization.

Produces publication-ready LaTeX tables, CSV datasets, and Matplotlib visualizations
for empirical performance evaluation.
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, Optional


def export_benchmark_to_csv(df: pd.DataFrame, output_path: str) -> str:
    """Export benchmark evaluation results to CSV file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path


def generate_latex_table(summary: Dict[str, Any], table_name: str = "milp_vs_baselines") -> str:
    """
    Generate an IEEE/ACM compliant LaTeX table comparing MILP against baseline heuristics.
    """
    savings = summary.get("mean_cost_savings_pct", {})
    latency = summary.get("solver_latency", {})

    aws_sav = savings.get("vs_single_cloud_aws", 0.0)
    rr_sav = savings.get("vs_round_robin", 0.0)
    rnd_sav = savings.get("vs_random", 0.0)
    greedy_sav = savings.get("vs_greedy_cheapest", 0.0)

    latex = r"""\begin{table}[t]
\centering
\caption{Empirical Comparison of Intent-Driven MILP Optimizer vs. Heuristic Baselines ($N=""" + str(summary.get("n_samples", 100)) + r"""$)}
\label{tab:""" + table_name + r"""}
\begin{tabular}{lcccc}
\toprule
\textbf{Placement Strategy} & \textbf{MILP Cost Advantage} & \textbf{Durability SLA} & \textbf{Feasibility} \\
\midrule
\textbf{TriCloud MILP (Proposed)} & \textbf{Reference Optimal} & \textbf{99.999999999\%} & \textbf{""" + str(summary.get("feasibility_rate_pct", 100.0)) + r"""\%} \\
Single Cloud AWS S3 & +""" + f"{aws_sav:.2f}" + r"""\% & 99.999999999\% & 100.0\% \\
Round-Robin Distribution & +""" + f"{rr_sav:.2f}" + r"""\% & 99.999999999\% & 100.0\% \\
Random Placement & +""" + f"{rnd_sav:.2f}" + r"""\% & 99.999999999\% & 100.0\% \\
Greedy Minimum Cost & """ + (f"+{greedy_sav:.2f}" if greedy_sav >= 0 else f"{greedy_sav:.2f}") + r"""\% & 99.999999999\% & 100.0\% \\
\bottomrule
\end{tabular}
\end{table}

% Solver Performance Metrics:
% Mean Solver Time: """ + str(latency.get("mean_ms", 0.0)) + r""" ms (p90: """ + str(latency.get("p90_ms", 0.0)) + r""" ms, p99: """ + str(latency.get("p99_ms", 0.0)) + r""" ms)
"""
    return latex


def generate_benchmark_plots(df: pd.DataFrame, output_dir: str) -> Dict[str, str]:
    """
    Generate high-resolution SVG and PNG plots for research reports.

    Requires matplotlib and seaborn.
    """
    os.makedirs(output_dir, exist_ok=True)
    generated_plots = {}
    sns.set_theme(style="whitegrid")

    # Plot 1: Optimization Solver Latency Empirical CDF
    if "milp_time_ms" in df.columns:
        times = df["milp_time_ms"].dropna().values
        if len(times) > 0:
            plt.figure(figsize=(6, 4))
            sorted_times = np.sort(times)
            cdf = np.arange(len(sorted_times)) / float(len(sorted_times))

            plt.plot(sorted_times, cdf, color="#1e40af", linewidth=2, label="MILP Solver (CBC)")
            plt.title("Empirical CDF of Placement Solver Latency", fontsize=12, fontweight="bold")
            plt.xlabel("Solver Latency (ms)", fontsize=10)
            plt.ylabel("Cumulative Probability (CDF)", fontsize=10)
            plt.grid(True, linestyle="--", alpha=0.6)
            plt.legend(loc="lower right")
            plt.tight_layout()

            cdf_path = os.path.join(output_dir, "solver_latency_cdf.png")
            plt.savefig(cdf_path, dpi=300)
            plt.close()
            generated_plots["latency_cdf"] = cdf_path

    # Plot 2: Cost Comparison by Redundancy Level
    if "redundancy" in df.columns and "milp_cost_usd" in df.columns:
        valid_cols = ["redundancy", "milp_cost_usd"]
        col_map = {"milp_cost_usd": "TriCloud MILP"}
        if "single_aws_cost_usd" in df.columns:
            valid_cols.append("single_aws_cost_usd")
            col_map["single_aws_cost_usd"] = "Single AWS S3"
        if "round_robin_cost_usd" in df.columns:
            valid_cols.append("round_robin_cost_usd")
            col_map["round_robin_cost_usd"] = "Round Robin"
        if "greedy_cost_usd" in df.columns:
            valid_cols.append("greedy_cost_usd")
            col_map["greedy_cost_usd"] = "Greedy Cheapest"

        filtered_df = df[df["milp_status"].isin(["optimal", "feasible"])][valid_cols].copy()
        if not filtered_df.empty:
            plt.figure(figsize=(7, 4.5))
            plot_df = filtered_df.melt(
                id_vars=["redundancy"],
                var_name="Strategy",
                value_name="Monthly Cost ($)"
            )
            plot_df["Strategy"] = plot_df["Strategy"].map(col_map)

            sns.barplot(data=plot_df, x="redundancy", y="Monthly Cost ($)", hue="Strategy", palette="Blues_r")
            plt.title("Mean Monthly Storage Cost by Redundancy Level ($K=1,2,3$)", fontsize=12, fontweight="bold")
            plt.xlabel("Replica Count ($K$)", fontsize=10)
            plt.ylabel("Mean Cost (USD/month)", fontsize=10)
            plt.grid(True, linestyle="--", alpha=0.5, axis="y")
            plt.tight_layout()

            cost_path = os.path.join(output_dir, "cost_by_redundancy.png")
            plt.savefig(cost_path, dpi=300)
            plt.close()
            generated_plots["cost_comparison"] = cost_path

    return generated_plots
