import { StyleSheet, Text, View } from "react-native";

import type { LibraryPreparationPanelItem } from "@/api/preparations";
import { Button } from "@/components/ui/controls";
import { Card } from "@/components/ui/surfaces";
import { tokens } from "@/design/tokens";

import { PreparationIngredientsCard, formatPreparationAllergens, formatPreparationNumber } from "./preparation-ingredients-card";

export function MealPreparationCard({ onEdit, onOpenFood, onRemove, preparation }: {
  onEdit(): void;
  onOpenFood(foodId: number): void;
  onRemove(): void;
  preparation: LibraryPreparationPanelItem;
}) {
  const portion = preparation.selection_mode === "units"
    ? `${formatPreparationNumber(preparation.selected_units ?? 1)} ${preparation.household_label}`
    : `${formatPreparationNumber(preparation.quantity_g)} g`;

  return <View style={styles.group}>
    <Card accent={tokens.color.meal}>
      <Text style={styles.eyebrow}>PREPARACIÓN</Text>
      <Text style={styles.name}>{preparation.name}</Text>
      <Text style={styles.portion}>{portion} · aprox. {formatPreparationNumber(preparation.quantity_g)} g</Text>
      <View style={styles.energyRow}><Text style={styles.calories}>{formatPreparationNumber(preparation.calories, 0)}</Text><Text style={styles.energyUnit}>kcal</Text></View>
      <View style={styles.infoRow}><Text style={styles.infoLabel}>Sodio</Text><Text style={styles.infoValue}>{preparation.sodium_mg == null ? "Sin dato" : `${formatPreparationNumber(preparation.sodium_mg, 0)} mg`}</Text></View>
      <View style={styles.infoRow}><Text style={styles.infoLabel}>Alérgenos declarados</Text><Text style={styles.infoValue}>{formatPreparationAllergens(preparation.allergens)}</Text></View>
      <View style={styles.actions}>
        <Button bleed={false} label="Editar porción" onPress={onEdit} variant="secondary" />
        <Button bleed={false} label="Quitar preparación" onPress={onRemove} variant="danger" />
      </View>
    </Card>
    <PreparationIngredientsCard ingredients={preparation.ingredients} onOpenFood={onOpenFood} />
  </View>;
}

const styles = StyleSheet.create({
  group: { gap: tokens.spacing.md, marginBottom: tokens.spacing.lg },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.semibold, letterSpacing: 1.1 },
  name: { color: tokens.color.textMain, fontSize: 23, fontWeight: tokens.weight.extraBold, lineHeight: 29 },
  portion: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 19 },
  energyRow: { alignItems: "baseline", flexDirection: "row", gap: tokens.spacing.xs },
  calories: { color: tokens.color.textMain, fontSize: 30, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.extraBold },
  energyUnit: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  infoRow: { flexDirection: "row", justifyContent: "space-between", gap: tokens.spacing.md },
  infoLabel: { color: tokens.color.textMuted, flex: 1, fontSize: tokens.type.caption },
  infoValue: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, textAlign: "right" },
  actions: { gap: tokens.spacing.sm, marginTop: tokens.spacing.xs },
});
