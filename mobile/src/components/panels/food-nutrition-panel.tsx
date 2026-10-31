import { StyleSheet, Text, View } from "react-native";

import { NutritionFactsTable } from "@/components/ui";
import type { NutritionFacts } from "@/components/ui/nutrition-facts";
import { formatNutritionPortion } from "@/components/ui/nutrition-facts";
import { tokens } from "@/design/tokens";

import { PanelBody, PanelSurface } from "./panel-surface";

export function FoodNutritionPanel({ facts, portion }: { facts: NutritionFacts; portion: { quantity: number | null; unit: "g" | "ml" } }) {
  return (
    <PanelSurface>
      <View style={styles.heading}>
        <Text style={styles.title}>Información nutricional</Text>
        <Text style={styles.detail}>{`Porción aprox: ${formatNutritionPortion(portion.quantity, portion.unit)}`}</Text>
      </View>
      <PanelBody>
        <NutritionFactsTable facts={facts} portion={portion} style={styles.table} />
      </PanelBody>
    </PanelSurface>
  );
}

const styles = StyleSheet.create({
  detail: { color: tokens.color.textMuted, fontSize: tokens.type.label },
  heading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "space-between", paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.sm },
  table: { paddingHorizontal: tokens.spacing.xs },
  title: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
});
