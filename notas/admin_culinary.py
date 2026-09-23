from django.contrib import admin, messages

from notas.application.culinary_library import validate_variant
from notas.domain.models import CulinaryTemplate, CulinaryVariant


@admin.register(CulinaryTemplate)
class CulinaryTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "family", "version", "owner")
    search_fields = ("name", "family")


@admin.register(CulinaryVariant)
class CulinaryVariantAdmin(admin.ModelAdmin):
    list_display = ("name", "template", "version", "status", "reviewed_by")
    list_filter = ("status", "template__family")
    readonly_fields = ("status", "reviewed_by", "reviewed_at", "evidence_digest")
    actions = ("validate_rules", "confirm_human_review")

    def _validate(self, request, queryset, *, human_review):
        for variant in queryset:
            try:
                validate_variant(user=request.user, variant_id=variant.pk, human_review=human_review, rubric=variant.rubric)
                self.message_user(request, f"{variant.name}: validación registrada.")
            except ValueError as exc:
                self.message_user(request, f"{variant.name}: {exc}", messages.ERROR)

    @admin.action(description="Validar reglas (no equivale a revisión humana)")
    def validate_rules(self, request, queryset):
        self._validate(request, queryset, human_review=False)

    @admin.action(description="Confirmar revisión humana con rúbrica explícita completada")
    def confirm_human_review(self, request, queryset):
        self._validate(request, queryset, human_review=True)
