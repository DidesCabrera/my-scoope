import { StyleSheet, View } from "react-native";

import {
  NutritionEntityCard,
  type NutritionEntityCardProps,
} from "@/components/nutrition";
import { FoodPanels, type FoodPanelItem } from "@/components/panels";
import { Pill } from "@/components/ui";
import { tokens } from "@/design/tokens";

export type DailyPlanMealDetailItem = {
  id: string;
  name: string;
  time?: string;
  foods: FoodPanelItem[];
  nutrition: NutritionEntityCardProps["nutrition"];
};

export function DailyPlanMealDetailList({ items }: { items: DailyPlanMealDetailItem[] }) {
  return (
    <View style={styles.list}>
      {items.map((item, index) => (
        <View key={item.id} style={styles.cardSlot}>
          <NutritionEntityCard
            accessory={item.time ? <Pill color={tokens.color.meal} label={item.time} /> : undefined}
            entity="meal"
            eyebrow={`Comida ${index + 1}`}
            indicators={[{ icon: "food", label: "alimentos", value: item.foods.length }]}
            nutrition={item.nutrition}
            title={item.name}>
            <FoodPanels items={item.foods} />
          </NutritionEntityCard>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  list: { minWidth: 0 },
  cardSlot: { minWidth: 0, paddingBottom: tokens.spacing.lg, width: "100%" },
});
