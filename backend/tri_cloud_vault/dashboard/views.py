from django.db.models import Sum, Case, When, BigIntegerField
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from files.models import File
from payments.models import Subscription


class StorageSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            subscription, _ = Subscription.objects.get_or_create(
                user=user,
                defaults={
                    "plan": "FREE",
                    "cloud_limit_mb": 1024,   # 1 GB
                    "max_file_size_mb": 100
                }
            )

            limit_mb = subscription.cloud_limit_mb

            # Single query with conditional aggregation — replaces 3 separate aggregate queries
            totals = File.objects.filter(user=user).aggregate(
                aws_total=Sum(
                    Case(
                        When(aws_path__isnull=False, then="file_size"),
                        output_field=BigIntegerField(),
                    )
                ),
                azure_total=Sum(
                    Case(
                        When(azure_path__isnull=False, then="file_size"),
                        output_field=BigIntegerField(),
                    )
                ),
                gcp_total=Sum(
                    Case(
                        When(gcp_path__isnull=False, then="file_size"),
                        output_field=BigIntegerField(),
                    )
                ),
            )

            aws_used   = totals["aws_total"]   or 0
            azure_used = totals["azure_total"] or 0
            gcp_used   = totals["gcp_total"]   or 0

        except Exception as e:
            return Response(
                {"error": "Failed to calculate storage usage"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "aws": {
                "used_mb": round(aws_used / (1024 * 1024), 2),
                "limit_mb": limit_mb
            },
            "azure": {
                "used_mb": round(azure_used / (1024 * 1024), 2),
                "limit_mb": limit_mb
            },
            "gcp": {
                "used_mb": round(gcp_used / (1024 * 1024), 2),
                "limit_mb": limit_mb
            }
        })


class RecentFilesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            files = (
                File.objects
                .filter(user=user)
                .only("id", "file_name", "file_size", "created_at",
                      "aws_path", "azure_path", "gcp_path")
                .order_by("-created_at")[:5]
            )
        except Exception:
            return Response(
                {"error": "Failed to fetch recent files"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        data = []

        for f in files:
            try:
                clouds = []
                if f.aws_path:
                    clouds.append("AWS")
                if f.azure_path:
                    clouds.append("Azure")
                if f.gcp_path:
                    clouds.append("GCP")

                data.append({
                    "id": f.id,
                    "file_name": f.file_name,
                    "size_mb": round((f.file_size or 0) / (1024 * 1024), 2),
                    "uploaded_at": f.created_at,
                    "clouds": clouds
                })
            except Exception:
                # Skip corrupted record, do not crash whole response
                continue

        return Response(data)


class FolderSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            # .only() avoids fetching cloud path columns (512 chars each × 3) for every row —
            # this view only needs file_name and file_size for its grouping logic
            files = (
                File.objects
                .filter(user=user)
                .only("file_name", "file_size")
            )
        except Exception:
            return Response(
                {"error": "Failed to fetch files"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        folders = {
            "Documents": ["pdf", "doc", "docx", "txt", "xlsx"],
            "Images": ["jpg", "jpeg", "png", "gif"],
            "Videos": ["mp4", "mkv", "avi"],
        }

        result = {
            "Documents": {"count": 0, "size": 0},
            "Images": {"count": 0, "size": 0},
            "Videos": {"count": 0, "size": 0},
            "Others": {"count": 0, "size": 0},
        }

        for f in files:
            try:
                ext = f.file_name.rsplit(".", 1)[-1].lower() if "." in f.file_name else ""
                matched = False

                for folder, exts in folders.items():
                    if ext in exts:
                        result[folder]["count"] += 1
                        result[folder]["size"] += f.file_size or 0
                        matched = True
                        break

                if not matched:
                    result["Others"]["count"] += 1
                    result["Others"]["size"] += f.file_size or 0

            except Exception:
                # Skip malformed file entry
                continue

        response = []
        for name, data in result.items():
            response.append({
                "name": name,
                "count": data["count"],
                "size_mb": round(data["size"] / (1024 * 1024), 2)
            })

        return Response(response)