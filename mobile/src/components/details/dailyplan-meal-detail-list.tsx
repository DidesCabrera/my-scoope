import { StyleSheet, Text, View } from "react-native";

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
        <View key={item.id} style={styles.step}>
          <View style={styles.marker}>
            <View style={styles.markerNumber}>
              <Text style={styles.markerText}>{index + 1}</Text>
            </View>
            {index < items.length - 1 ? <View style={styles.markerLine} /> : null}
          </View>
          <View style={styles.cardSlot}>
            <NutritionEntityCard
              accessory={item.time ? <Pill color={tokens.color.meal} label={item.time} /> : undefined}
              entity="meal"
              indicators={[{ icon: "food", label: "alimentos", value: item.foods.length }]}
              nutrition={item.nutrition}
              style={styles.mealCard}
              title={item.name}>
              <FoodPanels items={item.foods} />
            </NutritionEntityCard>
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  list: { minWidth: 0 },
  step: { minWidth: 0, position: "relative" },
  marker: { alignItems: "center", bottom: 0, left: -18, position: "absolute", top: 0, width: 24 },
  markerNumber: { alignItems: "center", backgroundColor: tokens.color.meal, borderRadius: tokens.radius.pill, height: 24, justifyContent: "center", width: 24, zIndex: 1 },
  markerText: { color: tokens.color.entityIconForeground, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, fontVariant: ["tabular-nums"] },
  markerLine: { backgroundColor: tokens.color.borderDefault, flex: 1, minHeight: tokens.spacing.lg, width: 1 },
  cardSlot: { minWidth: 0, paddingBottom: tokens.spacing.lg, width: "100%" },
  mealCard: { gap: tokens.spacing.sm, padding: tokens.spacing.sm },
});
