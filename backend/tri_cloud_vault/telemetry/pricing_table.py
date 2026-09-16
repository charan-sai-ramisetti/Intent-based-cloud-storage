"""
Static and dynamic cloud pricing data for AWS S3, Azure Blob, and GCP Storage.

Default prices reflect the configured regions:
- AWS: ap-south-1 (Mumbai)
- Azure: Central India (Pune)
- GCP: asia-south1 (Mumbai)
"""

# Real-world base pricing matrix in USD
DEFAULT_PRICING_TABLE = {
    "AWS": {
        "region": "ap-south-1",
        "durability": 99.999999999,  # 11 nines
        "tiers": {
            "standard": {
                "storage_per_gb_month": 0.023,
                "put_per_10k": 0.05,
                "get_per_10k": 0.004,
                "egress_per_gb": 0.09,
                "latency_typical_ms": 25.0,
                "availability": 99.99,
                "min_duration_days": 0,
            },
            "infrequent": {
                "storage_per_gb_month": 0.0125,
                "put_per_10k": 0.10,
                "get_per_10k": 0.01,
                "egress_per_gb": 0.09,
                "latency_typical_ms": 45.0,
                "availability": 99.9,
                "min_duration_days": 30,
            },
            "archive": {
                "storage_per_gb_month": 0.004,
                "put_per_10k": 0.05,
                "get_per_10k": 0.004,
                "egress_per_gb": 0.09,
                "latency_typical_ms": 150000.0,  # minutes to hours
                "availability": 99.9,
                "min_duration_days": 90,
            }
        }
    },
    "AZURE": {
        "region": "centralindia",
        "durability": 99.999999999,  # 11 nines (LRS)
        "tiers": {
            "standard": {  # Hot
                "storage_per_gb_month": 0.0208,
                "put_per_10k": 0.065,
                "get_per_10k": 0.005,
                "egress_per_gb": 0.087,
                "latency_typical_ms": 28.0,
                "availability": 99.9,
                "min_duration_days": 0,
            },
            "infrequent": {  # Cool
                "storage_per_gb_month": 0.0104,
                "put_per_10k": 0.13,
                "get_per_10k": 0.013,
                "egress_per_gb": 0.087,
                "latency_typical_ms": 50.0,
                "availability": 99.0,
                "min_duration_days": 30,
            },
            "archive": {  # Archive
                "storage_per_gb_month": 0.002,
                "put_per_10k": 0.13,
                "get_per_10k": 0.065,
                "egress_per_gb": 0.087,
                "latency_typical_ms": 3600000.0,  # hours
                "availability": 99.0,
                "min_duration_days": 180,
            }
        }
    },
    "GCP": {
        "region": "asia-south1",
        "durability": 99.999999999,  # 11 nines
        "tiers": {
            "standard": {
                "storage_per_gb_month": 0.023,
                "put_per_10k": 0.05,
                "get_per_10k": 0.004,
                "egress_per_gb": 0.12,
                "latency_typical_ms": 22.0,
                "availability": 99.95,
                "min_duration_days": 0,
            },
            "infrequent": {  # Nearline
                "storage_per_gb_month": 0.013,
                "put_per_10k": 0.10,
                "get_per_10k": 0.01,
                "egress_per_gb": 0.12,
                "latency_typical_ms": 40.0,
                "availability": 99.9,
                "min_duration_days": 30,
            },
            "archive": {  # Coldline / Archive
                "storage_per_gb_month": 0.0025,
                "put_per_10k": 0.10,
                "get_per_10k": 0.05,
                "egress_per_gb": 0.12,
                "latency_typical_ms": 50.0,  # Millisecond access in GCS Coldline!
                "availability": 99.9,
                "min_duration_days": 90,
            }
        }
    }
}


def get_pricing_for_cloud(cloud: str, tier: str = "standard") -> dict:
    """Get pricing parameters for a specific cloud and tier."""
    cloud_upper = cloud.upper()
    if cloud_upper not in DEFAULT_PRICING_TABLE:
        raise ValueError(f"Unknown cloud: {cloud}")

    cloud_info = DEFAULT_PRICING_TABLE[cloud_upper]
    if tier not in cloud_info["tiers"]:
        raise ValueError(f"Unknown tier {tier} for cloud {cloud}")

    return {
        "cloud": cloud_upper,
        "region": cloud_info["region"],
        "durability": cloud_info["durability"],
        **cloud_info["tiers"][tier]
    }
