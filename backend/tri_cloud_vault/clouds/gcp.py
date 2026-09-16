import os
import uuid
import time
import logging
from math import ceil
from datetime import timedelta

from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB

# Initialize GCP storage client
client = storage.Client()
bucket = client.bucket(os.getenv("GCP_BUCKET_NAME"))


# Generate upload signed URL
def generate_gcp_upload_url(user_id, file_name, file_type=None):
    # GCS signs content-type into the URL. We always sign as
    # "application/octet-stream" regardless of the actual file type so the
    # frontend can send a fixed Content-Type header that always matches.
    # The frontend wraps the File in Blob({type:"application/octet-stream"})
    # to prevent the browser from overriding the header with the real MIME type.
    try:
        blob_name = f"users/{user_id}/{uuid.uuid4()}_{file_name}"
        blob = bucket.blob(blob_name)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
            content_type="application/octet-stream",
        )

        return blob_name, url

    except GoogleAPIError as e:
        logger.error(str(e))
        raise RuntimeError("GCP upload url generation failed")


# Generate download signed URL
def generate_gcp_download_url(blob_name):
    try:
        blob = bucket.blob(blob_name)

        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET",
        )

    except GoogleAPIError as e:
        logger.error(str(e))
        raise RuntimeError("GCP download url generation failed")


# Delete file from bucket
def delete_file_from_gcp(blob_name):
    try:
        blob = bucket.blob(blob_name)
        blob.delete()

    except GoogleAPIError as e:
        logger.error(str(e))
        raise RuntimeError("GCP delete failed")


# Start resumable upload session
def start_resumable_upload(user_id, file_name, file_type, file_size=None):
    # Uses generate_signed_url(method="RESUMABLE") which produces an XML API
    # session URL (storage.googleapis.com/{bucket}/{object}?upload_id=...).
    # This respects bucket-level CORS rules, unlike create_resumable_upload_session()
    # which produces a JSON API URL (/upload/storage/v1/...) that ignores CORS config.
    # The browser POSTs to this signed URL to initiate the session, then PUTs chunks.
    try:
        blob_name = f"users/{user_id}/{uuid.uuid4()}_{file_name}"
        blob = bucket.blob(blob_name)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="RESUMABLE",
            content_type="application/octet-stream",
        )

        return blob_name, url

    except GoogleAPIError as e:
        logger.error(str(e))
        raise RuntimeError("GCP resumable upload start failed")


# Generate presigned resumable URL for benchmark
def generate_presigned_resumable_url(user_id, file_name, file_size, chunk_size=DEFAULT_CHUNK_SIZE):
    try:
        aligned_chunk_size = _align_chunk_size(chunk_size)
        total_parts = ceil(file_size / aligned_chunk_size)

        blob_name = f"benchmark/{user_id}/{uuid.uuid4()}_{file_name}"
        blob = bucket.blob(blob_name)

        # Set chunk size for resumable upload
        blob.chunk_size = aligned_chunk_size

        session_uri = blob.create_resumable_upload_session(
            content_type="application/octet-stream",
            size=file_size,
        )

        logger.info(
            f"GCP presigned resumable upload: blob={blob_name}, parts={total_parts}, chunk_size={aligned_chunk_size}"
        )

        return {
            "blob_name": blob_name,
            "upload_id": session_uri,
            "chunk_size": aligned_chunk_size,
            "total_parts": total_parts,
            "presigned_urls": [
                {"part_number": 1, "url": session_uri}
            ],
        }

    except GoogleAPIError as e:
        logger.error(f"GCP presigned resumable URL error: {str(e)}")
        raise RuntimeError("GCP presigned resumable URL generation failed")


# Server-side upload using resumable upload
def server_side_upload_gcp(file_obj, file_name, chunk_size=DEFAULT_CHUNK_SIZE):
    try:
        blob_name = f"benchmark/server/{uuid.uuid4()}_{file_name}"
        blob = bucket.blob(blob_name)

        # Align chunk size to GCP requirement
        aligned_chunk_size = _align_chunk_size(chunk_size)
        blob.chunk_size = aligned_chunk_size

        logger.info(
            f"GCP server upload start: blob={blob_name}, chunk_size={aligned_chunk_size}"
        )

        start = time.perf_counter()

        blob.upload_from_file(
            file_obj,
            content_type="application/octet-stream"
        )

        elapsed = time.perf_counter() - start

        logger.info(
            f"GCP server upload complete: blob={blob_name}, time={elapsed:.3f}s"
        )

        return elapsed, blob_name

    except GoogleAPIError as e:
        logger.error(f"GCP server-side upload error: {str(e)}")
        raise RuntimeError(f"GCP server-side upload failed: {str(e)}")


# Align chunk size to 256KB multiple (GCP requirement)
def _align_chunk_size(chunk_size):
    min_block = 256 * 1024  # 256KB
    remainder = chunk_size % min_block

    if remainder == 0:
        return chunk_size

    aligned = chunk_size + (min_block - remainder)

    logger.debug(
        f"GCP chunk_size {chunk_size} aligned to {aligned}"
    )

    return aligned