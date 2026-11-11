import { ChevronRight } from "lucide-react-native";
import { StyleSheet, View } from "react-native";

import type { PreparationDetail } from "@/api/preparations";
import { tokens } from "@/design/tokens";
import { Chip } from "@/components/ui/chip";
import { EntityCard, EntityCardAction } from "@/components/ui/product";
import { formatPreparationNumber } from "./preparation-ingredients-card";

export function PreparationLibraryCard({ item, onOpen }: { item: PreparationDetail; onOpen(): void }) {
  const label = `Ver detalle de ${item.name}`;
  return <EntityCard
    accent={tokens.color.preparation}
    actions={<EntityCardAction label={label} onPress={onOpen} role="link"><ChevronRight color={tokens.color.textMuted} size={19} /></EntityCardAction>}
    entity="preparation"
    eyebrow="Preparación"
    headingLink={{ label, onPress: onOpen }}
    style={styles.card}
    title={item.name}>
    <View style={styles.metadata}>
      <Chip backgroundColor={tokens.color.surfaceMuted} borderColor={tokens.color.borderDefault} label={`${formatPreparationNumber(item.default_portion_g)} g por ${item.household_label}`} textColor={tokens.color.textMain} />
      <Chip backgroundColor={tokens.color.surfaceMuted} borderColor={tokens.color.borderDefault} label={`${item.recipe_ingredients.length} ${item.recipe_ingredients.length === 1 ? "ingrediente" : "ingredientes"}`} textColor={tokens.color.textMain} />
      <Chip backgroundColor={tokens.color.surfaceMuted} borderColor={tokens.color.borderDefault} label={`${formatPreparationNumber(item.nutrition.calories, 0)} kcal`} textColor={tokens.color.textMain} />
    </View>
  </EntityCard>;
}

const styles = StyleSheet.create({
  card: { marginHorizontal: -18 },
  metadata: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
});
