from __future__ import annotations

from datetime import datetime
from typing import Literal

from ninja import Field, Schema


class FoodLabelCaptureInput(Schema):
    name: str = Field(min_length=1, max_length=100)
    protein_g: float = Field(ge=0, le=100)
    carbs_g: float = Field(ge=0, le=100)
    fat_g: float = Field(ge=0, le=100)
    saturated_fat_g: float | None = Field(default=None, ge=0, le=100)
    sugar_g: float | None = Field(default=None, ge=0, le=100)
    fiber_g: float | None = Field(default=None, ge=0, le=100)
    sodium_mg: float | None = Field(default=None, ge=0, le=100_000)
    serving_size_g: float | None = Field(default=None, gt=0, le=10_000)
    volume_weight_g_per_100ml: float | None = Field(default=None, gt=0, le=10_000)
    declared_energy_kcal_per_100g: float | None = Field(default=None, ge=0, le=10_000)
    detected_basis: Literal["per_100g", "per_serving", "per_100ml", "manual"]
    ocr_engine: str = Field(min_length=1, max_length=80)
    ocr_engine_version: str = Field(default="", max_length=40)
    field_confidence: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    idempotency_key: str = Field(min_length=8, max_length=120)
    analysis_id: str | None = Field(default=None, max_length=36)
    retain_label_image: bool = False
    label_image_base64: str | None = Field(default=None, max_length=2_100_000)
    label_image_content_type: Literal["image/jpeg", "image/png", "image/webp"] | None = None


class FoodLabelLocalCandidateInput(Schema):
    basis: str = Field(default="", max_length=24)
    values: dict[str, float] = Field(default_factory=dict)


class FoodLabelAIAnalysisInput(Schema):
    image_base64: str = Field(min_length=10_000, max_length=2_100_000)
    image_content_type: Literal["image/jpeg", "image/png", "image/webp"]
    image_width: int = Field(ge=320, le=10_000)
    image_height: int = Field(ge=320, le=10_000)
    idempotency_key: str = Field(min_length=8, max_length=120)
    consent_to_ai_processing: bool
    local_candidate: FoodLabelLocalCandidateInput | None = None


class FoodLabelAIAnalysisData(Schema):
    analysis_id: str
    name: str
    basis: Literal["per_100g", "per_serving", "per_100ml", "unknown"]
    source_basis: Literal["per_100g", "per_serving", "per_100ml", "unknown"]
    serving_size_g: float | None = None
    source_values: dict[str, float]
    values: dict[str, float]
    field_confidence: dict[str, float]
    warnings: list[str]
    normalization_status: Literal[
        "ready",
        "basis_confirmation_required",
        "serving_size_required",
        "volume_weight_required",
    ]
    quality_confidence: float
    ocr_engine: str
    ocr_engine_version: str
    credits_charged: int
    available_credits: int


class FoodLabelAIAnalysisEnvelope(Schema):
    ok: Literal[True] = True
    data: FoodLabelAIAnalysisData
    error: None = None


class FoodLabelAIConfigData(Schema):
    credits_per_scan: int
    available_credits: int
    can_scan: bool
    image_retention_available: bool


class FoodLabelAIConfigEnvelope(Schema):
    ok: Literal[True] = True
    data: FoodLabelAIConfigData
    error: None = None


class FoodLabelImageData(Schema):
    receipt_id: int
    content_type: str
    image_base64: str
    size_bytes: int


class FoodLabelImageEnvelope(Schema):
    ok: Literal[True] = True
    data: FoodLabelImageData
    error: None = None


class FoodLabelImageDeleteData(Schema):
    receipt_id: int
    deleted: bool


class FoodLabelImageDeleteEnvelope(Schema):
    ok: Literal[True] = True
    data: FoodLabelImageDeleteData
    error: None = None


class FoodLabelCaptureData(Schema):
    id: int
    name: str
    protein_g: float
    carbs_g: float
    fat_g: float
    saturated_fat_g: float | None = None
    sugar_g: float | None = None
    fiber_g: float | None = None
    sodium_mg: float | None = None
    total_kcal: float
    is_user_food: bool
    is_verified: bool
    capture_receipt_id: int
    detected_basis: str
    serving_size_g: float | None = None
    ocr_engine: str
    label_image_retained: bool
    created_at: datetime


class FoodLabelCaptureEnvelope(Schema):
    ok: Literal[True] = True
    data: FoodLabelCaptureData
    error: None = None
