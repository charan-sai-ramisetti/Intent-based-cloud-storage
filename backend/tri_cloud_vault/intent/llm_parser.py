"""
LLM-based intent parser for natural language storage requirements.

This module extracts structured storage constraints from plain English using
LLM function calling (Anthropic Tool Use / OpenAI Function Calling).

Critical constraint: The LLM only parses requirements into structured JSON.
Cloud placement decisions are ALWAYS made by the MILP optimizer, never by the LLM.
"""

import os
import json
import time
import logging
from typing import Optional, Literal
from django.conf import settings

from .schemas import StorageIntentInput, ParsedConstraints, IntentParseResult

logger = logging.getLogger(__name__)


# System prompt enforcing the research constraint
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


def parse_intent_anthropic(user_text: str, file_size_bytes: int) -> tuple[ParsedConstraints, float, float]:
    """
    Parse user intent using Anthropic Claude with Tool Use.

    Returns: (ParsedConstraints, latency_ms, confidence_score)
    """
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        start = time.perf_counter()

        prompt = f"""User intent: {user_text}
File size: {file_size_bytes / (1024**2):.2f} MB

Extract storage requirements from this text. Return a JSON object matching the constraints schema."""

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

        # Extract tool call result
        for block in response.content:
            if block.type == "tool_use" and block.name == "extract_storage_constraints":
                constraints_dict = block.input
                constraints = ParsedConstraints(**constraints_dict)

                # Confidence based on stop_reason and presence of required fields
                confidence = 0.95 if response.stop_reason == "tool_use" else 0.75

                return constraints, latency_ms, confidence

        # Fallback if no tool use
        raise ValueError("No tool use in Anthropic response")

    except Exception as e:
        logger.error(f"Anthropic parsing failed: {str(e)}")
        raise


def parse_intent_openai(user_text: str, file_size_bytes: int) -> tuple[ParsedConstraints, float, float]:
    """
    Parse user intent using OpenAI with Function Calling.

    Returns: (ParsedConstraints, latency_ms, confidence_score)
    """
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        start = time.perf_counter()

        prompt = f"""User intent: {user_text}
File size: {file_size_bytes / (1024**2):.2f} MB

Extract storage requirements from this text."""

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": INTENT_PARSER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": "extract_storage_constraints",
                    "description": "Extract structured storage requirements",
                    "parameters": CONSTRAINTS_JSON_SCHEMA
                }
            }],
            tool_choice={"type": "function", "function": {"name": "extract_storage_constraints"}}
        )

        latency_ms = (time.perf_counter() - start) * 1000

        # Extract function call result
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            constraints_dict = json.loads(tool_call.function.arguments)
            constraints = ParsedConstraints(**constraints_dict)

            confidence = 0.92 if response.choices[0].finish_reason == "tool_calls" else 0.70
            return constraints, latency_ms, confidence

        raise ValueError("No function call in OpenAI response")

    except Exception as e:
        logger.error(f"OpenAI parsing failed: {str(e)}")
        raise


def parse_intent_heuristic(user_text: str, file_size_bytes: int) -> tuple[ParsedConstraints, float, float]:
    """
    Fallback rule-based heuristic parser for offline operation or LLM API unavailability.

    Uses keyword matching to extract constraints when LLM APIs are down.
    Returns: (ParsedConstraints, latency_ms, confidence_score)
    """
    start = time.perf_counter()
    text_lower = user_text.lower()

    constraints_dict = {
        "redundancy_level": 1,
        "primary_goal": "BALANCED",
        "access_pattern": "warm",
        "data_sensitivity": "internal"
    }

    # Redundancy detection
    if any(word in text_lower for word in ["backup", "redundant", "replicate", "multiple copies"]):
        constraints_dict["redundancy_level"] = 2
    if any(word in text_lower for word in ["3 copies", "triple", "maximum redundancy", "three replicas"]):
        constraints_dict["redundancy_level"] = 3

    # Goal detection
    if any(word in text_lower for word in ["cheap", "cost", "minimize cost", "lowest price", "budget"]):
        constraints_dict["primary_goal"] = "COST_MINIMIZATION"
    elif any(word in text_lower for word in ["fast", "low latency", "quick", "speed", "performance"]):
        constraints_dict["primary_goal"] = "LATENCY_MINIMIZATION"
    elif any(word in text_lower for word in ["safe", "durable", "reliable", "max redundancy", "cannot lose"]):
        constraints_dict["primary_goal"] = "MAX_REDUNDANCY"

    # Access pattern detection
    if any(word in text_lower for word in ["frequent", "daily", "active", "hot"]):
        constraints_dict["access_pattern"] = "hot"
    elif any(word in text_lower for word in ["archive", "archival", "rarely", "cold", "backup", "glacier"]):
        constraints_dict["access_pattern"] = "archival"
    elif any(word in text_lower for word in ["infrequent", "monthly", "occasional", "ia"]):
        constraints_dict["access_pattern"] = "cold"

    # Budget extraction (basic regex)
    import re
    budget_match = re.search(r'\$?(\d+(?:\.\d+)?)\s*(?:usd|dollars?)?(?:/mo|monthly|per month)?', text_lower)
    if budget_match:
        constraints_dict["max_budget_monthly_usd"] = float(budget_match.group(1))

    # Latency extraction
    latency_match = re.search(r'(\d+)\s*ms|(\d+)\s*milliseconds?', text_lower)
    if latency_match:
        constraints_dict["max_latency_ms"] = int(latency_match.group(1) or latency_match.group(2))

    # Compliance detection
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

    # Heuristic confidence is lower
    confidence = 0.60

    return constraints, latency_ms, confidence


def parse_storage_intent(intent_input: StorageIntentInput) -> IntentParseResult:
    """
    Main entry point for intent parsing.

    Tries the configured LLM provider with automatic fallback to heuristic parser.
    """
    provider = "heuristic"
    anthropic_key = None
    openai_key = None

    if settings.configured:
        provider = getattr(settings, "DEFAULT_LLM_PROVIDER", "heuristic")
        anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", None)
        openai_key = getattr(settings, "OPENAI_API_KEY", None)
    else:
        provider = os.getenv("DEFAULT_LLM_PROVIDER", "heuristic")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

    try:
        if provider == "anthropic" and anthropic_key:
            constraints, latency_ms, confidence = parse_intent_anthropic(
                intent_input.user_text,
                intent_input.file_size_bytes
            )
            model = "claude-3-5-sonnet-20241022"

        elif provider == "openai" and openai_key:
            constraints, latency_ms, confidence = parse_intent_openai(
                intent_input.user_text,
                intent_input.file_size_bytes
            )
            model = "gpt-4-turbo-preview"

        else:
            # No API keys or heuristic explicitly chosen
            constraints, latency_ms, confidence = parse_intent_heuristic(
                intent_input.user_text,
                intent_input.file_size_bytes
            )
            provider = "heuristic"
            model = "rule-based-v1"

    except Exception as e:
        logger.warning(f"LLM parser failed, falling back to heuristic: {str(e)}")
        constraints, latency_ms, confidence = parse_intent_heuristic(
            intent_input.user_text,
            intent_input.file_size_bytes
        )
        provider = "heuristic"
        model = "rule-based-v1"

    return IntentParseResult(
        original_text=intent_input.user_text,
        parsed_constraints=constraints,
        llm_provider=provider,
        llm_model=model,
        parse_latency_ms=latency_ms,
        confidence_score=confidence
    )
