"""
Database models for intent parsing logs and audit trail.
"""

from django.db import models
from django.conf import settings


class IntentLog(models.Model):
    """
    Log of all parsed intents for research analysis, dataset generation, and auditing.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="intent_logs"
    )

    original_text = models.TextField()
    file_name = models.CharField(max_length=255, blank=True)
    file_size_bytes = models.BigIntegerField()

    # Parsed constraints (stored as JSON)
    parsed_constraints = models.JSONField()

    # Optimization result (stored as JSON)
    recommendation = models.JSONField(null=True, blank=True)

    # Performance and quality metrics
    llm_provider = models.CharField(max_length=50)  # anthropic, openai, heuristic
    llm_model = models.CharField(max_length=100, blank=True)
    parse_latency_ms = models.FloatField()
    optimization_latency_ms = models.FloatField(null=True, blank=True)
    confidence_score = models.FloatField()

    # Evaluation fields for research
    is_ground_truth = models.BooleanField(default=False)
    human_verified = models.BooleanField(default=False)
    accuracy_score = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["llm_provider"]),
            models.Index(fields=["is_ground_truth"]),
        ]

    def __str__(self):
        return f"IntentLog {self.id}: {self.original_text[:30]}..."
