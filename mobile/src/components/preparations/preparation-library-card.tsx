import { ChevronRight } from "lucide-react-native";
import { View } from "react-native";

import type { PersonalPreparation } from "@/api/preparations";
import { tokens } from "@/design/tokens";
import { NutritionEntityCard } from "@/components/nutrition";
import { FoodPanels } from "@/components/panels";
import { EntityCard, EntityCardAction } from "@/components/ui/product";
import { ingredientPanelItem } from "./preparation-panel-items";
import { preparationPortionLabel } from "./preparation-picker-card";

function allocation(grams: number, factor: number, calories: number): number {
  return calories > 0 ? grams * factor / calories * 100 : 0;
}

export function PreparationLibraryCard({ item, onOpen }: { item: PersonalPreparation; onOpen(): void }) {
  const label = item.is_draft ? `Continuar ${item.name}` : `Ver detalle de ${item.name}`;
  const openAction = <EntityCardAction label={label} onPress={onOpen} role="link"><ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} /></EntityCardAction>;
  if (item.is_draft) return <EntityCard
    accent={tokens.color.preparation}
    actions={openAction}
    entity="preparation"
    eyebrow="Preparación pendiente de ingredientes"
    headingLink={{ label, onPress: onOpen }}
    title={item.name}
  />;
  const { calories, protein_g, carbs_g, fat_g } = item.nutrition;
  return <View>
    <NutritionEntityCard
      actions={openAction}
      collapsiblePanel
      entity="preparation"
      eyebrow="Preparación"
      headingLink={{ label, onPress: onOpen }}
      nutrition={{
        calories,
        protein: { grams: protein_g, allocation: allocation(protein_g, 4, calories) },
        carbs: { grams: carbs_g, allocation: allocation(carbs_g, 4, calories) },
        fat: { grams: fat_g, allocation: allocation(fat_g, 9, calories) },
      }}
      subtitle={preparationPortionLabel(item)}
      title={item.name}>
      <FoodPanels items={item.ingredients.map((ingredient, index) => ingredientPanelItem(ingredient, index, item))} showEditTab={false} />
    </NutritionEntityCard>
  </View>;
}
