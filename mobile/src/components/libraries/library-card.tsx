import { type Href, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { Pressable, StyleSheet } from "react-native";
import type { LibraryItem } from "@/api/types";
import { tokens } from "@/design/tokens";

import { FoodPanels, MealPanels, ProgramPanels } from "./entity-panels";
import { NutritionEntityCard } from "./nutrition-entity-card";

export function LibraryCard({ item }: { item: LibraryItem }) {
  const router = useRouter();
  const segment = item.entity === "dailyPlan" ? "daily-plans" : item.entity === "program" ? "programs" : item.entity === "meal" ? "meals" : "foods";
  const detailHref = `/libraries/${segment}/${item.id}` as Href;
  return (
    <NutritionEntityCard entity={item.entity} indicators={item.indicators} nutrition={item.nutrition} subtitle={item.subtitle || undefined} title={item.name}>
      {item.panel.kind === "foods" ? <FoodPanels items={item.panel.foods} /> : null}
      {item.panel.kind === "meals" ? <MealPanels items={item.panel.meals} /> : null}
      {item.panel.kind === "weeks" ? <ProgramPanels items={item.panel.weeks} /> : null}
      <Pressable accessibilityLabel={`Ver detalle de ${item.name}`} accessibilityRole="button" hitSlop={8} onPress={() => router.push(detailHref)} style={({ pressed }) => [styles.detailButton, pressed && styles.pressed]}>
        <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
      </Pressable>
    </NutritionEntityCard>
  );
}

const styles = StyleSheet.create({
  detailButton: { alignItems: "center", alignSelf: "flex-end", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  pressed: { opacity: 0.6 },
});
