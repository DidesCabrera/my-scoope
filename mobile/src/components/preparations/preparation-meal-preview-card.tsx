import { type Href, useRouter } from "expo-router";

import type { PreparationDetail } from "@/api/preparations";
import type { LibraryItem } from "@/api/types";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";
import { NutritionEntityCard } from "@/components/nutrition";
import { FoodPanels } from "@/components/panels";
import { projectPreparationMeal } from "./preparation-meal-preview";

export function PreparationMealPreviewCard({ meal, selected, relationId }: { meal: LibraryItem; selected: PreparationDetail; relationId?: number }) {
  const router = useRouter();
  const preview = projectPreparationMeal(meal, selected, relationId);
  if (!preview) return null;
  return <NutritionEntityCard
    entity="meal"
    eyebrow="PREVISUALIZACIÓN COMIDA"
    indicators={[
      { icon: "food", label: "alimentos", value: preview.foodCount },
      { icon: "preparation", label: "preparaciones", value: preview.preparationCount },
    ]}
    nutrition={libraryNutrition(preview.nutrition)}
    title={preview.name}>
    <FoodPanels items={preview.items} onOpenItem={(item) => {
      if (item.detailId == null) return;
      router.push((item.kind === "preparation" ? `/libraries/preparations/${item.detailId}` : `/libraries/foods/${item.detailId}`) as Href);
    }} showEditTab={false} />
  </NutritionEntityCard>;
}
