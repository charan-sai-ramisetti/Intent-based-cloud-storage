import unittest
from intent.schemas import StorageIntentInput, ParsedConstraints, OptimizationRecommendation
from intent.llm_parser import parse_storage_intent, parse_intent_heuristic


class IntentParserTests(unittest.TestCase):
    """Test Intent Parsing via regex heuristics and fallback engine."""

    def test_schema_defaults(self):
        constraints = ParsedConstraints()
        self.assertEqual(constraints.redundancy_level, 1)
        self.assertEqual(constraints.durability_target, 99.999999999)
        self.assertEqual(constraints.primary_goal, "BALANCED")
        self.assertEqual(constraints.access_pattern, "warm")
        self.assertEqual(constraints.data_sensitivity, "internal")

    def test_heuristic_parser_cheapest_intent(self):
        text = "I need the cheapest storage possible for cold archive backups"
        constraints, latency_ms, conf = parse_intent_heuristic(text, file_size_bytes=1024 * 1024 * 50)
        self.assertEqual(constraints.primary_goal, "COST_MINIMIZATION")
        self.assertEqual(constraints.access_pattern, "archival")
        self.assertGreater(conf, 0.5)

    def test_heuristic_parser_high_redundancy_and_latency(self):
        text = "Store financial data with 3 copies and ultra low latency under 50ms"
        constraints, latency_ms, conf = parse_intent_heuristic(text, file_size_bytes=1024 * 1024 * 100)
        self.assertEqual(constraints.redundancy_level, 3)
        self.assertEqual(constraints.primary_goal, "LATENCY_MINIMIZATION")
        self.assertEqual(constraints.max_latency_ms, 50)

    def test_parse_intent_fallback_execution(self):
        raw_input = StorageIntentInput(
            user_text="Budget is tight, max $5 per month for archival video files",
            file_size_bytes=1024 * 1024 * 200,
            expected_read_frequency="archival"
        )
        result = parse_storage_intent(raw_input)
        self.assertIsNotNone(result.parsed_constraints)
        self.assertEqual(result.parsed_constraints.access_pattern, "archival")
        self.assertEqual(result.parsed_constraints.max_budget_monthly_usd, 5.0)
