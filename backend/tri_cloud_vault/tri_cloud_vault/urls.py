"""
URL configuration for tri_cloud_vault project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from .admin_dashboard import admin_site
from .health import HealthCheckView
from django.urls import path, include

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("admin/", admin_site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/files/", include("files.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/storage/", include("dashboard.urls")),
]
