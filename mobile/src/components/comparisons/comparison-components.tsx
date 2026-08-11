import { ChevronDown, ChevronRight, Trash2 } from "lucide-react-native";
import type { PropsWithChildren, ReactNode } from "react";
import { Pressable, StyleSheet, Text, TextInput, useWindowDimensions, View } from "react-native";

import { Button, EntityIcon, SectionHeading, SectionIcon, type EntityKind } from "@/components/ui";
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

export function ComparisonEditorCard({
  entity,
  index,
  label,
  onOpenSelector,
  onQuantityChange,
  onRemove,
  quantity,
}: {
  entity: ComparisonScope;
  index: number;
  label?: string;
  onOpenSelector?: () => void;
  onQuantityChange?: (value: string) => void;
  onRemove?: () => void;
  quantity?: string;
}) {
  const singularLabel = scopeSingularLabels[entity];
  const supportsQuantity = entity !== "dailyPlan";

  return (
    <View style={styles.editorCard}>
      <View style={styles.selectionHeading}>
        <View style={styles.selectionIdentity}>
          <View style={styles.selectionNumber}><Text style={styles.selectionNumberText}>{index}</Text></View>
          <View style={styles.selectionCopy}>
            <Text style={styles.selectionEyebrow}>{singularLabel} {index}</Text>
            {label ? <Text numberOfLines={1} style={styles.editorSelectedName}>{label}{quantity ? <Text style={styles.metricSuffix}> ({quantity}g)</Text> : null}</Text> : null}
          </View>
        </View>
        {onRemove ? (
          <Pressable accessibilityLabel={`Quitar ${label ?? "selección"}`} accessibilityRole="button" hitSlop={8} onPress={onRemove} style={({ pressed }) => [styles.removeButton, pressed && styles.pressed]}>
            <Trash2 color={tokens.color.textMuted} size={15} />
          </Pressable>
        ) : null}
      </View>

      <View style={styles.editorField}>
        <Text style={styles.editorFieldLabel}>{singularLabel}</Text>
        <Pressable accessibilityLabel={`Seleccionar ${singularLabel.toLowerCase()}`} accessibilityRole="button" onPress={onOpenSelector} style={({ pressed }) => [styles.editorSelect, pressed && styles.pressed]}>
          <Text numberOfLines={1} style={[styles.editorInputText, !label && styles.editorPlaceholder]}>{label ?? `Seleccionar ${singularLabel.toLowerCase()}`}</Text>
          <ChevronDown color={tokens.color.textMuted} size={16} />
        </Pressable>
      </View>

      {supportsQuantity && label ? (
        <View style={[styles.editorField, styles.quantityField]}>
          <Text style={styles.editorFieldLabel}>Cantidad</Text>
          <View style={styles.quantityInputWrap}>
            <TextInput
              accessibilityLabel="Cantidad en gramos"
              inputMode="numeric"
              onChangeText={onQuantityChange}
              style={styles.quantityInput}
              value={quantity}
            />
            <Text style={styles.quantityUnit}>g</Text>
          </View>
        </View>
      ) : null}
    </View>
  );
}

export function ComparisonBuilder({ addActionLabel, children, onAdd, onCompare, onSave, scope }: { addActionLabel?: string; children: React.ReactNode; onAdd?: () => void; onCompare?: () => void; onSave?: () => void; scope: ComparisonScope }) {
  const resolvedAddActionLabel = addActionLabel ?? `Agregar ${scopeSingularLabels[scope].toLowerCase()}`;
  return (
    <View style={styles.builder}>
      <View style={styles.builderEyebrow}>
        <SectionIcon section="comparator" size="compact" />
        <Text style={styles.builderEyebrowText}>Nueva comparación</Text>
      </View>
      <View style={styles.builderSelections}>{children}</View>
      <View style={styles.builderActions}>
        {onAdd ? <Button label={resolvedAddActionLabel} onPress={onAdd} variant="secondary" /> : null}
        {onSave ? <Button label="Guardar comparación" onPress={onSave} variant="secondary" /> : null}
        {onCompare ? <Button label="Comparar" onPress={onCompare} /> : null}
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

export function SavedComparisonDetailPage({
  children,
  itemCount,
  onEdit,
  scope,
  selections,
  title,
}: PropsWithChildren<{
  itemCount: number;
  onEdit?: () => void;
  scope: ComparisonScope;
  selections: ReactNode;
  title: string;
}>) {
  const { width } = useWindowDimensions();
  const titleSize = width < 420 ? 22 : 24;
  const titleLineHeight = width < 420 ? 32 : 34;

  return (
    <View style={styles.savedDetailPage}>
      <View style={styles.savedDetailHero}>
        <View style={styles.builderEyebrow}>
          <SectionIcon section="comparator" size="compact" />
          <Text style={styles.builderEyebrowText}>Comparación guardada</Text>
        </View>
        <Text style={[styles.savedDetailTitle, { fontSize: titleSize, lineHeight: titleLineHeight }]}>{title}</Text>
        <View accessibilityLabel={`${itemCount} ${scopeLabels[scope].toLowerCase()}`} style={styles.savedDetailCount}>
          <Text style={styles.savedDetailCountValue}>{itemCount}</Text>
          <EntityIcon entity={scope} size="compact" />
        </View>
      </View>

      <View style={styles.savedDetailSection}>
        <SectionHeading detail={`${itemCount} ${scopeLabels[scope].toLowerCase()}`} title="Elementos comparados" />
        <View style={styles.savedDetailSelections}>{selections}</View>
      </View>

      <View style={styles.savedDetailSection}>
        <SectionHeading title="Resultados comparativos" />
        <View style={styles.savedDetailResults}>{children}</View>
      </View>

      {onEdit ? <Button label="Editar comparación" onPress={onEdit} variant="secondary" /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.7 },
  scopeTabs: { flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  scopeTab: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, flex: 1, flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "center", minHeight: 40, minWidth: 0, paddingHorizontal: tokens.spacing.sm },
  scopeTabSelected: { backgroundColor: tokens.color.textMain, borderColor: "transparent" },
  scopeTabLabel: { color: tokens.color.textMuted, flexShrink: 1, fontSize: tokens.type.label, fontWeight: tokens.weight.semibold },
  scopeTabLabelSelected: { color: tokens.color.surfaceApp },
  selectionCard: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, padding: tokens.spacing.md },
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
  builder: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.md, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, padding: tokens.card.outerPadding },
  builderEyebrow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  builderEyebrowText: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, letterSpacing: 0, textTransform: "uppercase" },
  builderSelections: { gap: tokens.spacing.sm },
  editorCard: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, gap: tokens.spacing.md, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, padding: tokens.spacing.md },
  editorSelectedName: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  editorField: { gap: tokens.spacing.compact },
  editorFieldLabel: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.semibold },
  editorSelect: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 40, paddingHorizontal: tokens.spacing.sm },
  editorInputText: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular },
  editorPlaceholder: { color: tokens.color.textMuted },
  quantityField: { maxWidth: 150 },
  quantityInputWrap: { justifyContent: "center" },
  quantityInput: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, color: tokens.color.textMain, fontSize: tokens.type.caption, minHeight: 40, paddingHorizontal: tokens.spacing.sm, paddingRight: 34 },
  quantityUnit: { color: tokens.color.textSoft, fontSize: tokens.type.label, position: "absolute", right: tokens.spacing.sm },
  builderActions: { gap: tokens.spacing.sm },
  metricCard: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.md, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, padding: tokens.card.outerPadding },
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
  savedDetailPage: { alignSelf: "stretch", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.lg, marginHorizontal: -tokens.spacing.screen, minWidth: 0, padding: tokens.card.outerPadding },
  savedDetailHero: { gap: tokens.spacing.compact, minWidth: 0 },
  savedDetailTitle: { color: tokens.color.textMain, fontWeight: tokens.weight.semibold, letterSpacing: 0 },
  savedDetailCount: { alignItems: "center", alignSelf: "flex-start", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.compact, minHeight: 30, paddingHorizontal: tokens.spacing.sm },
  savedDetailCountValue: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold },
  savedDetailSection: { gap: tokens.spacing.sm, minWidth: 0 },
  savedDetailSelections: { gap: tokens.spacing.sm },
  savedDetailResults: { gap: tokens.spacing.sm },
});
