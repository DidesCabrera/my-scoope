export type NutritionLabelBoundingBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type NutritionLabelObservation = {
  text: string;
  confidence: number;
  boundingBox: NutritionLabelBoundingBox;
};

export type NutritionLabelImageQualityMetrics = {
  brightness: number;
  sharpness: number;
  textObservationCount: number;
  averageTextConfidence: number;
  textCoverage: number;
};

export type NutritionLabelRecognition = {
  engine: "apple_vision";
  engineVersion: string;
  durationMs: number;
  observations: NutritionLabelObservation[];
  imageQuality: NutritionLabelImageQualityMetrics;
};
