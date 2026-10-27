import type { LibraryItem } from "@/api/types";
import { MealPanels } from "@/components/libraries/entity-panels";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";
import { NutritionEntityCard } from "@/components/nutrition";
import { PickerCardAction } from "@/components/pickers/picker-card-action";

export function DailyPlanPreviewCard({ action, eyebrow, item }: {
  action?: { label: string; onPress(): void };
  eyebrow?: string;
  item: LibraryItem;
}) {
  return <NutritionEntityCard
    actions={action ? <PickerCardAction label={action.label} onPress={action.onPress} subject={item.name} /> : undefined}
    entity="dailyPlan"
    eyebrow={eyebrow}
    indicators={item.indicators}
    nutrition={libraryNutrition(item.nutrition)}
    subtitle={item.subtitle || undefined}
    title={item.name}>
    {item.panel.kind === "meals" ? <MealPanels dailyPlanId={item.id} items={item.panel.meals} nestedScroll showEditTab={false} /> : null}
  </NutritionEntityCard>;
}
