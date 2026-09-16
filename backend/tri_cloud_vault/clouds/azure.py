import base64
from azure.storage.blob import (
    BlobServiceClient,
    BlobBlock,
    generate_blob_sas,
    BlobSasPermissions,
)
from azure.core.exceptions import AzureError
from datetime import datetime, timedelta
import os
import uuid
import time
import urllib.parse
import logging
from math import ceil

logger = logging.getLogger(__name__)

ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
CONTAINER = os.getenv("AZURE_CONTAINER_NAME")

DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB

# Initialize Azure Blob service client
service = BlobServiceClient(
    account_url=f"https://{ACCOUNT_NAME}.blob.core.windows.net",
    credential=ACCOUNT_KEY,
)


# Generate upload SAS URL
def generate_azure_upload_url(user_id, file_name):
    try:
        blob_name = f"users/{user_id}/{uuid.uuid4()}_{file_name}"
        sas = generate_blob_sas(
            account_name=ACCOUNT_NAME,
            container_name=CONTAINER,
            blob_name=blob_name,
            account_key=ACCOUNT_KEY,
            permission=BlobSasPermissions(write=True),
            expiry=datetime.utcnow() + timedelta(hours=1),
        )
        url = f"https://{ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER}/{blob_name}?{sas}"
        return blob_name, url
    except AzureError as e:
        logger.error(str(e))
        raise RuntimeError("Azure upload url generation failed")


# Generate download SAS URL
def generate_azure_download_url(blob_name):
    try:
        sas = generate_blob_sas(
            account_name=ACCOUNT_NAME,
            container_name=CONTAINER,
            blob_name=blob_name,
            account_key=ACCOUNT_KEY,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1),
        )
        return f"https://{ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER}/{blob_name}?{sas}"
    except AzureError as e:
        logger.error(str(e))
        raise RuntimeError("Azure download failed")


# Delete blob from container
def delete_file_from_azure(blob_name):
    try:
        blob_client = service.get_blob_client(container=CONTAINER, blob=blob_name)
        blob_client.delete_blob()
    except AzureError as e:
        logger.error(str(e))
        raise RuntimeError("Azure delete failed")


# Generate URL for uploading a block
def generate_block_upload_url(blob_name, block_id):
    try:
        encoded_block_id = urllib.parse.quote(block_id, safe="")
        sas = generate_blob_sas(
            account_name=ACCOUNT_NAME,
            container_name=CONTAINER,
            blob_name=blob_name,
            account_key=ACCOUNT_KEY,
            permission=BlobSasPermissions(write=True),
            expiry=datetime.utcnow() + timedelta(hours=1),
        )
        return (
            f"https://{ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER}/"
            f"{blob_name}?comp=block&blockid={encoded_block_id}&{sas}"
        )
    except AzureError as e:
        logger.error(str(e))
        raise RuntimeError("Azure block upload url failed")


# Commit uploaded blocks to finalize blob
def commit_block_list(blob_name, block_ids):
    try:
        logger.info(f"Committing blocks for {blob_name}: {block_ids}")

        blob = service.get_blob_client(CONTAINER, blob_name)

        # Decode block IDs before committing
        blocks = [
            BlobBlock(block_id=base64.b64decode(block_id).decode())
            for block_id in block_ids
        ]

        blob.commit_block_list(blocks)

    except AzureError as e:
        logger.error(str(e))
        raise RuntimeError("Azure block commit failed")


# Generate all block URLs upfront for benchmarking
def generate_presigned_block_urls(user_id, file_name, file_size, chunk_size=DEFAULT_CHUNK_SIZE):
    try:
        total_parts = ceil(file_size / chunk_size)
        blob_name = f"benchmark/{user_id}/{uuid.uuid4()}_{file_name}"

        sas = generate_blob_sas(
            account_name=ACCOUNT_NAME,
            container_name=CONTAINER,
            blob_name=blob_name,
            account_key=ACCOUNT_KEY,
            permission=BlobSasPermissions(write=True),
            expiry=datetime.utcnow() + timedelta(hours=2),
        )

        presigned_urls = []
        block_ids = []

        for i in range(total_parts):
            plain_id = f"{i:06d}"  # zero-padded block id
            block_id_b64 = base64.b64encode(plain_id.encode()).decode()
            encoded_block_id = urllib.parse.quote(block_id_b64, safe="")

            url = (
                f"https://{ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER}/"
                f"{blob_name}?comp=block&blockid={encoded_block_id}&{sas}"
            )

            presigned_urls.append({
                "part_number": i + 1,
                "block_id": block_id_b64,
                "url": url,
            })

            block_ids.append(block_id_b64)

        logger.info(
            f"Azure presigned block upload: blob={blob_name}, parts={total_parts}, chunk_size={chunk_size}"
        )

        return {
            "blob_name": blob_name,
            "chunk_size": chunk_size,
            "total_parts": total_parts,
            "block_ids": block_ids,
            "presigned_urls": presigned_urls,
        }

    except AzureError as e:
        logger.error(f"Azure presigned block URL error: {str(e)}")
        raise RuntimeError("Azure presigned block URL generation failed")


# Server-side upload using chunked blocks
def server_side_upload_azure(file_obj, file_name, chunk_size=DEFAULT_CHUNK_SIZE):
    try:
        blob_name = f"benchmark/server/{uuid.uuid4()}_{file_name}"
        blob_client = service.get_blob_client(container=CONTAINER, blob=blob_name)

        start = time.perf_counter()

        blob_client.upload_blob(
            file_obj,
            overwrite=True,
            max_concurrency=4,
            max_single_put_size=chunk_size,
        )

        elapsed = time.perf_counter() - start

        logger.info(
            f"Azure server upload done: blob={blob_name}, time={elapsed:.3f}s"
        )

        return elapsed, blob_name

    except AzureError as e:
        logger.error(f"Azure server-side upload error: {str(e)}")
        raise RuntimeError(f"Azure server-side upload failed: {str(e)}")