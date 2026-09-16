from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Sum, Case, When, BigIntegerField
import logging
import uuid
from math import ceil

from payments.models import Subscription
from .models import File
from .serializers import FileSerializer

# ========= AWS =========
from clouds.aws import (
    generate_aws_upload_url,
    generate_aws_download_url,
    delete_file_from_s3,
    start_multipart_upload,
    generate_part_upload_url,
    complete_multipart_upload,
    generate_presigned_multipart_urls,
    server_side_upload_aws,
)

# ========= AZURE =========
from clouds.azure import (
    generate_azure_upload_url,
    generate_azure_download_url,
    delete_file_from_azure,
    generate_block_upload_url,
    commit_block_list,
    generate_presigned_block_urls,
    server_side_upload_azure,
)

# ========= GCP =========
from clouds.gcp import (
    generate_gcp_upload_url,
    generate_gcp_download_url,
    delete_file_from_gcp,
    start_resumable_upload,
    generate_presigned_resumable_url,
    server_side_upload_gcp,
)

logger = logging.getLogger(__name__)

ALLOWED_CLOUDS = {"AWS", "AZURE", "GCP"}
DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB


# ==========================================
# HELPERS
# ==========================================

def _parse_chunk_size(raw_value, default=DEFAULT_CHUNK_SIZE):
    """
    Parses chunk_size from a request field.
    Returns an integer in bytes. Raises ValueError on invalid input.
    """
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        raise ValueError("chunk_size must be a positive integer (bytes)")
    if value <= 0:
        raise ValueError("chunk_size must be greater than 0")
    return value


# ==========================================
# FILE LIST
# ==========================================
class FileListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            files = File.objects.filter(user=request.user).order_by("-created_at")
            serializer = FileSerializer(files, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(str(e))
            return Response(
                {"error": "Failed to fetch files"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================
# PRESIGN UPLOAD (app path — existing logic unchanged)
# ==========================================
class PresignUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_name = request.data.get("file_name")
        file_size = request.data.get("file_size")
        file_type = request.data.get("file_type")
        clouds = request.data.get("clouds", [])

        if not file_name or not file_size or not file_type or not clouds:
            return Response(
                {"error": "file_name, file_size, file_type and clouds are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_size = int(file_size)
        except Exception:
            return Response({"error": "Invalid file_size"}, status=400)

        MAX_FILE_SIZE_MB_DEFAULT = 100
        MAX_FILE_SIZE_MB_EXEMPT = 51200
        user = request.user

        if user.email == "charansairamisetti@gmail.com":
            max_size_mb = MAX_FILE_SIZE_MB_EXEMPT
        else:
            max_size_mb = MAX_FILE_SIZE_MB_DEFAULT

        if file_size > max_size_mb * 1024 * 1024:
            return Response(
                {"error": f"File size exceeds {max_size_mb} MB limit"},
                status=status.HTTP_403_FORBIDDEN,
            )

        clouds = [c.upper() for c in clouds]
        invalid = set(clouds) - ALLOWED_CLOUDS
        if invalid:
            return Response(
                {"error": f"Invalid clouds: {', '.join(invalid)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription, _ = Subscription.objects.get_or_create(
            user=request.user,
            defaults={"plan": "FREE", "cloud_limit_mb": 1024, "max_file_size_mb": 100},
        )
        cloud_limit_bytes = subscription.cloud_limit_mb * 1024 * 1024

        usage_totals = File.objects.filter(user=request.user).aggregate(
            aws_total=Sum(
                Case(When(aws_path__isnull=False, then="file_size"), output_field=BigIntegerField())
            ),
            azure_total=Sum(
                Case(When(azure_path__isnull=False, then="file_size"), output_field=BigIntegerField())
            ),
            gcp_total=Sum(
                Case(When(gcp_path__isnull=False, then="file_size"), output_field=BigIntegerField())
            ),
        )
        cloud_usage = {
            "AWS":   usage_totals["aws_total"]   or 0,
            "AZURE": usage_totals["azure_total"] or 0,
            "GCP":   usage_totals["gcp_total"]   or 0,
        }

        for cloud in clouds:
            used = cloud_usage[cloud]
            if used + file_size > cloud_limit_bytes:
                return Response(
                    {
                        "error": f"{cloud} storage limit exceeded",
                        "used_mb": used // (1024 * 1024),
                        "limit_mb": subscription.cloud_limit_mb,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        chunk_size = DEFAULT_CHUNK_SIZE
        upload_urls = {}
        paths = {}
        upload_type = "single" if file_size <= chunk_size else "multipart"

        if upload_type == "single":
            if "AWS" in clouds:
                key, url = generate_aws_upload_url(request.user.id, file_name, file_type)
                upload_urls["AWS"] = url
                paths["aws_path"] = key
            if "AZURE" in clouds:
                key, url = generate_azure_upload_url(request.user.id, file_name)
                upload_urls["AZURE"] = url
                paths["azure_path"] = key
            if "GCP" in clouds:
                key, url = generate_gcp_upload_url(request.user.id, file_name)
                upload_urls["GCP"] = url
                paths["gcp_path"] = key

            return Response(
                {"upload_type": "single", "upload_urls": upload_urls, "paths": paths},
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "upload_type": "multipart",
                "chunk_size": chunk_size,
                "message": "Use multipart endpoints",
            },
            status=status.HTTP_200_OK,
        )


# ==========================================
# MULTIPART START (app path — unchanged)
# ==========================================
class MultipartStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_name = request.data.get("file_name")
        file_type = request.data.get("file_type")
        file_size = request.data.get("file_size")   # required for GCP session locking
        cloud = request.data.get("cloud")

        if not file_name or not cloud:
            return Response({"error": "file_name and cloud required"}, status=400)

        cloud = cloud.upper()

        try:
            if cloud == "AWS":
                key, upload_id = start_multipart_upload(request.user.id, file_name, file_type)
                return Response({"key": key, "upload_id": upload_id})

            if cloud == "GCP":
                blob, session = start_resumable_upload(request.user.id, file_name, file_type, file_size)
                return Response({"blob_name": blob, "upload_url": session})

            if cloud == "AZURE":
                blob_name = f"users/{request.user.id}/{uuid.uuid4()}_{file_name}"
                return Response({"blob_name": blob_name})

        except Exception as e:
            logger.error(str(e))
            return Response({"error": "Multipart start failed"}, status=500)


# ==========================================
# MULTIPART PRESIGN PART (app path — unchanged)
# ==========================================
class MultipartPresignPartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cloud = request.data.get("cloud")
        if not cloud:
            return Response({"error": "cloud required"}, status=400)

        cloud = cloud.upper()

        try:
            if cloud == "AWS":
                key = request.data.get("key")
                upload_id = request.data.get("upload_id")
                part_number = request.data.get("part_number")
                if not key or not upload_id or not part_number:
                    return Response({"error": "key, upload_id and part_number required"}, status=400)
                url = generate_part_upload_url(key, upload_id, part_number)
                return Response({"url": url})

            if cloud == "AZURE":
                blob_name = request.data.get("blob_name")
                block_id = request.data.get("block_id")
                if not blob_name or not block_id:
                    return Response({"error": "blob_name and block_id required"}, status=400)
                url = generate_block_upload_url(blob_name, block_id)
                return Response({"url": url})

            if cloud == "GCP":
                return Response({"error": "GCP does not use presigned parts"}, status=400)

        except Exception as e:
            logger.error(str(e))
            return Response({"error": "Failed generating part upload url"}, status=500)


# ==========================================
# MULTIPART COMPLETE (app path — unchanged)
# ==========================================
class MultipartCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cloud = request.data.get("cloud")
        if not cloud:
            return Response({"error": "cloud required"}, status=400)

        cloud = cloud.upper()

        try:
            if cloud == "AWS":
                key = request.data.get("key")
                upload_id = request.data.get("upload_id")
                parts = request.data.get("parts")
                parts = sorted(parts, key=lambda p: p["PartNumber"])
                complete_multipart_upload(key, upload_id, parts)
                return Response({"message": "AWS multipart complete"})

            if cloud == "AZURE":
                blob_name = request.data.get("blob_name")
                blocks = request.data.get("blocks")
                commit_block_list(blob_name, blocks)
                return Response({"message": "Azure upload complete"})

            if cloud == "GCP":
                return Response({"message": "GCP upload complete"})

        except Exception as e:
            logger.error(str(e))
            return Response({"error": "Multipart completion failed"}, status=500)


# ==========================================
# DOWNLOAD (app path — unchanged)
# ==========================================
class PresignDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        try:
            file = File.objects.get(id=file_id, user=request.user)
        except File.DoesNotExist:
            return Response({"error": "File not found"}, status=404)

        try:
            if file.aws_path:
                url = generate_aws_download_url(file.aws_path)
            elif file.azure_path:
                url = generate_azure_download_url(file.azure_path)
            elif file.gcp_path:
                url = generate_gcp_download_url(file.gcp_path)
            else:
                return Response({"error": "File not available in any cloud"}, status=400)

        except Exception as e:
            logger.error(str(e))
            return Response({"error": "Failed to generate download URL"}, status=500)

        return Response({"download_url": url})


# ==========================================
# DELETE FILE (app path — unchanged)
# ==========================================
class FileDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, file_id):
        try:
            file = File.objects.get(id=file_id, user=request.user)
        except File.DoesNotExist:
            return Response({"error": "File not found"}, status=404)

        clouds = request.data.get("clouds") or ["AWS", "AZURE", "GCP"]
        clouds = [c.upper() for c in clouds]

        if "AWS" in clouds and file.aws_path:
            delete_file_from_s3(file.aws_path)
            file.aws_path = None

        if "AZURE" in clouds and file.azure_path:
            delete_file_from_azure(file.azure_path)
            file.azure_path = None

        if "GCP" in clouds and file.gcp_path:
            delete_file_from_gcp(file.gcp_path)
            file.gcp_path = None

        if not any([file.aws_path, file.azure_path, file.gcp_path]):
            file.delete()
            return Response({"message": "File deleted from all clouds"}, status=200)

        file.save()
        return Response({"message": "File deleted from selected clouds"}, status=200)


# ==========================================
# CONFIRM UPLOAD (app path — unchanged)
# ==========================================
class ConfirmUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_name = request.data.get("file_name")
        file_size = request.data.get("file_size")

        if not file_name or not file_size:
            return Response(
                {"error": "file_name and file_size are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file = File.objects.create(
                user=request.user,
                file_name=file_name,
                file_size=int(file_size),
                aws_path=request.data.get("aws_path"),
                azure_path=request.data.get("azure_path"),
                gcp_path=request.data.get("gcp_path"),
            )
        except Exception as e:
            logger.error(str(e))
            return Response(
                {"error": "Failed to save file metadata"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"file_id": file.id, "message": "Upload verified and saved"},
            status=status.HTTP_201_CREATED,
        )


# ==========================================
# BENCHMARK — PRESIGNED MULTIPART URLS
# POST /api/files/benchmark/presign/aws/
# POST /api/files/benchmark/presign/azure/
# POST /api/files/benchmark/presign/gcp/
#
# Input:  { file_size: int, chunk_size: int (optional, default 10MB) }
# Output: { upload_id, chunk_size, total_parts, presigned_urls: [...] }
# ==========================================

class BenchmarkPresignAWSView(APIView):
    """
    Benchmark presigned upload endpoint for AWS S3.

    Accepts file_size and chunk_size, calculates total_parts, and returns
    presigned PUT URLs for every part. The benchmark client uploads each
    part directly to S3 then calls complete_multipart_upload separately.

    No authentication required so the benchmark script can call it freely.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        file_size = request.data.get("file_size")
        raw_chunk_size = request.data.get("chunk_size")
        file_name = request.data.get("file_name", "benchmark_file")
        file_type = request.data.get("file_type", "application/octet-stream")

        if file_size is None:
            return Response({"error": "file_size is required"}, status=400)

        try:
            file_size = int(file_size)
            chunk_size = _parse_chunk_size(raw_chunk_size)
        except (ValueError, TypeError) as e:
            return Response({"error": str(e)}, status=400)

        if file_size <= 0:
            return Response({"error": "file_size must be greater than 0"}, status=400)

        try:
            result = generate_presigned_multipart_urls(
                user_id="benchmark",
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                chunk_size=chunk_size,
            )
            return Response(result, status=200)

        except RuntimeError as e:
            logger.error(f"BenchmarkPresignAWSView error: {str(e)}")
            return Response({"error": str(e)}, status=500)


class BenchmarkPresignAzureView(APIView):
    """
    Benchmark presigned upload endpoint for Azure Blob Storage.

    Returns per-block SAS URLs using Azure's Put Block + Put Block List pattern.
    The benchmark client must PUT each block then call the commit endpoint.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        file_size = request.data.get("file_size")
        raw_chunk_size = request.data.get("chunk_size")
        file_name = request.data.get("file_name", "benchmark_file")

        if file_size is None:
            return Response({"error": "file_size is required"}, status=400)

        try:
            file_size = int(file_size)
            chunk_size = _parse_chunk_size(raw_chunk_size)
        except (ValueError, TypeError) as e:
            return Response({"error": str(e)}, status=400)

        if file_size <= 0:
            return Response({"error": "file_size must be greater than 0"}, status=400)

        try:
            result = generate_presigned_block_urls(
                user_id="benchmark",
                file_name=file_name,
                file_size=file_size,
                chunk_size=chunk_size,
            )
            return Response(result, status=200)

        except RuntimeError as e:
            logger.error(f"BenchmarkPresignAzureView error: {str(e)}")
            return Response({"error": str(e)}, status=500)


class BenchmarkPresignGCPView(APIView):
    """
    Benchmark presigned upload endpoint for Google Cloud Storage.

    Returns a single resumable upload session URI. The benchmark client
    streams the file in chunks using Content-Range headers.
    chunk_size is aligned to the nearest 256 KiB (GCS requirement).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        file_size = request.data.get("file_size")
        raw_chunk_size = request.data.get("chunk_size")
        file_name = request.data.get("file_name", "benchmark_file")

        if file_size is None:
            return Response({"error": "file_size is required"}, status=400)

        try:
            file_size = int(file_size)
            chunk_size = _parse_chunk_size(raw_chunk_size)
        except (ValueError, TypeError) as e:
            return Response({"error": str(e)}, status=400)

        if file_size <= 0:
            return Response({"error": "file_size must be greater than 0"}, status=400)

        try:
            result = generate_presigned_resumable_url(
                user_id="benchmark",
                file_name=file_name,
                file_size=file_size,
                chunk_size=chunk_size,
            )
            return Response(result, status=200)

        except RuntimeError as e:
            logger.error(f"BenchmarkPresignGCPView error: {str(e)}")
            return Response({"error": str(e)}, status=500)


# ==========================================
# BENCHMARK — SERVER-SIDE UPLOADS
# POST /api/files/upload/server/aws/
# POST /api/files/upload/server/azure/
# POST /api/files/upload/server/gcp/
#
# Input:  multipart/form-data { file: <binary>, chunk_size: int (optional) }
# Output: { provider, method, file_size, chunk_size, upload_time_seconds }
# ==========================================

class ServerUploadAWSView(APIView):
    """
    Server-side upload benchmark endpoint for AWS S3.

    Receives the file as a multipart POST, streams it to S3 via boto3
    upload_fileobj() with TransferConfig(multipart_chunksize=chunk_size).
    Returns total upload time in seconds.
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        raw_chunk_size = request.data.get("chunk_size")

        if file_obj is None:
            return Response({"error": "file is required"}, status=400)

        try:
            chunk_size = _parse_chunk_size(raw_chunk_size)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        try:
            elapsed, key = server_side_upload_aws(
                file_obj=file_obj,
                file_name=file_obj.name,
                chunk_size=chunk_size,
            )
            return Response(
                {
                    "provider": "AWS",
                    "method": "server",
                    "file_size": file_obj.size,
                    "chunk_size": chunk_size,
                    "upload_time_seconds": round(elapsed, 6),
                },
                status=200,
            )

        except RuntimeError as e:
            logger.error(f"ServerUploadAWSView error: {str(e)}")
            return Response({"error": str(e)}, status=500)


class ServerUploadAzureView(APIView):
    """
    Server-side upload benchmark endpoint for Azure Blob Storage.

    Receives the file as a multipart POST, streams it to Azure via
    upload_blob() with max_single_put_size=chunk_size to force the block
    upload path. Returns total upload time in seconds.
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        raw_chunk_size = request.data.get("chunk_size")

        if file_obj is None:
            return Response({"error": "file is required"}, status=400)

        try:
            chunk_size = _parse_chunk_size(raw_chunk_size)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        try:
            elapsed, blob_name = server_side_upload_azure(
                file_obj=file_obj,
                file_name=file_obj.name,
                chunk_size=chunk_size,
            )
            return Response(
                {
                    "provider": "AZURE",
                    "method": "server",
                    "file_size": file_obj.size,
                    "chunk_size": chunk_size,
                    "upload_time_seconds": round(elapsed, 6),
                },
                status=200,
            )

        except RuntimeError as e:
            logger.error(f"ServerUploadAzureView error: {str(e)}")
            return Response({"error": str(e)}, status=500)


class ServerUploadGCPView(APIView):
    """
    Server-side upload benchmark endpoint for Google Cloud Storage.

    Receives the file as a multipart POST, streams it to GCS via
    blob.upload_from_file() with blob.chunk_size=aligned_chunk_size.
    Returns total upload time in seconds.
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        raw_chunk_size = request.data.get("chunk_size")

        if file_obj is None:
            return Response({"error": "file is required"}, status=400)

        try:
            chunk_size = _parse_chunk_size(raw_chunk_size)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        try:
            elapsed, blob_name = server_side_upload_gcp(
                file_obj=file_obj,
                file_name=file_obj.name,
                chunk_size=chunk_size,
            )
            return Response(
                {
                    "provider": "GCP",
                    "method": "server",
                    "file_size": file_obj.size,
                    "chunk_size": chunk_size,
                    "upload_time_seconds": round(elapsed, 6),
                },
                status=200,
            )

        except RuntimeError as e:
            logger.error(f"ServerUploadGCPView error: {str(e)}")
            return Response({"error": str(e)}, status=500)