import hashlib
import json
import math
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Max

from notas.domain.models import Food, FoodLabelCaptureReceipt


@dataclass(frozen=True)
class FoodCreateResult:
    food: Food


@dataclass(frozen=True)
class FoodUpdateResult:
    food: Food


@dataclass(frozen=True)
class FoodDeleteResult:
    food_id: int


@dataclass(frozen=True)
class FoodBulkCreateResult:
    foods: list[Food]

    @property
    def created_count(self) -> int:
        return len(self.foods)


@dataclass(frozen=True)
class FoodLabelCaptureResult:
    food: Food
    receipt: FoodLabelCaptureReceipt


def _next_food_list_order(user) -> int:
    current_max = (
        Food.objects
        .filter(created_by=user, is_active=True)
        .aggregate(max_order=Max("list_order"))
        .get("max_order")
    )
    return (current_max or 0) + 1


def _label_number(value, *, field: str, maximum: float, required: bool = False) -> float | None:
    if value is None and not required:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"food_label_{field}_invalid") from exc
    if not math.isfinite(number) or number < 0 or number > maximum:
        raise ValueError(f"food_label_{field}_invalid")
    return round(number, 3)


def _label_confidence(values) -> dict[str, float]:
    if not isinstance(values, dict):
        raise ValueError("food_label_confidence_invalid")
    allowed = {
        "energy_kcal",
        "protein_g",
        "carbs_g",
        "fat_g",
        "saturated_fat_g",
        "sugar_g",
        "fiber_g",
        "sodium_mg",
        "serving_size_g",
    }
    result = {}
    for key, value in values.items():
        if key not in allowed:
            raise ValueError("food_label_confidence_invalid")
        result[key] = _label_number(value, field="confidence", maximum=1, required=True)
    return result


def _label_warnings(values) -> list[str]:
    if not isinstance(values, list) or len(values) > 20:
        raise ValueError("food_label_warnings_invalid")
    warnings = []
    for value in values:
        clean = str(value or "").strip()
        if not clean or len(clean) > 160:
            raise ValueError("food_label_warnings_invalid")
        warnings.append(clean)
    return warnings


def _label_payload_hash(payload: dict) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _existing_label_capture(*, user, idempotency_key: str, payload_hash: str) -> FoodLabelCaptureResult | None:
    receipt = (
        FoodLabelCaptureReceipt.objects.select_related("food")
        .filter(idempotency_key=idempotency_key)
        .first()
    )
    if receipt is None:
        return None
    if receipt.food.created_by_id != user.id or receipt.confirmed_payload_hash != payload_hash:
        raise ValueError("food_label_idempotency_conflict")
    return FoodLabelCaptureResult(food=receipt.food, receipt=receipt)


def create_food_from_label_capture(
    *,
    user,
    name,
    protein_g,
    carbs_g,
    fat_g,
    idempotency_key,
    ocr_engine,
    ocr_engine_version="",
    detected_basis=FoodLabelCaptureReceipt.BASIS_MANUAL,
    serving_size_g=None,
    declared_energy_kcal_per_100g=None,
    saturated_fat_g=None,
    sugar_g=None,
    fiber_g=None,
    sodium_mg=None,
    field_confidence=None,
    warnings=None,
    retained_label_image=None,
    retained_label_image_content_type="",
    retained_label_image_sha256="",
) -> FoodLabelCaptureResult:
    clean_name = str(name or "").strip()
    if not clean_name or len(clean_name) > 100:
        raise ValueError("food_label_name_invalid")
    clean_key = str(idempotency_key or "").strip()
    if not 8 <= len(clean_key) <= 120:
        raise ValueError("food_label_idempotency_key_invalid")
    clean_engine = str(ocr_engine or "").strip()
    clean_engine_version = str(ocr_engine_version or "").strip()
    if not clean_engine or len(clean_engine) > 80 or len(clean_engine_version) > 40:
        raise ValueError("food_label_ocr_engine_invalid")
    if detected_basis not in dict(FoodLabelCaptureReceipt.BASIS_CHOICES):
        raise ValueError("food_label_basis_invalid")

    confirmed = {
        "name": clean_name,
        "protein_g": _label_number(protein_g, field="protein", maximum=100, required=True),
        "carbs_g": _label_number(carbs_g, field="carbs", maximum=100, required=True),
        "fat_g": _label_number(fat_g, field="fat", maximum=100, required=True),
        "saturated_fat_g": _label_number(saturated_fat_g, field="saturated_fat", maximum=100),
        "sugar_g": _label_number(sugar_g, field="sugar", maximum=100),
        "fiber_g": _label_number(fiber_g, field="fiber", maximum=100),
        "sodium_mg": _label_number(sodium_mg, field="sodium", maximum=100_000),
        "serving_size_g": _label_number(serving_size_g, field="serving_size", maximum=10_000),
        "declared_energy_kcal_per_100g": _label_number(
            declared_energy_kcal_per_100g,
            field="energy",
            maximum=10_000,
        ),
        "ocr_engine": clean_engine,
        "ocr_engine_version": clean_engine_version,
        "detected_basis": detected_basis,
        "field_confidence": _label_confidence(field_confidence or {}),
        "warnings": _label_warnings(warnings or []),
        "retained_label_image_sha256": str(retained_label_image_sha256 or ""),
    }
    image_bytes = bytes(retained_label_image) if retained_label_image else None
    image_content_type = str(retained_label_image_content_type or "").strip()
    if image_bytes:
        if len(image_bytes) > 1_500_000 or image_content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise ValueError("food_label_retained_image_invalid")
        if hashlib.sha256(image_bytes).hexdigest() != confirmed["retained_label_image_sha256"]:
            raise ValueError("food_label_retained_image_invalid")
    elif image_content_type or confirmed["retained_label_image_sha256"]:
        raise ValueError("food_label_retained_image_invalid")
    if confirmed["serving_size_g"] is not None and confirmed["serving_size_g"] <= 0:
        raise ValueError("food_label_serving_size_invalid")
    if detected_basis == FoodLabelCaptureReceipt.BASIS_PER_SERVING and confirmed["serving_size_g"] is None:
        raise ValueError("food_label_serving_size_required")
    payload_hash = _label_payload_hash(confirmed)
    existing = _existing_label_capture(user=user, idempotency_key=clean_key, payload_hash=payload_hash)
    if existing:
        return existing

    try:
        with transaction.atomic():
            food = Food.objects.create(
                name=clean_name,
                protein=confirmed["protein_g"],
                carbs=confirmed["carbs_g"],
                fat=confirmed["fat_g"],
                saturated_fat_g_per_100g=confirmed["saturated_fat_g"],
                sugar_g_per_100g=confirmed["sugar_g"],
                fiber_g_per_100g=confirmed["fiber_g"],
                sodium_mg_per_100g=confirmed["sodium_mg"],
                default_portion_g=confirmed["serving_size_g"],
                created_by=user,
                is_global=False,
                is_verified=False,
                solver_enabled=False,
                list_order=_next_food_list_order(user),
            )
            receipt = FoodLabelCaptureReceipt.objects.create(
                food=food,
                idempotency_key=clean_key,
                ocr_engine=clean_engine,
                ocr_engine_version=clean_engine_version,
                detected_basis=detected_basis,
                serving_size_g=confirmed["serving_size_g"],
                declared_energy_kcal_per_100g=confirmed["declared_energy_kcal_per_100g"],
                field_confidence=confirmed["field_confidence"],
                warnings=confirmed["warnings"],
                confirmed_payload_hash=payload_hash,
                retained_label_image=image_bytes,
                retained_label_image_content_type=image_content_type,
                retained_label_image_sha256=confirmed["retained_label_image_sha256"],
                retained_label_image_size=len(image_bytes or b""),
            )
    except IntegrityError:
        existing = _existing_label_capture(user=user, idempotency_key=clean_key, payload_hash=payload_hash)
        if existing:
            return existing
        raise
    return FoodLabelCaptureResult(food=food, receipt=receipt)


@transaction.atomic
def create_food(
    *,
    user,
    name,
    protein,
    carbs,
    fat,
) -> FoodCreateResult:
    food = Food.objects.create(
        name=(name or "").strip(),
        protein=protein,
        carbs=carbs,
        fat=fat,
        created_by=user,
        list_order=_next_food_list_order(user),
    )

    return FoodCreateResult(
        food=food,
    )


@transaction.atomic
def update_food(
    *,
    food: Food,
    name,
    protein,
    carbs,
    fat,
) -> FoodUpdateResult:
    food.name = (name or "").strip()
    food.protein = protein
    food.carbs = carbs
    food.fat = fat

    food.save(
        update_fields=[
            "name",
            "protein",
            "carbs",
            "fat",
        ]
    )

    return FoodUpdateResult(
        food=food,
    )


@transaction.atomic
def delete_food(
    *,
    food: Food,
) -> FoodDeleteResult:
    food_id = food.id
    food.is_active = False
    food.save(update_fields=["is_active"])

    return FoodDeleteResult(food_id=food_id)


@transaction.atomic
def bulk_create_foods(
    *,
    user,
    rows,
) -> FoodBulkCreateResult:
    foods = []
    next_order = _next_food_list_order(user)

    for offset, row in enumerate(rows):
        food = Food.objects.create(
            name=(row["name"] or "").strip(),
            protein=row["protein"],
            carbs=row["carbs"],
            fat=row["fat"],
            created_by=user,
            list_order=next_order + offset,
        )
        foods.append(food)

    return FoodBulkCreateResult(
        foods=foods,
    )
