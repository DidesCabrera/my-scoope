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
            <View style={styles.markerLine} />
            <View style={styles.markerNumber}>
              <Text style={styles.markerText}>{index + 1}</Text>
            </View>
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
  step: { gap: tokens.spacing.sm, minWidth: 0 },
  marker: { alignItems: "center", height: 36, justifyContent: "center", paddingHorizontal: tokens.spacing.xs, position: "relative", width: "100%" },
  markerNumber: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, height: 36, justifyContent: "center", left: tokens.spacing.xs, position: "absolute", width: 36, zIndex: 1 },
  markerText: { color: tokens.color.textMuted, fontSize: 18, fontWeight: tokens.weight.semibold, fontVariant: ["tabular-nums"] },
  markerLine: { backgroundColor: tokens.color.borderDefault, height: 1, width: "100%" },
  cardSlot: { minWidth: 0, paddingBottom: tokens.spacing.lg, width: "100%" },
  mealCard: { gap: tokens.spacing.sm, padding: tokens.spacing.sm },
});
