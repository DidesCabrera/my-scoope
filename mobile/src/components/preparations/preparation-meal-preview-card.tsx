import { type Href, useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import type { PreparationDetail } from "@/api/preparations";
import type { LibraryItem } from "@/api/types";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";
import { NutritionEntityCard } from "@/components/nutrition";
import { FoodPanels } from "@/components/panels";
import { tokens } from "@/design/tokens";
import { formatPreparationNumber } from "./preparation-ingredients-card";
import { projectPreparationMeal } from "./preparation-meal-preview";

export function PreparationMealPreviewCard({ meal, selected, relationId }: { meal: LibraryItem; selected: PreparationDetail; relationId?: number }) {
  const router = useRouter();
  const preview = projectPreparationMeal(meal, selected, relationId);
  if (!preview) return null;
  const contribution = preview.contribution;
  return <NutritionEntityCard
    afterNutrition={<View style={styles.contribution}>
      <Text style={styles.contributionLabel}>Aporte de {selected.name}</Text>
      <Text style={styles.contributionValue}>{formatPreparationNumber(contribution.calories, 0)} kcal · P {formatPreparationNumber(contribution.protein_g)} g · C {formatPreparationNumber(contribution.carbs_g)} g · G {formatPreparationNumber(contribution.fat_g)} g</Text>
    </View>}
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

const styles = StyleSheet.create({
  contribution: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.panel, gap: 3, marginHorizontal: -6, marginTop: tokens.spacing.sm, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.sm },
  contributionLabel: { color: tokens.color.textSoft, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  contributionValue: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
});
