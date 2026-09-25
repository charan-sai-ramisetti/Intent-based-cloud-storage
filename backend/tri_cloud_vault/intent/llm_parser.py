"""
LLM-based intent parser for natural language storage requirements.

This module extracts structured storage constraints from plain English using:
  - AWS Bedrock  → Anthropic Claude 3.5 Sonnet (Tool Use)     [Priority 1 - AWS Credits]
  - Azure OpenAI → GPT-4o (Function Calling)                  [Priority 2 - Azure Credits]
  - Rule-Based   → Regex heuristics (offline fallback)         [Priority 3 - Free]

Critical constraint: The LLM only parses requirements into structured JSON.
Cloud placement decisions are ALWAYS made by the MILP optimizer, never by the LLM.
"""

import os
import json
import time
import logging
from typing import Optional
from django.conf import settings

from .schemas import StorageIntentInput, ParsedConstraints, IntentParseResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt — shared across all LLM backends
# ---------------------------------------------------------------------------

INTENT_PARSER_SYSTEM_PROMPT = """You are a storage requirements analyzer for a multi-cloud storage optimization system.

Your ONLY role is to extract structured storage constraints from user text. You do NOT make cloud placement decisions.

Extract the following from the user's intent:
- Redundancy level (how many copies/replicas needed)
- Durability target (9 to 11 nines)
- Budget constraints (monthly USD limit)
- Latency requirements (max acceptable ms)
- Geographic restrictions (allowed regions)
- Compliance requirements (HIPAA, GDPR, etc.)
- Primary optimization goal (cost vs latency vs redundancy vs balanced)
- Access pattern (hot/warm/cold/archival)
- Expected read/write frequency
- Data sensitivity level

CRITICAL: You extract requirements. A separate MILP optimizer makes the actual cloud selection decision.
Never suggest which cloud provider to use. Only extract what the user needs."""


# ---------------------------------------------------------------------------
# Shared JSON schema used by all tool/function-calling backends
# ---------------------------------------------------------------------------

CONSTRAINTS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "redundancy_level": {
            "type": "integer",
            "minimum": 1,
            "maximum": 3,
            "description": "Number of cloud replicas (1-3)"
        },
        "durability_target": {
            "type": "number",
            "minimum": 99.0,
            "maximum": 99.999999999,
            "description": "Target durability percentage"
        },
        "max_budget_monthly_usd": {
            "type": "number",
            "minimum": 0.0,
            "description": "Maximum monthly cost in USD"
        },
        "max_latency_ms": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10000,
            "description": "Maximum acceptable latency in milliseconds"
        },
        "geo_restriction": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Allowed regions: ap-south-1, centralindia, asia-south1"
        },
        "compliance_requirements": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Required compliance standards"
        },
        "primary_goal": {
            "type": "string",
            "enum": ["COST_MINIMIZATION", "LATENCY_MINIMIZATION", "MAX_REDUNDANCY", "BALANCED"],
            "description": "Optimization objective"
        },
        "access_pattern": {
            "type": "string",
            "enum": ["hot", "warm", "cold", "archival"],
            "description": "Expected access frequency"
        },
        "expected_monthly_reads": {
            "type": "integer",
            "minimum": 0,
            "description": "Expected read operations per month"
        },
        "expected_monthly_writes": {
            "type": "integer",
            "minimum": 0,
            "description": "Expected write operations per month"
        },
        "data_sensitivity": {
            "type": "string",
            "enum": ["public", "internal", "confidential", "restricted"],
            "description": "Data classification level"
        }
    },
    "required": ["primary_goal", "access_pattern"]
}


# ---------------------------------------------------------------------------
# Helper: read a setting from Django settings or environment fallback
# ---------------------------------------------------------------------------

def _cfg(key: str, default=None):
    """Read from Django settings first, then OS environment."""
    if settings.configured:
        return getattr(settings, key, None) or os.getenv(key, default)
    return os.getenv(key, default)


# ---------------------------------------------------------------------------
# Priority 1: AWS Bedrock → Claude 3.5 Sonnet (Tool Use)
# ---------------------------------------------------------------------------

def parse_intent_bedrock(user_text: str, file_size_bytes: int) -> tuple[ParsedConstraints, float, float]:
    """
    Parse user intent using Anthropic Claude via Amazon Bedrock.

    No Anthropic API key required — uses AWS IAM credentials (boto3 default
    credential chain: instance role → env vars → ~/.aws/credentials).

    Returns: (ParsedConstraints, latency_ms, confidence_score)
    """
    import boto3
    import json as _json

    region = _cfg("AWS_BEDROCK_REGION", "ap-south-1")
    model_id = _cfg("AWS_BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")

    bedrock = boto3.client("bedrock-runtime", region_name=region)

    prompt = (
        f"User intent: {user_text}\n"
        f"File size: {file_size_bytes / (1024 ** 2):.2f} MB\n\n"
        "Extract storage requirements from this text. Use the extract_storage_constraints tool."
    )

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "system": INTENT_PARSER_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [{
            "name": "extract_storage_constraints",
            "description": "Extract structured storage requirements from user text",
            "input_schema": CONSTRAINTS_JSON_SCHEMA
        }],
        "tool_choice": {"type": "tool", "name": "extract_storage_constraints"}
    }

    start = time.perf_counter()
    response = bedrock.invoke_model(
        modelId=model_id,
        body=_json.dumps(request_body),
        contentType="application/json",
        accept="application/json",
    )
    latency_ms = (time.perf_counter() - start) * 1000

    response_body = _json.loads(response["body"].read())

    # Extract tool use block
    for block in response_body.get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == "extract_storage_constraints":
            constraints = ParsedConstraints(**block["input"])
            stop_reason = response_body.get("stop_reason", "")
            confidence = 0.95 if stop_reason == "tool_use" else 0.78
            logger.info(f"[Bedrock] parsed in {latency_ms:.0f}ms, confidence={confidence}")
            return constraints, latency_ms, confidence

    raise ValueError("No tool_use block in Bedrock response")


# ---------------------------------------------------------------------------
# Priority 2: Azure OpenAI → GPT-4o (Function Calling)
# ---------------------------------------------------------------------------

def parse_intent_azure_openai(user_text: str, file_size_bytes: int) -> tuple[ParsedConstraints, float, float]:
    """
    Parse user intent using GPT-4o via Azure OpenAI Service.

    Uses Azure credits — no OpenAI direct billing.
    Required env vars:
      AZURE_OPENAI_ENDPOINT          e.g. https://my-resource.openai.azure.com/
      AZURE_OPENAI_API_KEY           Key 1 from Azure Portal
      AZURE_OPENAI_DEPLOYMENT_NAME   e.g. gpt-4o
      AZURE_OPENAI_API_VERSION       e.g. 2024-08-01-preview

    Returns: (ParsedConstraints, latency_ms, confidence_score)
    """
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=_cfg("AZURE_OPENAI_ENDPOINT"),
        api_key=_cfg("AZURE_OPENAI_API_KEY"),
        api_version=_cfg("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
    )

    deployment = _cfg("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

    prompt = (
        f"User intent: {user_text}\n"
        f"File size: {file_size_bytes / (1024 ** 2):.2f} MB\n\n"
        "Extract storage requirements from this text."
    )

    start = time.perf_counter()
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": INTENT_PARSER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        tools=[{
            "type": "function",
            "function": {
                "name": "extract_storage_constraints",
                "description": "Extract structured storage requirements",
                "parameters": CONSTRAINTS_JSON_SCHEMA,
            }
        }],
        tool_choice={"type": "function", "function": {"name": "extract_storage_constraints"}},
    )
    latency_ms = (time.perf_counter() - start) * 1000

    choice = response.choices[0]
    if choice.message.tool_calls:
        args = json.loads(choice.message.tool_calls[0].function.arguments)
        constraints = ParsedConstraints(**args)
        confidence = 0.92 if choice.finish_reason == "tool_calls" else 0.72
        logger.info(f"[AzureOpenAI] parsed in {latency_ms:.0f}ms, confidence={confidence}")
        return constraints, latency_ms, confidence

    raise ValueError("No function call in Azure OpenAI response")


# ---------------------------------------------------------------------------
# Legacy direct-API parsers (kept for backward compatibility / local dev)
# ---------------------------------------------------------------------------

def parse_intent_anthropic(user_text: str, file_size_bytes: int) -> tuple[ParsedConstraints, float, float]:
    """Direct Anthropic API (requires ANTHROPIC_API_KEY). Kept for local dev."""
    from anthropic import Anthropic

    client = Anthropic(api_key=_cfg("ANTHROPIC_API_KEY"))
    prompt = (
        f"User intent: {user_text}\n"
        f"File size: {file_size_bytes / (1024**2):.2f} MB\n\n"
        "Extract storage requirements. Return a JSON object matching the constraints schema."
    )

    start = time.perf_counter()
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        system=INTENT_PARSER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        tools=[{
            "name": "extract_storage_constraints",
            "description": "Extract structured storage requirements from user text",
            "input_schema": CONSTRAINTS_JSON_SCHEMA
        }]
    )
    latency_ms = (time.perf_counter() - start) * 1000

    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_storage_constraints":
            constraints = ParsedConstraints(**block.input)
            confidence = 0.95 if response.stop_reason == "tool_use" else 0.75
            return constraints, latency_ms, confidence

    raise ValueError("No tool use in Anthropic response")


def parse_intent_openai(user_text: str, file_size_bytes: int) -> tuple[ParsedConstraints, float, float]:
    """Direct OpenAI API (requires OPENAI_API_KEY). Kept for local dev."""
    from openai import OpenAI

    client = OpenAI(api_key=_cfg("OPENAI_API_KEY"))
    prompt = (
        f"User intent: {user_text}\n"
        f"File size: {file_size_bytes / (1024**2):.2f} MB\n\n"
        "Extract storage requirements from this text."
    )

    start = time.perf_counter()
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": INTENT_PARSER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        tools=[{
            "type": "function",
            "function": {
                "name": "extract_storage_constraints",
                "description": "Extract structured storage requirements",
                "parameters": CONSTRAINTS_JSON_SCHEMA,
            }
        }],
        tool_choice={"type": "function", "function": {"name": "extract_storage_constraints"}},
    )
    latency_ms = (time.perf_counter() - start) * 1000

    if response.choices[0].message.tool_calls:
        args = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
        constraints = ParsedConstraints(**args)
        confidence = 0.92 if response.choices[0].finish_reason == "tool_calls" else 0.70
        return constraints, latency_ms, confidence

    raise ValueError("No function call in OpenAI response")


# ---------------------------------------------------------------------------
# Priority 3: Rule-based heuristic (offline, zero cost)
# ---------------------------------------------------------------------------

def parse_intent_heuristic(user_text: str, file_size_bytes: int) -> tuple[ParsedConstraints, float, float]:
    """
    Fallback rule-based heuristic parser.

    Uses keyword matching to extract constraints when both LLM backends are
    unavailable. Runs 100% offline with no API calls.

    Returns: (ParsedConstraints, latency_ms, confidence_score)
    """
    import re

    start = time.perf_counter()
    text_lower = user_text.lower()

    constraints_dict = {
        "redundancy_level": 1,
        "primary_goal": "BALANCED",
        "access_pattern": "warm",
        "data_sensitivity": "internal",
    }

    # Redundancy
    if any(w in text_lower for w in ["3 copies", "three copies", "triple", "maximum redundancy", "three replicas", "3 replicas", "3 clouds", "three clouds", "all 3 clouds", "across 3 clouds", "all clouds", "3 providers", "three providers"]):
        constraints_dict["redundancy_level"] = 3
    elif any(w in text_lower for w in ["backup", "redundant", "replicate", "multiple copies", "2 copies", "two copies", "2 clouds", "two clouds", "dual cloud", "multi cloud", "multicloud", "two replicas", "2 replicas", "2 providers", "two providers"]):
        constraints_dict["redundancy_level"] = 2

    # Optimization goal
    if any(w in text_lower for w in ["cheap", "cost", "minimize cost", "lowest price", "cheapest"]):
        constraints_dict["primary_goal"] = "COST_MINIMIZATION"
    elif any(w in text_lower for w in ["fast", "low latency", "quick", "speed", "performance", "ultra low latency"]):
        constraints_dict["primary_goal"] = "LATENCY_MINIMIZATION"
    elif any(w in text_lower for w in ["safe", "durable", "reliable", "max redundancy", "cannot lose", "high available", "high availability", "ha", "fault tolerant", "fault tolerance", "zero downtime", "resilient"]):
        constraints_dict["primary_goal"] = "MAX_REDUNDANCY"

    # Access pattern
    if any(w in text_lower for w in ["frequent", "daily", "active", "hot"]):
        constraints_dict["access_pattern"] = "hot"
    elif any(w in text_lower for w in ["archive", "archival", "rarely", "cold", "backup", "glacier"]):
        constraints_dict["access_pattern"] = "archival"
    elif any(w in text_lower for w in ["infrequent", "monthly", "occasional", "ia"]):
        constraints_dict["access_pattern"] = "cold"

    # Budget (requires explicit currency symbol, currency name, or budget phrase)
    budget_match = (
        re.search(r'\$\s*(\d+(?:\.\d+)?)', text_lower)
        or re.search(r'(\d+(?:\.\d+)?)\s*(?:usd|dollars?)', text_lower)
        or re.search(r'(?:budget|cost|price|limit)\s*(?:is|of|under|<=|:)?\s*\$?(\d+(?:\.\d+)?)', text_lower)
        or re.search(r'(\d+(?:\.\d+)?)\s*(?:/mo|monthly|per month)', text_lower)
    )
    if budget_match:
        constraints_dict["max_budget_monthly_usd"] = float(budget_match.group(1))

    # Latency (e.g. "50ms", "100 milliseconds")
    latency_match = re.search(r'(\d+)\s*ms|(\d+)\s*milliseconds?', text_lower)
    if latency_match:
        constraints_dict["max_latency_ms"] = int(latency_match.group(1) or latency_match.group(2))

    # Compliance
    compliance = []
    if "hipaa" in text_lower:
        compliance.append("HIPAA")
    if "gdpr" in text_lower:
        compliance.append("GDPR")
    if "sox" in text_lower or "sarbanes" in text_lower:
        compliance.append("SOX")
    if compliance:
        constraints_dict["compliance_requirements"] = compliance

    constraints = ParsedConstraints(**constraints_dict)
    latency_ms = (time.perf_counter() - start) * 1000
    return constraints, latency_ms, 0.60


# ---------------------------------------------------------------------------
# Main entry point with automatic failover cascade
# ---------------------------------------------------------------------------

# Provider routing map — order defines priority
_PROVIDER_MAP = {
    "bedrock":       parse_intent_bedrock,
    "azure_openai":  parse_intent_azure_openai,
    "anthropic":     parse_intent_anthropic,
    "openai":        parse_intent_openai,
    "heuristic":     parse_intent_heuristic,
}

_PROVIDER_MODEL = {
    "bedrock":       "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "azure_openai":  "gpt-4o",
    "anthropic":     "claude-3-5-sonnet-20241022",
    "openai":        "gpt-4-turbo-preview",
    "heuristic":     "rule-based-v1",
}

# Automatic failover chain — if primary fails, try these in order
_FAILOVER_CHAIN = ["bedrock", "azure_openai", "heuristic"]


def parse_storage_intent(intent_input: StorageIntentInput) -> IntentParseResult:
    """
    Main entry point for intent parsing.

    Priority order (configurable via DEFAULT_LLM_PROVIDER env var):
      1. bedrock      → AWS Bedrock Claude 3.5 Sonnet   (AWS credits, no Anthropic key)
      2. azure_openai → Azure OpenAI GPT-4o             (Azure credits, no OpenAI key)
      3. heuristic    → Regex rule-based fallback        (offline, free)

    Any failure in a higher priority provider automatically falls back to the next.
    """
    primary = _cfg("DEFAULT_LLM_PROVIDER", "bedrock")

    # Build the attempt chain: start with the primary, then append failovers (excluding primary)
    chain = [primary] + [p for p in _FAILOVER_CHAIN if p != primary]

    for provider in chain:
        parser_fn = _PROVIDER_MAP.get(provider)
        if parser_fn is None:
            logger.warning(f"Unknown provider '{provider}', skipping")
            continue

        try:
            constraints, latency_ms, confidence = parser_fn(
                intent_input.user_text, intent_input.file_size_bytes
            )
            model = _PROVIDER_MODEL.get(provider, provider)
            logger.info(f"Intent parsed by '{provider}' in {latency_ms:.0f}ms")
            break

        except Exception as exc:
            logger.warning(f"Provider '{provider}' failed: {exc}. Trying next in chain…")
            continue
    else:
        # All providers failed — this should never happen because heuristic always succeeds
        logger.error("All intent parsers failed; using bare heuristic defaults")
        constraints, latency_ms, confidence = parse_intent_heuristic(
            intent_input.user_text, intent_input.file_size_bytes
        )
        provider = "heuristic"
        model = "rule-based-v1"

    return IntentParseResult(
        original_text=intent_input.user_text,
        parsed_constraints=constraints,
        llm_provider=provider,
        llm_model=model,
        parse_latency_ms=latency_ms,
        confidence_score=confidence,
    )
