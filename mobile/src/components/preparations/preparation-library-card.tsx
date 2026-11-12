import { ChevronRight } from "lucide-react-native";
import { StyleSheet, View } from "react-native";

import type { PersonalPreparation } from "@/api/preparations";
import { tokens } from "@/design/tokens";
import { Chip } from "@/components/ui/chip";
import { EntityCard, EntityCardAction } from "@/components/ui/product";
import { formatPreparationNumber } from "./preparation-ingredients-card";

export function PreparationLibraryCard({ item, onOpen }: { item: PersonalPreparation; onOpen(): void }) {
  const label = item.is_draft ? `Continuar ${item.name}` : `Ver detalle de ${item.name}`;
  return <EntityCard
    accent={tokens.color.preparation}
    actions={<EntityCardAction label={label} onPress={onOpen} role="link"><ChevronRight color={tokens.color.textMuted} size={19} /></EntityCardAction>}
    entity="preparation"
    eyebrow="Preparación"
    headingLink={{ label, onPress: onOpen }}
    style={styles.card}
    title={item.name}>
    <View style={styles.metadata}>
      {item.is_draft ? <Chip backgroundColor={tokens.color.surfaceMuted} borderColor={tokens.color.borderDefault} label="Pendiente de ingredientes" textColor={tokens.color.textMain} /> : <>
      <Chip backgroundColor={tokens.color.surfaceMuted} borderColor={tokens.color.borderDefault} label={`Porción habitual: ${formatPreparationNumber(item.default_portion_g)} g`} textColor={tokens.color.textMain} />
      <Chip backgroundColor={tokens.color.surfaceMuted} borderColor={tokens.color.borderDefault} label={`${item.recipe_ingredients.length} ${item.recipe_ingredients.length === 1 ? "ingrediente" : "ingredientes"}`} textColor={tokens.color.textMain} />
      <Chip backgroundColor={tokens.color.surfaceMuted} borderColor={tokens.color.borderDefault} label={`${formatPreparationNumber(item.nutrition.calories, 0)} kcal`} textColor={tokens.color.textMain} />
      </>}
    </View>
  </EntityCard>;
}

const styles = StyleSheet.create({
  card: { marginHorizontal: -18 },
  metadata: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
});
