from rest_framework import serializers
from .models import File

ALLOWED_CLOUDS = {"AWS", "AZURE", "GCP"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = [
            "id",
            "file_name",
            "file_size",
            "aws_path",
            "azure_path",
            "gcp_path",
            "created_at",
        ]


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    clouds = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )

    def validate_clouds(self, clouds):
        clouds = [c.upper() for c in clouds]
        invalid = set(clouds) - ALLOWED_CLOUDS
        if invalid:
            raise serializers.ValidationError(
                f"Invalid clouds: {', '.join(invalid)}"
            )
        return clouds

    def validate_file(self, file):
        if file.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(
                "File too large (max 100MB)"
            )
        return file
