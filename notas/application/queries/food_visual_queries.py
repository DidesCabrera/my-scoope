"""Published public food-image paths for authorized food read results."""

import re

from notas.application.services.food_catalog_snapshots import published_catalog_food_visual_digests
from notas.domain.models import LegacyFoodVisualAsset

_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _image_path(reference, digest: str) -> str | None:
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        return None
    return f"/api/v1/foods/visual-assets/{reference}/{digest}.png"


def published_food_visual_paths(foods) -> dict[int, str]:
    """Resolve only images already public in the food visual manifest.

    Operational foods have no direct FK to the master catalog. Match its stable
    reference and let a published operational override take precedence, as the
    public manifest does.
    """
    eligible = {food.id: food for food in foods if food.id and food.is_global and food.is_active}
    if not eligible:
        return {}
    refs = {food.catalog_food_ref for food in eligible.values() if food.catalog_food_ref}
    published_refs, catalog_digests = published_catalog_food_visual_digests(refs)
    catalog_paths = {}
    for reference, digest in catalog_digests.items():
        path = _image_path(reference, digest)
        if path:
            catalog_paths[reference] = path

    paths = {
        food_id: catalog_paths[food.catalog_food_ref]
        for food_id, food in eligible.items()
        if food.catalog_food_ref in catalog_paths
    }
    overrides = LegacyFoodVisualAsset.objects.filter(
        food_id__in=eligible, is_published=True,
    ).exclude(mobile_image_data=b"").values_list("food_id", "public_ref", "content_sha256")
    for food_id, reference, digest in overrides:
        food = eligible[food_id]
        if food.catalog_food_ref and food.catalog_food_ref not in published_refs:
            continue
        path = _image_path(reference, digest)
        if path:
            paths[food_id] = path
    return paths
