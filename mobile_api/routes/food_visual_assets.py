"""Public, versioned food images; no nutrition snapshot is changed."""

from uuid import UUID

from django.http import Http404, HttpResponse, JsonResponse
from ninja import Router

from food_catalog.models import CatalogFood, FoodVisualAsset
from notas.application.services.food_imports.localized_names import resolve_food_display_name
from notas.domain.models import Food

router = Router()


@router.get("/foods/visual-assets/manifest", auth=None, operation_id="mobile_api_food_visual_manifest")
def food_visual_manifest(request):
    assets = list(
        FoodVisualAsset.objects.filter(
            is_published=True,
            food__status=CatalogFood.STATUS_PUBLISHED,
        ).select_related("food").only("food__catalog_ref", "content_sha256")
    )
    by_ref = {asset.food.catalog_ref: asset for asset in assets if asset.content_sha256}
    images = {}
    food_ids = {}
    if by_ref:
        for food in Food.objects.filter(
            is_global=True, is_active=True, catalog_food_ref__in=by_ref
        ).prefetch_related("localized_names").only("name", "catalog_food_ref"):
            asset = by_ref[food.catalog_food_ref]
            url = f"/api/v1/foods/visual-assets/{food.catalog_food_ref}/{asset.content_sha256}.png"
            food_ids[str(food.pk)] = url
            images[food.name] = url
            images[resolve_food_display_name(food)] = url
    response = JsonResponse({"images": images, "food_ids": food_ids})
    response["Cache-Control"] = "public, max-age=60"
    return response


@router.get("/foods/visual-assets/{catalog_ref}/{digest}.png", auth=None, operation_id="mobile_api_food_visual_image")
def food_visual_image(request, catalog_ref: str, digest: str):
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise Http404
    try:
        catalog_ref = UUID(catalog_ref)
    except ValueError as exc:
        raise Http404 from exc
    asset = FoodVisualAsset.objects.filter(
        food__catalog_ref=catalog_ref,
        food__status=CatalogFood.STATUS_PUBLISHED,
        is_published=True,
        content_sha256=digest,
    ).first()
    if asset is None or not asset.mobile_image_data:
        raise Http404
    response = HttpResponse(bytes(asset.mobile_image_data), content_type="image/png")
    response["Cache-Control"] = "public, max-age=300"
    response["ETag"] = f'"{digest}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response
