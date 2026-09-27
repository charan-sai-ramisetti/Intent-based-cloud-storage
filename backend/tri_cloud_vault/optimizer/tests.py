import os
import sys
import django
import unittest

# Point to settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tri_cloud_vault.settings')
# Add backend directory to path
sys.path.append(os.path.abspath('backend/tri_cloud_vault'))
django.setup()

from intent.schemas import ParsedConstraints
from optimizer.milp_solver import solve_optimal_placement
from optimizer.baselines import run_all_baselines


class OptimizerTests(unittest.TestCase):
    """Test MILP optimization solver and heuristic baselines."""

    def test_milp_solver_single_replica(self):
        print("Running test_milp_solver_single_replica")
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
        print("Running test_milp_solver_triple_replica")
        constraints = ParsedConstraints(
            redundancy_level=3,
            primary_goal="MAX_REDUNDANCY",
            access_pattern="hot"
        )
        rec = solve_optimal_placement(file_size_bytes=1024 * 1024 * 50, constraints=constraints)
        self.assertIn(rec.solver_status, ["optimal", "feasible"])
        # Should be able to pick 3 distinct clouds (AWS, Azure, GCP)
        self.assertEqual(len(rec.selected_clouds), 3)
        self.assertSetEqual(set(rec.selected_clouds), {"AWS", "AZURE", "GCP"})

    def test_baselines_execution(self):
        print("Running test_baselines_execution")
        constraints = ParsedConstraints(
            redundancy_level=2,
            primary_goal="BALANCED",
            access_pattern="warm"
        )
        baselines = run_all_baselines(file_size_bytes=1024 * 1024 * 10, constraints=constraints)
        # Verify all expected baseline implementations exist
        self.assertIn("single_cloud_aws", baselines)
        self.assertIn("round_robin", baselines)
        self.assertIn("random", baselines)
        self.assertIn("greedy_cheapest", baselines)
        self.assertEqual(len(baselines["single_cloud_aws"].selected_clouds), 1)
        self.assertEqual(len(baselines["round_robin"].selected_clouds), 2)
        self.assertEqual(len(baselines["greedy_cheapest"].selected_clouds), 2)
        self.assertEqual(len(baselines["random"].selected_clouds), 2)

if __name__ == '__main__':
    unittest.main()
