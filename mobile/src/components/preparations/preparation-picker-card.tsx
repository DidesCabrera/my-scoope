import type { PreparationDetail } from "@/api/preparations";
import { NutritionEntityCard } from "@/components/nutrition";
import { PickerCardAction } from "@/components/pickers/picker-card-action";
import { householdMeasureDisplayLabel } from "@/components/pickers/food-portion-nutrition";
import { FoodPanels } from "@/components/panels";
import type { FoodPanelItem } from "@/components/panels";
import { formatPreparationNumber } from "./preparation-ingredients-card";
import { ingredientPanelItem } from "./preparation-panel-items";

function allocation(grams: number, caloriesPerGram: number, calories: number): number {
  return calories > 0 ? grams * caloriesPerGram / calories * 100 : 0;
}

export function preparationPortionLabel(detail: PreparationDetail): string {
  if (detail.selection_mode === "grams") return `${formatPreparationNumber(detail.grams)} g`;
  const count = detail.selected_units ?? 1;
  const label = count > 1 && detail.household_label === "completo mediano"
    ? "completos medianos"
    : householdMeasureDisplayLabel(detail.household_label, count);
  return `${formatPreparationNumber(count)} ${label}`;
}

export function PreparationPickerCard({ actionLabel, detail, onAction, onOpenItem, selected = false }: {
  actionLabel?: string;
  detail: PreparationDetail;
  onAction?: () => void;
  onOpenItem?: (item: FoodPanelItem) => void;
  selected?: boolean;
}) {
  const { calories, protein_g, carbs_g, fat_g } = detail.nutrition;
  return <NutritionEntityCard
    actions={actionLabel && onAction ? <PickerCardAction label={actionLabel} onPress={onAction} subject={detail.name} /> : undefined}
    collapsiblePanel
    entity="preparation"
    eyebrow={selected ? "PREPARACIÓN SELECCIONADA" : "PREPARACIÓN"}
    subtitle={preparationPortionLabel(detail)}
    nutrition={{
      calories,
      protein: { grams: protein_g, allocation: allocation(protein_g, 4, calories) },
      carbs: { grams: carbs_g, allocation: allocation(carbs_g, 4, calories) },
      fat: { grams: fat_g, allocation: allocation(fat_g, 9, calories) },
    }}
    title={detail.name}>
    <FoodPanels items={detail.ingredients.map((ingredient, index) => ingredientPanelItem(ingredient, index, detail))} onOpenItem={onOpenItem} showEditTab={false} />
  </NutritionEntityCard>;
}
