from django.contrib.admin import AdminSite
from django.db.models import Sum
from django.utils.timezone import now

from accounts.models import User
from files.models import File
from payments.models import Subscription, Payment


class TriCloudAdminSite(AdminSite):

    site_header = "TriCloud Vault Admin"
    site_title = "TriCloud Vault"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):

        # -----------------------------
        # USERS
        # -----------------------------
        total_users = User.objects.count()

        # -----------------------------
        # PREMIUM USERS
        # -----------------------------
        premium_users = Subscription.objects.filter(
            plan="PRO"
        ).count()

        # -----------------------------
        # TOTAL STORAGE USED
        # -----------------------------
        storage_bytes = File.objects.aggregate(
            total=Sum("file_size")
        )["total"] or 0

        storage_gb = round(storage_bytes / (1024 ** 3), 2)

        # -----------------------------
        # TOTAL REVENUE
        # -----------------------------
        total_revenue = Payment.objects.filter(
            status="SUCCESS"
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        # -----------------------------
        # UPLOADS TODAY
        # -----------------------------
        uploads_today = File.objects.filter(
            created_at__date=now().date()
        ).count()

        # -----------------------------
        # AWS STORAGE
        # -----------------------------
        aws_bytes = File.objects.exclude(
            aws_path__isnull=True
        ).exclude(
            aws_path=""
        ).aggregate(total=Sum("file_size"))["total"] or 0

        aws_storage = round(aws_bytes / (1024 ** 3), 2)

        # -----------------------------
        # AZURE STORAGE
        # -----------------------------
        azure_bytes = File.objects.exclude(
            azure_path__isnull=True
        ).exclude(
            azure_path=""
        ).aggregate(total=Sum("file_size"))["total"] or 0

        azure_storage = round(azure_bytes / (1024 ** 3), 2)

        # -----------------------------
        # GCP STORAGE
        # -----------------------------
        gcp_bytes = File.objects.exclude(
            gcp_path__isnull=True
        ).exclude(
            gcp_path=""
        ).aggregate(total=Sum("file_size"))["total"] or 0

        gcp_storage = round(gcp_bytes / (1024 ** 3), 2)

        extra_context = extra_context or {}

        extra_context.update({
            "total_users": total_users,
            "premium_users": premium_users,
            "total_storage": storage_gb,
            "total_revenue": total_revenue,
            "uploads_today": uploads_today,
            "aws_storage": aws_storage,
            "azure_storage": azure_storage,
            "gcp_storage": gcp_storage,
        })

        return super().index(request, extra_context)


admin_site = TriCloudAdminSite(name="admin")