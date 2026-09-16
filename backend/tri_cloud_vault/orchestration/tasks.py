"""
Celery asynchronous tasks for multi-cloud storage orchestration.

Coordinates parallel uploads, multipart sessions, integrity verification,
and compensating transactions (rollback) across AWS S3, Azure Blob, and GCP Storage.
"""

import time
import logging
import uuid
from typing import Dict, List, Optional
from celery import shared_task
from django.core.cache import cache

from .fsm import StorageFSM, StorageFSMState
from clouds.aws import (
    generate_aws_upload_url,
    delete_file_from_s3,
    start_multipart_upload as aws_start_multipart,
    complete_multipart_upload as aws_complete_multipart,
    generate_presigned_multipart_urls,
)
from clouds.azure import (
    generate_azure_upload_url,
    delete_file_from_azure,
    generate_presigned_block_urls,
    commit_block_list,
)
from clouds.gcp import (
    generate_gcp_upload_url,
    delete_file_from_gcp,
    start_resumable_upload as gcp_start_resumable,
    generate_presigned_resumable_url,
)

logger = logging.getLogger(__name__)


def _get_or_create_fsm(operation_id: str) -> StorageFSM:
    """Retrieve FSM from Redis cache or create new."""
    cache_key = f"fsm:{operation_id}"
    data = cache.get(cache_key)
    if data:
        # Reconstruct FSM
        fsm = StorageFSM(operation_id)
        fsm.current_state = StorageFSMState(data["current_state"])
        fsm.context = data.get("context", {})
        return fsm
    fsm = StorageFSM(operation_id)
    return fsm


def _save_fsm(fsm: StorageFSM):
    """Save FSM state to Redis cache (1 hour expiration)."""
    cache_key = f"fsm:{fsm.operation_id}"
    cache.set(cache_key, fsm.to_dict(), timeout=3600)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def prepare_multicloud_upload_task(
    self,
    user_id: int,
    file_name: str,
    file_size_bytes: int,
    file_type: str,
    selected_clouds: List[str],
    selected_tiers: Dict[str, str],
    operation_id: Optional[str] = None
) -> Dict:
    """
    Asynchronously prepare upload sessions / presigned URLs across all selected clouds.

    Coordinates AWS, Azure, and GCP simultaneously.
    """
    if not operation_id:
        operation_id = str(uuid.uuid4())

    fsm = _get_or_create_fsm(operation_id)
    fsm.context.update({
        "user_id": user_id,
        "file_name": file_name,
        "file_size_bytes": file_size_bytes,
        "file_type": file_type,
        "selected_clouds": selected_clouds,
        "selected_tiers": selected_tiers,
    })

    fsm.transition_to(
        StorageFSMState.PREPARING_CLOUDS,
        message=f"Preparing upload sessions for {', '.join(selected_clouds)}"
    )
    _save_fsm(fsm)

    cloud_sessions = {}
    is_multipart = file_size_bytes > 10 * 1024 * 1024  # > 10MB

    try:
        fsm.transition_to(
            StorageFSMState.ALLOCATING_PRESIGNED,
            message="Allocating presigned URLs / upload IDs"
        )

        for cloud in selected_clouds:
            cloud_upper = cloud.upper()

            if cloud_upper == "AWS":
                if is_multipart:
                    key, upload_id = aws_start_multipart(user_id, file_name, file_type)
                    cloud_sessions["AWS"] = {
                        "mode": "multipart",
                        "key": key,
                        "upload_id": upload_id
                    }
                else:
                    key, url = generate_aws_upload_url(user_id, file_name, file_type)
                    cloud_sessions["AWS"] = {
                        "mode": "single",
                        "key": key,
                        "upload_url": url
                    }

            elif cloud_upper == "AZURE":
                if is_multipart:
                    res = generate_presigned_block_urls(user_id, file_name, file_size_bytes)
                    cloud_sessions["AZURE"] = {
                        "mode": "multipart",
                        "key": res["blob_name"],
                        "block_info": res,
                    }
                else:
                    key, url = generate_azure_upload_url(user_id, file_name)
                    cloud_sessions["AZURE"] = {
                        "mode": "single",
                        "key": key,
                        "upload_url": url
                    }

            elif cloud_upper == "GCP":
                if is_multipart:
                    key, session_uri = gcp_start_resumable(user_id, file_name, file_type)
                    cloud_sessions["GCP"] = {
                        "mode": "multipart",
                        "key": key,
                        "session_uri": session_uri
                    }
                else:
                    key, url = generate_gcp_upload_url(user_id, file_name, file_type)
                    cloud_sessions["GCP"] = {
                        "mode": "single",
                        "key": key,
                        "upload_url": url
                    }

        fsm.context["cloud_sessions"] = cloud_sessions
        fsm.transition_to(
            StorageFSMState.PRESIGNED_READY,
            message="All cloud upload sessions successfully prepared"
        )
        _save_fsm(fsm)

        return {
            "operation_id": operation_id,
            "status": "ready",
            "is_multipart": is_multipart,
            "sessions": cloud_sessions
        }

    except Exception as exc:
        logger.error(f"FSM preparation error for {operation_id}: {str(exc)}")
        fsm.transition_to(
            StorageFSMState.FAILED,
            message="Failed to allocate cloud upload sessions",
            error=str(exc)
        )
        _save_fsm(fsm)

        # Trigger rollback of any allocated sessions
        rollback_orchestration_task.delay(operation_id)
        raise self.retry(exc=exc)


@shared_task
def rollback_orchestration_task(operation_id: str) -> Dict:
    """
    Compensating transaction: Delete partial files and cancel active multipart uploads
    across all cloud providers if one of the replicas fails.
    """
    fsm = _get_or_create_fsm(operation_id)
    fsm.transition_to(
        StorageFSMState.ROLLING_BACK,
        message="Initiating compensating rollback across clouds"
    )
    _save_fsm(fsm)

    cloud_sessions = fsm.context.get("cloud_sessions", {})
    cleaned_clouds = []

    for cloud, session in cloud_sessions.items():
        key = session.get("key")
        if not key:
            continue

        try:
            if cloud == "AWS":
                delete_file_from_s3(key)
                cleaned_clouds.append("AWS")
            elif cloud == "AZURE":
                delete_file_from_azure(key)
                cleaned_clouds.append("AZURE")
            elif cloud == "GCP":
                delete_file_from_gcp(key)
                cleaned_clouds.append("GCP")
        except Exception as e:
            logger.warning(f"Rollback cleanup error for {cloud} (key: {key}): {str(e)}")

    fsm.transition_to(
        StorageFSMState.ROLLED_BACK,
        message=f"Rollback completed. Cleaned up: {', '.join(cleaned_clouds)}"
    )
    _save_fsm(fsm)

    return {
        "operation_id": operation_id,
        "status": "rolled_back",
        "cleaned_clouds": cleaned_clouds
    }
