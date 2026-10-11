from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    UserProfile,
    Service,
    Invoice,
    ActivityLog,
    Plan,
    Payment,
    DNSRecord,
)


# ---------------------------------------------------------------
# Inline the profile directly into the User admin page
# so you edit them together.
# ---------------------------------------------------------------
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]


# Re-register User with the inline attached
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# ---------------------------------------------------------------
# Standalone admin views
# ---------------------------------------------------------------
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "status", "owner", "renews_on", "price")
    list_filter = ("kind", "status")
    search_fields = ("name", "owner__username", "owner__email")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "owner", "amount", "status", "issued_on", "due_on")
    list_filter = ("status",)
    search_fields = ("number", "owner__username", "owner__email")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "owner", "ip_address", "created_at")
    list_filter = ("category",)
    search_fields = ("title", "detail", "owner__username")


admin.site.site_header = "InterServer Admin"
admin.site.site_title = "InterServer Admin"
admin.site.index_title = "Dashboard"
@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name", "category", "price", "billing_period", "setup_fee", "trial_days",
        "is_featured", "is_active", "sort_order",
    )
    list_filter = ("category", "billing_period", "is_featured", "is_active")
    search_fields = ("name", "slug", "tagline")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("category", "sort_order")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "invoice", "amount_kes", "phone",
        "status", "provider", "created_at",
    )
    list_filter = ("status", "provider")
    search_fields = ("reference", "phone", "invoice__number")
    readonly_fields = (
        "request_payload", "response_payload", "callback_payload",
        "created_at", "updated_at",
    )


@admin.register(DNSRecord)
class DNSRecordAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "value", "service", "ttl")
    list_filter = ("type",)
    search_fields = ("name", "value", "service__name")