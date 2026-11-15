"""Admin editing for visual overrides of operational global foods."""

from django import forms
from django.contrib import admin

from food_catalog.models import CatalogFood
from food_catalog.visual_assets import prepare_food_visual
from notas.domain.models import LegacyFoodVisualAsset


class LegacyFoodVisualAssetForm(forms.ModelForm):
    food = forms.ModelChoiceField(queryset=None)
    upload = forms.FileField(label="PNG del alimento", required=False)

    class Meta:
        model = LegacyFoodVisualAsset
        fields = ("food", "is_published", "source_note")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["food"].queryset = self._meta.model._meta.get_field("food").remote_field.model.objects.filter(
            is_global=True, is_active=True
        )

    def clean(self):
        cleaned = super().clean()
        food = cleaned.get("food")
        if food and (not food.is_global or not food.is_active):
            self.add_error("food", "Selecciona un alimento global activo.")
        if cleaned.get("is_published") and food and food.catalog_food_ref:
            if not CatalogFood.objects.filter(
                catalog_ref=food.catalog_food_ref, status=CatalogFood.STATUS_PUBLISHED
            ).exists():
                self.add_error("is_published", "El alimento del catálogo central debe estar publicado.")
        if cleaned.get("is_published") and not cleaned.get("source_note", "").strip():
            self.add_error("source_note", "Registra el origen o la aprobación de la imagen.")
        if not cleaned.get("upload") and not self.instance.pk:
            self.add_error("upload", "Selecciona un PNG para crear el recurso.")
        return cleaned

    def clean_upload(self):
        upload = self.cleaned_data.get("upload")
        if upload:
            self.prepared_image = prepare_food_visual(upload)
        return upload


@admin.register(LegacyFoodVisualAsset)
class LegacyFoodVisualAssetAdmin(admin.ModelAdmin):
    form = LegacyFoodVisualAssetForm
    fields = ("food", "upload", "is_published", "source_note", "public_ref", "content_sha256", "updated_at")
    list_display = ("food", "is_published", "public_ref", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("food__name",)
    readonly_fields = ("public_ref", "content_sha256", "updated_at")

    def save_model(self, request, obj, form, change):
        prepared = getattr(form, "prepared_image", None)
        if prepared:
            obj.image_data, obj.mobile_image_data, obj.content_sha256 = prepared
        super().save_model(request, obj, form, change)
