import sys
import os
import unittest
import django

# Add backend to path for imports
sys.path.append(os.path.abspath('backend/tri_cloud_vault'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tri_cloud_vault.settings')
django.setup()

from optimizer.milp_solver import solve_optimal_placement
from intent.schemas import ParsedConstraints

class TestPipelineValidation(unittest.TestCase):

    def test_redundancy_two_distinct_clouds(self):
        # replicas=2, should produce 2 distinct cloud providers
        constraints = ParsedConstraints(
            redundancy_level=2,
            primary_goal="COST_MINIMIZATION",
            access_pattern="cold"
        )
        res = solve_optimal_placement(1024*1024*100, constraints)
        self.assertEqual(res.solver_status, "optimal")
        self.assertEqual(len(set(res.selected_clouds)), 2)

    def test_redundancy_three_distinct_clouds(self):
        # replicas=3, should produce 3 distinct cloud providers
        constraints = ParsedConstraints(
            redundancy_level=3,
            primary_goal="COST_MINIMIZATION",
            access_pattern="cold"
        )
        res = solve_optimal_placement(1024*1024*100, constraints)
        self.assertEqual(res.solver_status, "optimal")
        self.assertEqual(len(set(res.selected_clouds)), 3)

    def test_single_cloud_multitier_exclusion(self):
        # A provider must NOT count multiple storage tiers as multiple replicas.
        # This is implicitly tested by redundancy constraint being >= providers,
        # but we can verify it by checking if solver allows it for a trivial case.
        # However, checking if solver produces valid output for it is difficult directly
        # without inspecting decision variables.
        # We check redundancy achieved.
        constraints = ParsedConstraints(
            redundancy_level=2,
            primary_goal="COST_MINIMIZATION",
            access_pattern="cold"
        )
        res = solve_optimal_placement(1024*1024*100, constraints)
        self.assertEqual(res.solver_status, "optimal")
        # Ensure we don't have multiple tiers for the same cloud,
        # and that we have exactly at least 2 distinct providers
        self.assertEqual(len(res.selected_clouds), len(set(res.selected_clouds)))
        self.assertTrue(len(set(res.selected_clouds)) >= 2 )

    def test_budget_constraint(self):
        # Strict budget should filter out solutions
        constraints = ParsedConstraints(
            redundancy_level=1,
            primary_goal="COST_MINIMIZATION",
            access_pattern="cold",
            max_budget_monthly_usd=0.0000000001
        )
        res = solve_optimal_placement(1024*1024*100, constraints)
        self.assertEqual(res.solver_status, "infeasible")

    def test_latency_sla_constraint(self):
        # Extremely low latency requirement should be infeasible
        constraints = ParsedConstraints(
            redundancy_level=1,
            primary_goal="COST_MINIMIZATION",
            access_pattern="hot",
            max_latency_ms=1 # Should be infeasible as min is ~20ms
        )
        res = solve_optimal_placement(1024*1024*100, constraints)
        self.assertEqual(res.solver_status, "infeasible")

    def test_cost_precision(self):
        # Check if cost is sufficiently precise
        constraints = ParsedConstraints(redundancy_level=1, primary_goal="COST_MINIMIZATION")
        res = solve_optimal_placement(1024*1024, constraints)
        # Check for non-zero cost at high precision
        cost_str = f"{res.estimated_monthly_cost_usd:.6f}"
        self.assertNotEqual(cost_str, "0.000000")

if __name__ == '__main__':
    unittest.main()
