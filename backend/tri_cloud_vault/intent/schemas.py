"""
Pydantic validation schemas for intent-driven storage optimization.

These schemas enforce strict constraints on user intent parsing and provide
validated inputs to the MILP optimization engine.
"""

from typing import Literal, Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone


class StorageIntentInput(BaseModel):
    """Raw user input for intent parsing."""

    user_text: str = Field(..., min_length=1, max_length=5000)
    file_size_bytes: int = Field(..., gt=0)
    file_type: Optional[str] = Field(None, max_length=100)
    expected_read_frequency: Optional[Literal["daily", "weekly", "monthly", "archival"]] = None


class ParsedConstraints(BaseModel):
    """
    Validated storage constraints extracted from user intent.

    This is the structured output of LLM parsing that feeds into the MILP solver.
    All fields have safe defaults for fallback operation.
    """

    # Redundancy and durability
    redundancy_level: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Minimum number of cloud replicas (1-3)"
    )

    durability_target: float = Field(
        default=99.999999999,
        ge=99.0,
        le=99.999999999,
        description="Target durability percentage (9 to 11 nines)"
    )

    # Cost constraints
    max_budget_monthly_usd: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Maximum acceptable monthly storage cost in USD"
    )

    # Performance constraints
    max_latency_ms: Optional[int] = Field(
        default=None,
        ge=0,
        le=10000,
        description="Maximum acceptable read/write latency in milliseconds"
    )

    # Geographic and compliance
    geo_restriction: Optional[List[str]] = Field(
        default=None,
        description="Allowed cloud regions (e.g., ['ap-south-1', 'centralindia', 'asia-south1'])"
    )

    compliance_requirements: List[str] = Field(
        default_factory=list,
        description="Compliance standards required (e.g., ['HIPAA', 'GDPR', 'SOC2'])"
    )

    # Optimization goal
    primary_goal: Literal[
        "COST_MINIMIZATION",
        "LATENCY_MINIMIZATION",
        "MAX_REDUNDANCY",
        "BALANCED"
    ] = Field(default="BALANCED")

    # Access pattern hints
    access_pattern: Literal["hot", "warm", "cold", "archival"] = Field(default="warm")
    expected_monthly_reads: Optional[int] = Field(default=None, ge=0)
    expected_monthly_writes: Optional[int] = Field(default=None, ge=0)

    # Data classification
    data_sensitivity: Literal["public", "internal", "confidential", "restricted"] = Field(
        default="internal"
    )

    @field_validator("geo_restriction")
    @classmethod
    def validate_regions(cls, v):
        """Validate that regions are in the supported set."""
        if v is None:
            return v

        SUPPORTED_REGIONS = {
            "ap-south-1",      # AWS Mumbai
            "centralindia",    # Azure Central India
            "asia-south1",     # GCP Mumbai
        }

        invalid = set(v) - SUPPORTED_REGIONS
        if invalid:
            raise ValueError(f"Unsupported regions: {invalid}. Supported: {SUPPORTED_REGIONS}")

        return v


class OptimizationRecommendation(BaseModel):
    """
    MILP solver output containing the optimal cloud placement policy.
    """

    selected_clouds: List[Literal["AWS", "AZURE", "GCP"]] = Field(default_factory=list)
    selected_tiers: dict[str, Literal["standard", "infrequent", "archive"]] = Field(default_factory=dict)

    estimated_monthly_cost_usd: float = Field(..., ge=0.0)
    estimated_latency_ms: float = Field(..., ge=0.0)
    durability_achieved: float = Field(..., ge=0.0, le=100.0)

    cost_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Storage, operations, and egress costs per cloud"
    )

    optimization_time_ms: float = Field(..., ge=0.0)
    solver_status: Literal["optimal", "feasible", "infeasible", "timeout"] = Field(...)

    reasoning: str = Field(..., description="Human-readable explanation of the decision")


class IntentParseResult(BaseModel):
    """
    Complete result of intent parsing including metadata for analysis.
    """

    original_text: str
    parsed_constraints: ParsedConstraints
    recommendation: Optional[OptimizationRecommendation] = None

    llm_provider: Literal["bedrock", "azure_openai", "anthropic", "openai", "heuristic"]
    llm_model: Optional[str] = None
    parse_latency_ms: float
    confidence_score: float = Field(ge=0.0, le=1.0)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # For research dataset generation
    ground_truth_constraints: Optional[ParsedConstraints] = None
    parse_errors: List[str] = Field(default_factory=list)
