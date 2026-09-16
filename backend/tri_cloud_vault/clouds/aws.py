import boto3
import os
import uuid
import time
import logging
from math import ceil
from botocore.exceptions import ClientError, BotoCoreError
from boto3.s3.transfer import TransferConfig

logger = logging.getLogger(__name__)

AWS_BUCKET = os.getenv("AWS_S3_BUCKET_NAME")

# Create S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "ap-south-1"),
    config=boto3.session.Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"}),
)

DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB


# Generate upload URL
def generate_aws_upload_url(user_id, file_name, file_type):
    try:
        key = f"users/{user_id}/{uuid.uuid4()}_{file_name}"
        url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": AWS_BUCKET, "Key": key, "ContentType": file_type},
            ExpiresIn=3600,
        )
        return key, url
    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS upload url error: {str(e)}")
        raise RuntimeError("AWS upload URL generation failed")


# Generate download URL
def generate_aws_download_url(object_key):
    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": AWS_BUCKET, "Key": object_key},
            ExpiresIn=3600,
        )
    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS download error: {str(e)}")
        raise RuntimeError("AWS download URL generation failed")


# Delete file
def delete_file_from_s3(object_key):
    try:
        s3.delete_object(Bucket=AWS_BUCKET, Key=object_key)
    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS delete error: {str(e)}")
        raise RuntimeError("AWS delete failed")


# Start multipart upload
def start_multipart_upload(user_id, file_name, file_type):
    try:
        key = f"users/{user_id}/{uuid.uuid4()}_{file_name}"
        response = s3.create_multipart_upload(
            Bucket=AWS_BUCKET,
            Key=key,
            ContentType=file_type,
        )
        return key, response["UploadId"]
    except Exception as e:
        logger.error(f"AWS multipart start error: {str(e)}")
        raise RuntimeError("AWS multipart start failed")


# Generate part URL
def generate_part_upload_url(key, upload_id, part_number):
    try:
        return s3.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": AWS_BUCKET,
                "Key": key,
                "UploadId": upload_id,
                "PartNumber": part_number,
            },
            ExpiresIn=3600,
        )
    except Exception as e:
        logger.error(f"AWS part URL error: {str(e)}")
        raise RuntimeError("AWS multipart part url failed")


# Complete multipart upload
def complete_multipart_upload(key, upload_id, parts):
    try:
        s3.complete_multipart_upload(
            Bucket=AWS_BUCKET,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts},
        )
    except Exception as e:
        logger.error(f"AWS multipart complete error: {str(e)}")
        raise RuntimeError("AWS multipart completion failed")


# Generate presigned multipart URLs
def generate_presigned_multipart_urls(user_id, file_name, file_type, file_size, chunk_size=DEFAULT_CHUNK_SIZE):
    try:
        total_parts = ceil(file_size / chunk_size)
        key = f"benchmark/{user_id}/{uuid.uuid4()}_{file_name}"

        response = s3.create_multipart_upload(
            Bucket=AWS_BUCKET,
            Key=key,
            ContentType=file_type,
        )
        upload_id = response["UploadId"]

        presigned_urls = []
        for part_number in range(1, total_parts + 1):
            url = s3.generate_presigned_url(
                "upload_part",
                Params={
                    "Bucket": AWS_BUCKET,
                    "Key": key,
                    "UploadId": upload_id,
                    "PartNumber": part_number,
                },
                ExpiresIn=3600,
            )
            presigned_urls.append({"part_number": part_number, "url": url})

        return {
            "key": key,
            "upload_id": upload_id,
            "chunk_size": chunk_size,
            "total_parts": total_parts,
            "presigned_urls": presigned_urls,
        }

    except Exception as e:
        logger.error(f"AWS presigned multipart error: {str(e)}")
        raise RuntimeError("AWS presigned multipart URL generation failed")


# Server-side upload
def server_side_upload_aws(file_obj, file_name, chunk_size=DEFAULT_CHUNK_SIZE):
    try:
        key = f"benchmark/server/{uuid.uuid4()}_{file_name}"

        config = TransferConfig(
            multipart_chunksize=chunk_size,
            multipart_threshold=chunk_size,
            use_threads=True,
        )

        start = time.perf_counter()
        s3.upload_fileobj(file_obj, AWS_BUCKET, key, Config=config)
        elapsed = time.perf_counter() - start

        return elapsed, key

    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS server-side upload error: {str(e)}")
        raise RuntimeError(f"AWS server-side upload failed: {str(e)}")