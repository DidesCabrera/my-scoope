import type { FoodPortionMeasure } from "./food-portion-nutrition";

export type FoodPortionFieldProps = {
  equivalentMetricAmount: number;
  householdDefaultAmount?: number | null;
  householdDetail?: string;
  householdMeasureLabel?: string;
  label: string;
  measure: FoodPortionMeasure;
  metricDefaultAmount?: number | null;
  metricUnit: "g" | "ml";
  onChange(value: string): void;
  onMeasureChange(measure: FoodPortionMeasure): void;
  value: string;
};
