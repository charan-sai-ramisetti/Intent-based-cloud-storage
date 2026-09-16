"""
Database models for cloud telemetry, pricing, and latency probing.
"""

from django.db import models


class CloudPricing(models.Model):
    """
    Historical and current pricing data for AWS, Azure, and GCP storage.
    """

    CLOUD_CHOICES = [
        ("AWS", "Amazon Web Services S3"),
        ("AZURE", "Microsoft Azure Blob"),
        ("GCP", "Google Cloud Storage"),
    ]

    TIER_CHOICES = [
        ("standard", "Standard / Hot"),
        ("infrequent", "Infrequent Access / Cool"),
        ("archive", "Archive / Cold"),
    ]

    cloud = models.CharField(max_length=10, choices=CLOUD_CHOICES)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES)
    region = models.CharField(max_length=50)

    # Storage costs ($/GB/month)
    storage_per_gb_month_usd = models.DecimalField(max_digits=10, decimal_places=6)

    # Operation costs ($ per 10,000 requests)
    put_cost_per_10k_usd = models.DecimalField(max_digits=10, decimal_places=6)
    get_cost_per_10k_usd = models.DecimalField(max_digits=10, decimal_places=6)

    # Data transfer out ($/GB)
    egress_per_gb_usd = models.DecimalField(max_digits=10, decimal_places=6)

    # SLA availability percentage
    availability_sla = models.DecimalField(max_digits=6, decimal_places=4, default=99.9)

    # Minimum storage duration in days (e.g., 30 for IA, 90 for Archive)
    min_storage_duration_days = models.IntegerField(default=0)

    # Minimum object size in KB for billing
    min_billable_size_kb = models.IntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("cloud", "tier", "region")
        indexes = [
            models.Index(fields=["cloud", "tier"]),
        ]

    def __str__(self):
        return f"{self.cloud} - {self.tier} ({self.region})"


class LatencyProbeRecord(models.Model):
    """
    Periodic network latency probes to each cloud provider region.
    """

    cloud = models.CharField(max_length=10)
    region = models.CharField(max_length=50)

    rtt_ms = models.FloatField()
    p50_latency_ms = models.FloatField(null=True, blank=True)
    p90_latency_ms = models.FloatField(null=True, blank=True)
    p99_latency_ms = models.FloatField(null=True, blank=True)

    status_code = models.IntegerField(default=200)
    is_successful = models.BooleanField(default=True)

    probed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-probed_at"]
        indexes = [
            models.Index(fields=["cloud", "-probed_at"]),
        ]
