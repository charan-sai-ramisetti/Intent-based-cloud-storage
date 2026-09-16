from django.urls import path

from .views import (
    FileListView,
    PresignUploadView,
    ConfirmUploadView,
    PresignDownloadView,
    FileDeleteView,
    MultipartStartView,
    MultipartPresignPartView,
    MultipartCompleteView,
    BenchmarkPresignAWSView,
    BenchmarkPresignAzureView,
    BenchmarkPresignGCPView,
    ServerUploadAWSView,
    ServerUploadAzureView,
    ServerUploadGCPView,
)

urlpatterns = [

    # List all user files
    path("", FileListView.as_view()),

    # Generate upload URL
    path("presign/upload/", PresignUploadView.as_view()),

    # Confirm upload metadata
    path("confirm-upload/", ConfirmUploadView.as_view()),

    # Generate download URL
    path("<int:file_id>/presign/download/", PresignDownloadView.as_view()),

    # Delete file
    path("<int:file_id>/", FileDeleteView.as_view()),

    # Start multipart upload
    path("multipart/start/", MultipartStartView.as_view()),

    # Generate part upload URL
    path("multipart/presign-part/", MultipartPresignPartView.as_view()),

    # Complete multipart upload
    path("multipart/complete/", MultipartCompleteView.as_view()),

    # Benchmark presigned (AWS/Azure/GCP)
    path("benchmark/presign/aws/", BenchmarkPresignAWSView.as_view()),
    path("benchmark/presign/azure/", BenchmarkPresignAzureView.as_view()),
    path("benchmark/presign/gcp/", BenchmarkPresignGCPView.as_view()),

    # Benchmark server-side uploads
    path("upload/server/aws/", ServerUploadAWSView.as_view()),
    path("upload/server/azure/", ServerUploadAzureView.as_view()),
    path("upload/server/gcp/", ServerUploadGCPView.as_view()),
]