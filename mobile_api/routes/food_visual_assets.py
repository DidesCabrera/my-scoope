"""Public, versioned food images; no nutrition snapshot is changed."""

from typing import Literal
from uuid import UUID

from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from ninja import Router

from food_catalog.models import CatalogFood, FoodVisualAsset, PreparationVisualAsset
from food_catalog.visual_assets import render_wide_food_visual
from notas.application.services.food_imports.localized_names import resolve_food_display_name
from notas.domain.models import Food, LegacyFoodVisualAsset, Preparation

router = Router()


def _global_visual_overrides():
    """Published editorial images for visible foods, regardless of nutrition source."""
    published_refs = CatalogFood.objects.filter(
        status=CatalogFood.STATUS_PUBLISHED
    ).values("catalog_ref")
    return LegacyFoodVisualAsset.objects.filter(
        is_published=True,
        food__is_global=True,
        food__is_active=True,
    ).filter(
        Q(food__catalog_food_ref__isnull=True)
        | Q(food__catalog_food_ref__in=published_refs)
    )


@router.get("/foods/visual-assets/manifest", auth=None, operation_id="mobile_api_food_visual_manifest")
def food_visual_manifest(request, layout: Literal["square", "wide-v1"] = "square"):
    """Compatibility endpoint for installed mobile builds."""
    return _catalog_visual_manifest(layout)


@router.get("/catalog/visual-assets/manifest", auth=None, operation_id="mobile_api_catalog_visual_manifest")
def catalog_visual_manifest(request, layout: Literal["square", "wide-v1"] = "square"):
    return _catalog_visual_manifest(layout)


def _catalog_visual_manifest(layout: str):
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
            url = _visual_url(food.catalog_food_ref, asset.content_sha256, layout)
            food_ids[str(food.pk)] = url
            images[food.name] = url
            images[resolve_food_display_name(food)] = url
    for asset in _global_visual_overrides().select_related("food").prefetch_related("food__localized_names"):
        if not asset.content_sha256 or not asset.mobile_image_data:
            continue
        food = asset.food
        url = _visual_url(asset.public_ref, asset.content_sha256, layout)
        food_ids[str(food.pk)] = url
        images[food.name] = url
        images[resolve_food_display_name(food)] = url
    preparation_ids = {}
    preparation_images = {}
    preparation_assets = PreparationVisualAsset.objects.filter(
        is_published=True,
        preparation__is_active=True,
        preparation__current_version__published_at__isnull=False,
    ).select_related("preparation")
    by_preparation_ref = {
        asset.preparation.catalog_ref: asset
        for asset in preparation_assets if asset.content_sha256 and asset.mobile_image_data
    }
    if by_preparation_ref:
        for preparation in Preparation.objects.filter(
            is_global=True, is_active=True, current_version__isnull=False,
            catalog_ref__in=by_preparation_ref,
        ):
            asset = by_preparation_ref[preparation.catalog_ref]
            url = _preparation_visual_url(preparation.catalog_ref, asset.content_sha256, layout)
            preparation_ids[str(preparation.pk)] = url
            preparation_images[preparation.name] = url
    response = JsonResponse({
        "images": images, "food_ids": food_ids,
        "preparation_images": preparation_images, "preparation_ids": preparation_ids,
    })
    response["Cache-Control"] = "public, max-age=60"
    return response


def _visual_url(ref, digest: str, layout: str) -> str:
    suffix = "/wide-v1.png" if layout == "wide-v1" else ".png"
    return f"/api/v1/foods/visual-assets/{ref}/{digest}{suffix}"


def _preparation_visual_url(ref, digest: str, layout: str) -> str:
    suffix = "/wide-v1.png" if layout == "wide-v1" else ".png"
    return f"/api/v1/preparations/visual-assets/{ref}/{digest}{suffix}"


def _find_preparation_visual(catalog_ref: str, digest: str):
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise Http404
    try:
        catalog_ref = UUID(catalog_ref)
    except ValueError as exc:
        raise Http404 from exc
    if not Preparation.objects.filter(
        catalog_ref=catalog_ref, is_global=True, is_active=True, current_version__isnull=False,
    ).exists():
        raise Http404
    asset = PreparationVisualAsset.objects.filter(
        preparation__catalog_ref=catalog_ref,
        preparation__is_active=True,
        preparation__current_version__published_at__isnull=False,
        is_published=True, content_sha256=digest,
    ).first()
    if asset is None or not asset.mobile_image_data:
        raise Http404
    return asset


@router.get("/preparations/visual-assets/{catalog_ref}/{digest}.png", auth=None, operation_id="mobile_api_preparation_visual_image")
def preparation_visual_image(request, catalog_ref: str, digest: str):
    asset = _find_preparation_visual(catalog_ref, digest)
    response = HttpResponse(bytes(asset.mobile_image_data), content_type="image/png")
    response["Cache-Control"] = "public, max-age=300"
    response["ETag"] = f'"{digest}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@router.get("/preparations/visual-assets/{catalog_ref}/{digest}/wide-v1.png", auth=None, operation_id="mobile_api_preparation_visual_wide_image")
def preparation_visual_wide_image(request, catalog_ref: str, digest: str):
    asset = _find_preparation_visual(catalog_ref, digest)
    response = HttpResponse(render_wide_food_visual(bytes(asset.mobile_image_data)), content_type="image/png")
    response["Cache-Control"] = "public, max-age=300"
    response["ETag"] = f'"{digest}-wide-v1"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _find_visual(catalog_ref: str, digest: str):
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
    if asset is None:
        asset = _global_visual_overrides().filter(
            public_ref=catalog_ref, content_sha256=digest
        ).first()
    if asset is None or not asset.mobile_image_data:
        raise Http404
    return asset


@router.get("/foods/visual-assets/{catalog_ref}/{digest}.png", auth=None, operation_id="mobile_api_food_visual_image")
def food_visual_image(request, catalog_ref: str, digest: str):
    asset = _find_visual(catalog_ref, digest)
    response = HttpResponse(bytes(asset.mobile_image_data), content_type="image/png")
    response["Cache-Control"] = "public, max-age=300"
    response["ETag"] = f'"{digest}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@router.get("/foods/visual-assets/{catalog_ref}/{digest}/wide-v1.png", auth=None, operation_id="mobile_api_food_visual_wide_image")
def food_visual_wide_image(request, catalog_ref: str, digest: str):
    asset = _find_visual(catalog_ref, digest)
    response = HttpResponse(render_wide_food_visual(bytes(asset.mobile_image_data)), content_type="image/png")
    response["Cache-Control"] = "public, max-age=300"
    response["ETag"] = f'"{digest}-wide-v1"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@router.get("/foods/visual-assets/legacy/{food_id}/{digest}.png", auth=None, operation_id="mobile_api_legacy_food_visual_image")
def legacy_food_visual_image(request, food_id: int, digest: str):
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise Http404
    asset = LegacyFoodVisualAsset.objects.filter(
        food_id=food_id,
        food__is_global=True,
        food__is_active=True,
        food__catalog_food_ref__isnull=True,
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
