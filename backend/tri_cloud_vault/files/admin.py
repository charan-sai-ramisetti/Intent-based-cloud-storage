from django.contrib import admin
from .models import File
from tri_cloud_vault.admin_dashboard import admin_site


class FileAdmin(admin.ModelAdmin):
    def readable_size(self, obj):
        size = obj.file_size or 0
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{round(size,2)} {unit}"
            size /= 1024
    list_display = (
        "id",
        "user",
        "file_name",
        "readable_size",
        "storage_clouds",
        "created_at",
    )

    list_filter = (
        "created_at",
    )

    search_fields = (
        "file_name",
        "user__email",
    )

    ordering = (
        "-created_at",
    )

    def storage_clouds(self, obj):
        clouds = []

        if obj.aws_path:
            clouds.append("AWS")

        if obj.azure_path:
            clouds.append("Azure")

        if obj.gcp_path:
            clouds.append("GCP")

        return ", ".join(clouds)

    storage_clouds.short_description = "Cloud Storage"


admin_site.register(File, FileAdmin)