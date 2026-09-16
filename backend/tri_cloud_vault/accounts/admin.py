from django.contrib.auth.admin import UserAdmin
from .models import User
from tri_cloud_vault.admin_dashboard import admin_site


class CustomUserAdmin(UserAdmin):
    model = User

    list_display = (
        "email",
        "username",
        "is_email_verified",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "is_email_verified",
        "is_staff",
        "is_active",
    )

    search_fields = ("email", "username")
    ordering = ("email",)

    fieldsets = UserAdmin.fieldsets + (
        ("Email Verification", {"fields": ("is_email_verified",)}),
    )


admin_site.register(User, CustomUserAdmin)