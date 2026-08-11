import { ChevronRight, Trash2 } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { EntityIcon, type EntityKind } from "@/components/ui";
import { tokens } from "@/design/tokens";

export type ComparisonScope = Extract<EntityKind, "food" | "meal" | "dailyPlan">;
export type ComparisonMetricTone = "calories" | "ppk" | "protein" | "carbs" | "fat";

const scopeLabels: Record<ComparisonScope, string> = {
  food: "Alimentos",
  meal: "Comidas",
  dailyPlan: "Planes",
};

const scopeSingularLabels: Record<ComparisonScope, string> = {
  food: "Alimento",
  meal: "Comida",
  dailyPlan: "Plan",
};

const metricColors: Record<ComparisonMetricTone, string> = {
  calories: "#7B5B39",
  ppk: tokens.color.ppk,
  protein: tokens.color.protein,
  carbs: tokens.color.carbs,
  fat: tokens.color.fat,
};

export function ComparisonScopeTabs({ activeScope, onChange }: { activeScope: ComparisonScope; onChange: (scope: ComparisonScope) => void }) {
  return (
    <View accessibilityLabel="Tipo de comparación" accessibilityRole="tablist" style={styles.scopeTabs}>
      {(Object.keys(scopeLabels) as ComparisonScope[]).map((scope) => {
        const selected = activeScope === scope;
        return (
          <Pressable
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            key={scope}
            onPress={() => onChange(scope)}
            style={({ pressed }) => [styles.scopeTab, selected && styles.scopeTabSelected, pressed && styles.pressed]}>
            <EntityIcon entity={scope} size="compact" />
            <Text style={[styles.scopeTabLabel, selected && styles.scopeTabLabelSelected]}>{scopeLabels[scope]}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function ComparisonSelectionCard({
  entity,
  index,
  label,
  onRemove,
  quantity,
}: {
  entity: ComparisonScope;
  index: number;
  label?: string;
  onRemove?: () => void;
  quantity?: string;
}) {
  return (
    <View style={styles.selectionCard}>
      <View style={styles.selectionHeading}>
        <View style={styles.selectionIdentity}>
          <View style={styles.selectionNumber}><Text style={styles.selectionNumberText}>{index}</Text></View>
          <View style={styles.selectionCopy}>
            <Text style={styles.selectionEyebrow}>{scopeSingularLabels[entity]} {index}</Text>
            <View style={styles.selectionNameRow}>
              <EntityIcon entity={entity} size="compact" />
              <Text numberOfLines={1} style={styles.selectionName}>{label ?? `Seleccionar ${scopeSingularLabels[entity].toLowerCase()}`}</Text>
              {quantity ? <Text style={styles.selectionQuantity}>{quantity}</Text> : null}
            </View>
          </View>
        </View>
        {onRemove ? (
          <Pressable accessibilityLabel={`Quitar ${label ?? "selección"}`} accessibilityRole="button" hitSlop={8} onPress={onRemove} style={({ pressed }) => [styles.removeButton, pressed && styles.pressed]}>
            <Trash2 color={tokens.color.textMuted} size={15} />
          </Pressable>
        ) : null}
      </View>
    </View>
  );
}

export type ComparisonBarItem = {
  entity: ComparisonScope;
  formattedValue: string;
  id: string;
  label: string;
  labelSuffix?: string;
  width: number;
};

export function ComparisonMetricCard({ items, label, tone, unit }: { items: ComparisonBarItem[]; label: string; tone: ComparisonMetricTone; unit: string }) {
  const color = metricColors[tone];
  return (
    <View style={styles.metricCard}>
      <View style={styles.metricHeader}>
        <Text style={styles.metricTitle}>{label}</Text>
        <Text style={styles.metricUnit}>{unit}</Text>
      </View>
      <View style={styles.metricBars}>
        {items.map((item) => {
          const width = Math.max(0, Math.min(item.width, 100));
          return (
            <View key={item.id} style={styles.metricRow}>
              <View style={styles.metricMeta}>
                <EntityIcon entity={item.entity} size="compact" />
                <Text numberOfLines={1} style={styles.metricLabel}>{item.label}{item.labelSuffix ? <Text style={styles.metricSuffix}> {item.labelSuffix}</Text> : null}</Text>
                <Text style={styles.metricValue}>{item.formattedValue}</Text>
              </View>
              <View accessibilityLabel={`${item.label}: ${item.formattedValue}`} accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: width }} style={styles.metricTrack}>
                <View style={[styles.metricFill, { backgroundColor: color, width: `${width}%` }]} />
              </View>
            </View>
          );
        })}
      </View>
    </View>
  );
}

export function SavedComparisonCard({ entity, onPress, preview, subtitle, title }: { entity: ComparisonScope; onPress?: () => void; preview: string; subtitle: string; title: string }) {
  return (
    <Pressable accessibilityRole={onPress ? "button" : undefined} disabled={!onPress} onPress={onPress} style={({ pressed }) => [styles.savedCard, pressed && styles.pressed]}>
      <EntityIcon entity={entity} size="hero" />
      <View style={styles.savedCopy}>
        <Text numberOfLines={1} style={styles.savedTitle}>{title}</Text>
        <Text numberOfLines={1} style={styles.savedSubtitle}>{subtitle}</Text>
        <Text numberOfLines={1} style={styles.savedPreview}>{preview}</Text>
      </View>
      <ChevronRight color={tokens.color.textMuted} size={18} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.7 },
  scopeTabs: { flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  scopeTab: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, flex: 1, flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "center", minHeight: 40, minWidth: 0, paddingHorizontal: tokens.spacing.sm },
  scopeTabSelected: { backgroundColor: tokens.color.textMain, borderColor: "transparent" },
  scopeTabLabel: { color: tokens.color.textMuted, flexShrink: 1, fontSize: tokens.type.label, fontWeight: tokens.weight.semibold },
  scopeTabLabelSelected: { color: tokens.color.surfaceApp },
  selectionCard: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, padding: tokens.spacing.md },
  selectionHeading: { alignItems: "flex-start", flexDirection: "row", justifyContent: "space-between", minWidth: 0 },
  selectionIdentity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  selectionNumber: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, height: 28, justifyContent: "center", width: 28 },
  selectionNumberText: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  selectionCopy: { flex: 1, gap: tokens.spacing.xs, minWidth: 0 },
  selectionEyebrow: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.semibold },
  selectionNameRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
  selectionName: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  selectionQuantity: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.regular },
  removeButton: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, height: 32, justifyContent: "center", width: 32 },
  metricCard: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.md, padding: tokens.card.outerPadding },
  metricHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  metricTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  metricUnit: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  metricBars: { gap: tokens.spacing.md },
  metricRow: { gap: tokens.spacing.compact },
  metricMeta: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  metricLabel: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  metricSuffix: { color: tokens.color.textMuted, fontWeight: tokens.weight.regular },
  metricValue: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold },
  metricTrack: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, height: 11, overflow: "hidden" },
  metricFill: { borderRadius: tokens.radius.pill, height: "100%" },
  savedCard: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.md, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 82, padding: tokens.spacing.md },
  savedCopy: { flex: 1, gap: tokens.spacing.xs, minWidth: 0 },
  savedTitle: { color: tokens.color.textMain, fontSize: 15, fontWeight: tokens.weight.bold },
  savedSubtitle: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.semibold },
  savedPreview: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.medium },
});
