import unittest
import pandas as pd
from backend.tri_cloud_vault.optimizer.milp_solver import solve_optimal_placement
from backend.tri_cloud_vault.intent.schemas import ParsedConstraints

class TestMILPSolver(unittest.TestCase):
    def test_solver_feasibility(self):
        c = ParsedConstraints(redundancy_level=1)
        res = solve_optimal_placement(1024**3, c)
        self.assertEqual(res.solver_status, 'optimal')

    def test_budget_constraint(self):
        # Very low budget should force infeasible
        c = ParsedConstraints(max_budget_monthly_usd=0.0001)
        res = solve_optimal_placement(1024**3, c)
        self.assertEqual(res.solver_status, 'infeasible')

if __name__ == "__main__":
    unittest.main()
