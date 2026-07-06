from django.contrib import admin

from admin_operations.models import AdminOperationAuditEvent


@admin.register(AdminOperationAuditEvent)
class AdminOperationAuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "actor_label", "target_app", "target_model", "target_id", "status_before", "status_after")
    list_filter = ("target_app", "target_model", "action", "source", "created_at")
    search_fields = ("actor_label", "action", "target_label", "target_id", "reason")
    readonly_fields = (
        "actor",
        "actor_label",
        "action",
        "source",
        "target_app",
        "target_model",
        "target_id",
        "target_label",
        "status_before",
        "status_after",
        "reason",
        "metadata",
        "created_at",
    )
    ordering = ("-created_at", "-id")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
