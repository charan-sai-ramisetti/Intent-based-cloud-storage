from django.conf import settings
from django.db import models


class File(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="files"
    )

    file_name = models.CharField(max_length=255)

    file_size = models.BigIntegerField(
        null=True,
        blank=True
    )

    # cloud locations (nullable → user may not choose all)
    aws_path = models.CharField(max_length=512, null=True, blank=True)
    azure_path = models.CharField(max_length=512, null=True, blank=True)
    gcp_path = models.CharField(max_length=512, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # FileListView and RecentFilesView: filter by user, sort by -created_at
            models.Index(fields=["user", "-created_at"], name="file_user_created_idx"),
            # StorageSummaryView and PresignUploadView: per-cloud storage aggregates
            models.Index(fields=["user", "aws_path"],   name="file_user_aws_idx"),
            models.Index(fields=["user", "azure_path"], name="file_user_azure_idx"),
            models.Index(fields=["user", "gcp_path"],   name="file_user_gcp_idx"),
        ]

    def __str__(self):
        return f"{self.file_name} ({self.user})"