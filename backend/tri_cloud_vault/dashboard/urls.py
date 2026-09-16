from django.urls import path
from .views import StorageSummaryView,FolderSummaryView,RecentFilesView

urlpatterns = [
    path("summary/", StorageSummaryView.as_view()),
    path("folders/", FolderSummaryView.as_view()),
    path("recent-files/", RecentFilesView.as_view()),
]
