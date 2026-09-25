import unittest
from unittest.mock import patch, MagicMock
import json

from intent.schemas import StorageIntentInput, ParsedConstraints, OptimizationRecommendation
from intent.llm_parser import (
    parse_storage_intent,
    parse_intent_heuristic,
    parse_intent_bedrock,
    parse_intent_azure_openai,
)


class IntentHeuristicTests(unittest.TestCase):
    """Tests for the offline rule-based fallback parser."""

    def test_schema_defaults(self):
        constraints = ParsedConstraints()
        self.assertEqual(constraints.redundancy_level, 1)
        self.assertEqual(constraints.durability_target, 99.999999999)
        self.assertEqual(constraints.primary_goal, "BALANCED")
        self.assertEqual(constraints.access_pattern, "warm")
        self.assertEqual(constraints.data_sensitivity, "internal")

    def test_cheapest_archival_intent(self):
        text = "I need the cheapest storage possible for cold archive backups"
        constraints, latency_ms, conf = parse_intent_heuristic(text, file_size_bytes=50 * 1024 * 1024)
        self.assertEqual(constraints.primary_goal, "COST_MINIMIZATION")
        self.assertEqual(constraints.access_pattern, "archival")
        self.assertGreater(conf, 0.5)

    def test_high_redundancy_and_latency(self):
        text = "Store financial data with 3 copies and ultra low latency under 50ms"
        constraints, latency_ms, conf = parse_intent_heuristic(text, file_size_bytes=100 * 1024 * 1024)
        self.assertEqual(constraints.redundancy_level, 3)
        self.assertEqual(constraints.primary_goal, "LATENCY_MINIMIZATION")
        self.assertEqual(constraints.max_latency_ms, 50)

    def test_budget_extraction(self):
        text = "Budget is tight, max $5 per month for archival video files"
        constraints, latency_ms, conf = parse_intent_heuristic(text, file_size_bytes=200 * 1024 * 1024)
        self.assertEqual(constraints.access_pattern, "archival")
        self.assertEqual(constraints.max_budget_monthly_usd, 5.0)

    def test_hipaa_compliance(self):
        text = "HIPAA compliant storage needed for patient records, must be highly durable"
        constraints, _, _ = parse_intent_heuristic(text, file_size_bytes=10 * 1024 * 1024)
        self.assertIn("HIPAA", constraints.compliance_requirements)
        self.assertEqual(constraints.primary_goal, "MAX_REDUNDANCY")

    def test_high_available_3_clouds(self):
        """Verify 'high available data in 3 clouds' parses to 3 replicas with MAX_REDUNDANCY and no fake budget."""
        text = "high available data in 3 clouds"
        constraints, latency_ms, conf = parse_intent_heuristic(text, file_size_bytes=100 * 1024 * 1024)
        self.assertEqual(constraints.redundancy_level, 3)
        self.assertEqual(constraints.primary_goal, "MAX_REDUNDANCY")
        self.assertIsNone(constraints.max_budget_monthly_usd)


class IntentFallbackFlowTests(unittest.TestCase):
    """Tests for the main parse_storage_intent fallback cascade."""

    def test_fallback_uses_heuristic(self):
        """When DEFAULT_LLM_PROVIDER=heuristic, heuristic runs directly."""
        raw_input = StorageIntentInput(
            user_text="Budget is tight, max $5 per month for archival video files",
            file_size_bytes=200 * 1024 * 1024,
            expected_read_frequency="archival",
        )
        with patch("intent.llm_parser._cfg", side_effect=lambda k, d=None: "heuristic" if k == "DEFAULT_LLM_PROVIDER" else d):
            result = parse_storage_intent(raw_input)
        self.assertIsNotNone(result.parsed_constraints)
        self.assertEqual(result.parsed_constraints.access_pattern, "archival")
        self.assertEqual(result.parsed_constraints.max_budget_monthly_usd, 5.0)
        self.assertEqual(result.llm_provider, "heuristic")


class BedrockParserTests(unittest.TestCase):
    """Tests for AWS Bedrock Claude integration (mocked boto3 call)."""

    def _make_bedrock_response(self, constraints_dict: dict) -> MagicMock:
        """Build a mock boto3 bedrock-runtime invoke_model response."""
        body_content = {
            "id": "msg_mock",
            "type": "message",
            "role": "assistant",
            "stop_reason": "tool_use",
            "content": [
                {
                    "type": "tool_use",
                    "name": "extract_storage_constraints",
                    "id": "toolu_mock",
                    "input": constraints_dict,
                }
            ],
        }
        body_bytes = json.dumps(body_content).encode("utf-8")

        mock_stream = MagicMock()
        mock_stream.read.return_value = body_bytes

        mock_response = MagicMock()
        mock_response.__getitem__ = lambda self, key: mock_stream if key == "body" else None
        return mock_response

    @patch("boto3.client")
    def test_bedrock_cost_minimization(self, mock_boto):
        """Bedrock Claude correctly extracts COST_MINIMIZATION goal."""
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.invoke_model.return_value = self._make_bedrock_response({
            "primary_goal": "COST_MINIMIZATION",
            "access_pattern": "cold",
            "redundancy_level": 1,
        })

        constraints, latency_ms, confidence = parse_intent_bedrock(
            "cheapest option for infrequent backups", 50 * 1024 * 1024
        )
        self.assertEqual(constraints.primary_goal, "COST_MINIMIZATION")
        self.assertEqual(constraints.access_pattern, "cold")
        self.assertGreater(confidence, 0.9)

    @patch("boto3.client")
    def test_bedrock_max_redundancy(self, mock_boto):
        """Bedrock Claude extracts MAX_REDUNDANCY with 3 replicas."""
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.invoke_model.return_value = self._make_bedrock_response({
            "primary_goal": "MAX_REDUNDANCY",
            "access_pattern": "hot",
            "redundancy_level": 3,
            "max_latency_ms": 100,
        })

        constraints, latency_ms, confidence = parse_intent_bedrock(
            "financial records, 3 replicas, low latency", 100 * 1024 * 1024
        )
        self.assertEqual(constraints.redundancy_level, 3)
        self.assertEqual(constraints.max_latency_ms, 100)


class AzureOpenAIParserTests(unittest.TestCase):
    """Tests for Azure OpenAI GPT-4o integration (mocked AzureOpenAI client)."""

    def _make_azure_response(self, constraints_dict: dict) -> MagicMock:
        """Build a mock AzureOpenAI chat completion response."""
        tool_call = MagicMock()
        tool_call.function.arguments = json.dumps(constraints_dict)

        message = MagicMock()
        message.tool_calls = [tool_call]

        choice = MagicMock()
        choice.message = message
        choice.finish_reason = "tool_calls"

        response = MagicMock()
        response.choices = [choice]
        return response

    @patch("openai.AzureOpenAI")
    def test_azure_openai_balanced_intent(self, mock_azure_cls):
        """Azure OpenAI extracts BALANCED goal with HIPAA compliance."""
        mock_client = MagicMock()
        mock_azure_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = self._make_azure_response({
            "primary_goal": "BALANCED",
            "access_pattern": "warm",
            "compliance_requirements": ["HIPAA"],
            "data_sensitivity": "confidential",
        })

        with patch("intent.llm_parser._cfg", side_effect=lambda k, d=None: {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-4o",
            "AZURE_OPENAI_API_VERSION": "2024-08-01-preview",
        }.get(k, d)):
            constraints, latency_ms, confidence = parse_intent_azure_openai(
                "store patient health records with HIPAA compliance", 20 * 1024 * 1024
            )

        self.assertIn("HIPAA", constraints.compliance_requirements)
        self.assertEqual(constraints.data_sensitivity, "confidential")
        self.assertGreater(confidence, 0.9)

    @patch("openai.AzureOpenAI")
    def test_azure_openai_budget_constraint(self, mock_azure_cls):
        """Azure OpenAI respects budget constraint extraction."""
        mock_client = MagicMock()
        mock_azure_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = self._make_azure_response({
            "primary_goal": "COST_MINIMIZATION",
            "access_pattern": "archival",
            "max_budget_monthly_usd": 3.0,
        })

        with patch("intent.llm_parser._cfg", side_effect=lambda k, d=None: {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-4o",
            "AZURE_OPENAI_API_VERSION": "2024-08-01-preview",
        }.get(k, d)):
            constraints, _, _ = parse_intent_azure_openai(
                "archive old videos, maximum $3/month", 500 * 1024 * 1024
            )

        self.assertEqual(constraints.max_budget_monthly_usd, 3.0)
        self.assertEqual(constraints.primary_goal, "COST_MINIMIZATION")
