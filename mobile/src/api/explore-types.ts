import type { LibraryItem, LibraryPageData } from "./types";

export type ExploreMealOccasion = "breakfast" | "lunch" | "dinner" | "snack" | "pre_workout" | "post_workout";
export type ExploreMealDietaryStyle = "omnivore" | "pescatarian" | "vegetarian" | "vegan";

export type ExploreMealItem = LibraryItem & {
  catalog_id: number;
  summary: string;
  occasion: ExploreMealOccasion;
  occasion_label: string;
  dietary_style: ExploreMealDietaryStyle;
  dietary_style_label: string;
  is_saved: boolean;
};

export type ExploreMealPageData = Omit<LibraryPageData, "items"> & {
  items: ExploreMealItem[];
};

export type ExploreMealSaveResult = {
  saved_meal_id: number;
  already_saved: boolean;
  message: string;
};

export type ExploreDailyPlanItem = LibraryItem & {
  catalog_id: number;
  summary: string;
  dietary_style: ExploreMealDietaryStyle;
  dietary_style_label: string;
  meal_count: number;
  is_saved: boolean;
};

export type ExploreDailyPlanPageData = Omit<LibraryPageData, "items"> & {
  items: ExploreDailyPlanItem[];
};

export type ExploreDailyPlanSaveResult = {
  saved_dailyplan_id: number;
  already_saved: boolean;
  message: string;
};
