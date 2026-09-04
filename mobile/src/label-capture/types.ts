export type FoodLabelCaptureInput = {
  name: string;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  saturated_fat_g?: number;
  sugar_g?: number;
  fiber_g?: number;
  sodium_mg?: number;
  serving_size_g?: number;
  declared_energy_kcal_per_100g?: number;
  detected_basis: "per_100g" | "per_serving" | "manual";
  ocr_engine: string;
  ocr_engine_version: string;
  field_confidence: Record<string, number>;
  warnings: string[];
  idempotency_key: string;
  analysis_id?: string;
  retain_label_image?: boolean;
  label_image_base64?: string;
  label_image_content_type?: "image/jpeg" | "image/png" | "image/webp";
};

export type FoodLabelAIConfig = {
  credits_per_scan: number;
  available_credits: number;
  can_scan: boolean;
  image_retention_available: boolean;
};

export type FoodLabelAIAnalysis = {
  analysis_id: string;
  name: string;
  basis: "per_100g";
  source_basis: "per_100g" | "per_serving";
  serving_size_g: number | null;
  source_values: Record<string, number>;
  values: Record<string, number>;
  field_confidence: Record<string, number>;
  warnings: string[];
  normalization_status: "ready";
  quality_confidence: number;
  ocr_engine: string;
  ocr_engine_version: string;
  credits_charged: number;
  available_credits: number;
};

export type FoodLabelCaptureResult = {
  id: number;
  name: string;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  saturated_fat_g: number | null;
  sugar_g: number | null;
  fiber_g: number | null;
  sodium_mg: number | null;
  total_kcal: number;
  is_user_food: boolean;
  is_verified: boolean;
  capture_receipt_id: number;
  detected_basis: string;
  serving_size_g: number | null;
  ocr_engine: string;
  label_image_retained: boolean;
  created_at: string;
};

export type FoodLabelImage = {
  receipt_id: number;
  content_type: string;
  image_base64: string;
  size_bytes: number;
};
