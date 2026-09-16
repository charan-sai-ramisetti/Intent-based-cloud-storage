from django.contrib import admin
from .models import Subscription, Payment
from tri_cloud_vault.admin_dashboard import admin_site


class SubscriptionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "plan",
        "cloud_limit_mb",
        "max_file_size_mb",
        "upgraded_at",
    )

    list_filter = (
        "plan",
        "upgraded_at",
    )

    search_fields = (
        "user__email",
        "user__username",
    )

    ordering = (
        "-upgraded_at",
    )


class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "amount",
        "payment_status",
        "razorpay_order_id",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "user__email",
        "razorpay_order_id",
        "razorpay_payment_id",
    )

    ordering = (
        "-created_at",
    )

    def payment_status(self, obj):
        if obj.status == "SUCCESS":
            return "✅ Success"
        elif obj.status == "FAILED":
            return "❌ Failed"
        return "⏳ Pending"

    payment_status.short_description = "Payment Status"


admin_site.register(Subscription, SubscriptionAdmin)
admin_site.register(Payment, PaymentAdmin)