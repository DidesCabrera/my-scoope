import { ChevronRight } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { ComparisonKind, SavedComparisonSummary } from "@/api/types";
import { Card } from "@/components/ui/primitives";
import { Chip, EntityCardAction, EntityCardActions, EntityIcon } from "@/components/ui";
import { tokens } from "@/design/tokens";

import { SavedComparisonPreviewPanels } from "./comparison-components";

const comparisonEntities = {
  foods: "food",
  meals: "meal",
  dailyplans: "dailyPlan",
} as const satisfies Record<ComparisonKind, "food" | "meal" | "dailyPlan">;

const comparisonEntityColors: Record<ComparisonKind, string> = {
  foods: tokens.color.food,
  meals: tokens.color.meal,
  dailyplans: tokens.color.dailyPlan,
};

const comparisonCountLabels: Record<ComparisonKind, { plural: string; singular: string }> = {
  foods: { plural: "Alimentos", singular: "Alimento" },
  meals: { plural: "Comidas", singular: "Comida" },
  dailyplans: { plural: "Planes diarios", singular: "Plan diario" },
};

function comparisonCountLabel(kind: ComparisonKind, count: number) {
  const labels = comparisonCountLabels[kind];
  return `${count} ${count === 1 ? labels.singular : labels.plural}`;
}

export function SavedComparisonListCard({ item, onPress }: { item: SavedComparisonSummary; onPress(): void }) {
  const entity = comparisonEntities[item.kind];
  const entityColor = comparisonEntityColors[item.kind];
  return (
    <Card accent={entityColor} style={styles.savedCard}>
      <Pressable
        accessibilityLabel={`Ver detalle de ${item.name}`}
        accessibilityRole="link"
        onPress={onPress}
        style={({ pressed }) => [styles.savedCopy, pressed && styles.pressed]}>
        <View style={styles.savedEyebrow}>
          <EntityIcon entity={entity} size="compact" />
          <Text style={styles.savedEyebrowText}>Comparación {item.kind_label}</Text>
        </View>
        <Text style={styles.savedTitle}>{item.name}</Text>
        <View style={styles.savedChip}>
          <Chip backgroundColor={`${entityColor}1A`} borderColor={entityColor} label={comparisonCountLabel(item.kind, item.item_count)} textColor={tokens.color.entityIconForeground} />
        </View>
      </Pressable>
      <SavedComparisonPreviewPanels items={item.items} scope={entity} />
      <EntityCardActions>
        <EntityCardAction label={`Ver detalle de ${item.name}`} onPress={onPress} role="link">
          <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
        </EntityCardAction>
      </EntityCardActions>
    </Card>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.68 },
  savedCard: { paddingBottom: tokens.card.innerPadding },
  savedChip: { alignItems: "flex-start", marginTop: tokens.spacing.xs },
  savedCopy: { flex: 1, gap: tokens.spacing.xs },
  savedEyebrow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  savedEyebrowText: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, textTransform: "uppercase" },
  savedTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
});
