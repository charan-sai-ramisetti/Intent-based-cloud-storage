import unittest
from intent.schemas import ParsedConstraints
from optimizer.milp_solver import solve_optimal_placement
from optimizer.baselines import run_all_baselines


class OptimizerTests(unittest.TestCase):
    """Test MILP optimization solver and heuristic baselines."""

    def test_milp_solver_single_replica(self):
        constraints = ParsedConstraints(
            redundancy_level=1,
            primary_goal="COST_MINIMIZATION",
            access_pattern="cold"
        )
        rec = solve_optimal_placement(file_size_bytes=1024 * 1024 * 100, constraints=constraints)
        self.assertIn(rec.solver_status, ["optimal", "feasible"])
        self.assertEqual(len(rec.selected_clouds), 1)
        self.assertGreater(rec.estimated_monthly_cost_usd, 0)
        self.assertGreaterEqual(rec.durability_achieved, 99.0)

    def test_milp_solver_triple_replica(self):
        constraints = ParsedConstraints(
            redundancy_level=3,
            primary_goal="MAX_REDUNDANCY",
            access_pattern="hot"
        )
        rec = solve_optimal_placement(file_size_bytes=1024 * 1024 * 50, constraints=constraints)
        self.assertIn(rec.solver_status, ["optimal", "feasible"])
        self.assertEqual(len(rec.selected_clouds), 3)
        self.assertSetEqual(set(rec.selected_clouds), {"AWS", "AZURE", "GCP"})

    def test_baselines_execution(self):
        constraints = ParsedConstraints(
            redundancy_level=2,
            primary_goal="BALANCED",
            access_pattern="warm"
        )
        baselines = run_all_baselines(file_size_bytes=1024 * 1024 * 10, constraints=constraints)
        self.assertIn("single_cloud_aws", baselines)
        self.assertIn("round_robin", baselines)
        self.assertIn("random", baselines)
        self.assertIn("greedy_cheapest", baselines)
        self.assertEqual(len(baselines["single_cloud_aws"].selected_clouds), 1)
        self.assertEqual(len(baselines["round_robin"].selected_clouds), 3)
