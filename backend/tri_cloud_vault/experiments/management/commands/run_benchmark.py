"""
Management command to run empirical multi-cloud optimization benchmarks.

Usage:
    python manage.py run_benchmark --samples 100 --output ./benchmark_reports/
"""

import os
from django.core.management.base import BaseCommand
from experiments.benchmark_runner import run_comprehensive_benchmark
from experiments.report_exporter import export_benchmark_to_csv, generate_latex_table, generate_benchmark_plots


class Command(BaseCommand):
    help = "Run empirical Monte Carlo benchmarks comparing MILP against baseline heuristics"

    def add_arguments(self, parser):
        parser.add_argument(
            "--samples",
            type=int,
            default=100,
            help="Number of synthetic workload samples (default: 100)"
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducibility (default: 42)"
        )
        parser.add_argument(
            "--output",
            type=str,
            default="benchmark_results",
            help="Directory to save CSV data, LaTeX tables, and plots"
        )

    def handle(self, *args, **options):
        samples = options["samples"]
        seed = options["seed"]
        output_dir = options["output"]

        self.stdout.write(self.style.NOTICE(f"Starting TriCloud Vault Monte Carlo Benchmark (N={samples}, seed={seed})..."))

        results = run_comprehensive_benchmark(n_samples=samples, seed=seed)
        summary = results["summary"]
        df = results["dataframe"]

        os.makedirs(output_dir, exist_ok=True)

        # 1. Export CSV
        csv_path = os.path.join(output_dir, "benchmark_data.csv")
        export_benchmark_to_csv(df, csv_path)
        self.stdout.write(self.style.SUCCESS(f"Saved dataset: {csv_path}"))

        # 2. Export LaTeX Table
        latex_str = generate_latex_table(summary)
        tex_path = os.path.join(output_dir, "table_comparison.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_str)
        self.stdout.write(self.style.SUCCESS(f"Saved LaTeX table: {tex_path}"))

        # 3. Generate Visualizations (if matplotlib available)
        try:
            plots = generate_benchmark_plots(df, output_dir)
            for name, path in plots.items():
                self.stdout.write(self.style.SUCCESS(f"Generated plot ({name}): {path}"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not generate plots (matplotlib/seaborn error): {e}"))

        # Print summary to console
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("BENCHMARK RESULTS SUMMARY"))
        self.stdout.write("="*60)
        self.stdout.write(f"Workload Feasibility Rate: {summary['feasibility_rate_pct']}%")
        self.stdout.write(f"Mean Solver Latency:      {summary['solver_latency']['mean_ms']} ms")
        self.stdout.write(f"P90 Solver Latency:       {summary['solver_latency']['p90_ms']} ms")
        self.stdout.write(f"Cost Savings vs Single Cloud: {summary['mean_cost_savings_pct']['vs_single_cloud_aws']}%")
        self.stdout.write(f"Cost Savings vs Round Robin:  {summary['mean_cost_savings_pct']['vs_round_robin']}%")
        self.stdout.write("="*60 + "\n")
