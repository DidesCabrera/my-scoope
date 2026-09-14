import { ChevronRight } from "lucide-react-native";
import { StyleSheet, View } from "react-native";

import { NutritionEntityCard } from "@/components/nutrition";
import { EntityCardAction } from "@/components/ui";
import { tokens } from "@/design/tokens";
import type { FoodPanelItem } from "@/components/panels";

function macroShare(grams: number, factor: number, calories: number): number {
  return calories > 0 ? (grams * factor * 100) / calories : 0;
}

export function FoodDetailCardList({ items, onOpenFood }: { items: FoodPanelItem[]; onOpenFood?(item: FoodPanelItem): void }) {
  return (
    <View style={styles.list}>
      {items.map((item) => {
        const calculatedCalories = item.proteinGrams * 4 + item.carbsGrams * 4 + item.fatGrams * 9;
        const calories = item.calories || calculatedCalories;
        return (
          <NutritionEntityCard
            actions={onOpenFood && item.detailId != null ? (
              <EntityCardAction label={`Ver detalle de ${item.name}`} onPress={() => onOpenFood(item)} role="link">
                <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
              </EntityCardAction>
            ) : undefined}
            entity="food"
            eyebrow="Alimento"
            key={item.id}
            nutrition={{
              calories,
              protein: { grams: item.proteinGrams, allocation: macroShare(item.proteinGrams, 4, calories) },
              carbs: { grams: item.carbsGrams, allocation: macroShare(item.carbsGrams, 4, calories) },
              fat: { grams: item.fatGrams, allocation: macroShare(item.fatGrams, 9, calories) },
            }}
            subtitle={`${item.quantity} ${item.quantityUnit}`}
            title={item.name}
          />
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({ list: { gap: tokens.spacing.lg, minWidth: 0 } });
