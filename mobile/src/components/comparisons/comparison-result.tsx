import { type Href, useRouter } from "expo-router";
import { Scale } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { ComparisonKind, ComparisonMetric, ComparisonResult } from "@/api/types";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";
import { EntityIcon, type EntityKind } from "@/components/ui";
import { Card } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

function libraryHref(kind: ComparisonKind, id: number): Href {
  const segment = kind === "dailyplans" ? "daily-plans" : kind;
  return `/libraries/${segment}/${id}` as Href;
}

function metricColor(metric: ComparisonMetric): string {
  if (metric.key === "total_kcal") return tokens.color.kcalBorder;
  if (metric.key === "ppk") return tokens.color.ppk;
  if (metric.key.includes("protein")) return tokens.color.protein;
  if (metric.key.includes("carbs")) return tokens.color.carbs;
  return tokens.color.fat;
}

function comparisonEntity(kind: ComparisonKind): EntityKind {
  if (kind === "foods") return "food";
  if (kind === "meals") return "meal";
  return "dailyPlan";
}

function compactPercentage(value: string): string {
  return value.replace(/\s+%$/, "%");
}

export function ComparisonResultCards({ hideHeader = false, interactive = true, result }: { hideHeader?: boolean; interactive?: boolean; result: ComparisonResult }) {
  const router = useRouter();
  const entity = comparisonEntity(result.kind);
  const allocationKeys = ["alloc_protein", "alloc_carbs", "alloc_fat"] as const;
  const allocationMetrics = allocationKeys.map((key) => result.metrics.find((metric) => metric.key === key));
  const hasAllocation = allocationMetrics.every((metric) => metric != null);
  const regularMetrics = result.metrics.filter((metric) => !allocationKeys.includes(metric.key as typeof allocationKeys[number]));
  return (
    <View style={styles.container}>
      {!hideHeader ? <ProgramSectionHeader
        icon={Scale}
        subtitle="Observa las diferencias entre las comidas de la forma que más te acomode."
        title="Resultados de la comparación"
      /> : null}
      {regularMetrics.map((metric) => {
        const color = metricColor(metric);
        return (
          <Card accent={tokens.color[entity]} key={metric.key}>
            <View style={styles.metricHeading}>
              <Text style={styles.metricTitle}>{metric.label}</Text>
            </View>
            <View style={styles.bars}>
              {metric.bars.map((bar) => (
                <Pressable
                  accessibilityHint={interactive ? "Abre la entidad en tu librería" : undefined}
                  accessibilityLabel={`${bar.label}, ${bar.formatted_value}`}
                  accessibilityRole={interactive ? "button" : undefined}
                  key={`${bar.position}-${bar.id}`}
                  disabled={!interactive}
                  onPress={() => { if (interactive) router.push(libraryHref(result.kind, bar.id)); }}
                  style={({ pressed }) => [styles.barRow, pressed && styles.pressed]}>
                  <View style={styles.barMeta}>
                    <View style={styles.barIdentity}>
                      <EntityIcon entity={entity} size="compact" />
                      <Text numberOfLines={2} style={styles.barLabel}>
                        {bar.label}{bar.quantity != null ? (
                          <Text style={styles.quantity}> ({Math.round(bar.quantity)}{bar.quantity_unit ?? "g"})</Text>
                        ) : null}
                      </Text>
                    </View>
                    <Text style={styles.barValue}>{bar.formatted_value}</Text>
                  </View>
                  <View style={styles.track}>
                    <View style={[styles.fill, { backgroundColor: color, width: `${Math.max(0, Math.min(bar.relative_percentage, 100))}%` }]} />
                  </View>
                </Pressable>
              ))}
            </View>
          </Card>
        );
      })}
      {hasAllocation ? (
        <Card accent={tokens.color[entity]}>
          <View style={styles.metricHeading}>
            <Text style={styles.metricTitle}>Distribución macros</Text>
          </View>
          <View style={styles.bars}>
            {allocationMetrics[0]!.bars.map((proteinBar) => {
              const carbsBar = allocationMetrics[1]!.bars.find((bar) => bar.position === proteinBar.position)!;
              const fatBar = allocationMetrics[2]!.bars.find((bar) => bar.position === proteinBar.position)!;
              return (
                <Pressable
                  accessibilityHint={interactive ? "Abre la entidad en tu librería" : undefined}
                  accessibilityLabel={`${proteinBar.label}, proteína ${proteinBar.formatted_value}, carbohidratos ${carbsBar.formatted_value}, grasas ${fatBar.formatted_value}`}
                  accessibilityRole={interactive ? "button" : undefined}
                  key={`allocation-${proteinBar.position}-${proteinBar.id}`}
                  disabled={!interactive}
                  onPress={() => { if (interactive) router.push(libraryHref(result.kind, proteinBar.id)); }}
                  style={({ pressed }) => [styles.barRow, pressed && styles.pressed]}>
                  <View style={styles.barMeta}>
                    <View style={styles.barIdentity}>
                      <EntityIcon entity={entity} size="compact" />
                      <Text numberOfLines={2} style={styles.barLabel}>{proteinBar.label}</Text>
                    </View>
                    <View style={styles.allocationLegend}>
                      <Text style={[styles.allocationValue, { color: tokens.color.protein }]}><Text style={styles.allocationKey}>P </Text>{compactPercentage(proteinBar.formatted_value)}</Text>
                      <Text style={[styles.allocationValue, { color: tokens.color.carbs }]}><Text style={styles.allocationKey}>C </Text>{compactPercentage(carbsBar.formatted_value)}</Text>
                      <Text style={[styles.allocationValue, { color: tokens.color.fat }]}><Text style={styles.allocationKey}>F </Text>{compactPercentage(fatBar.formatted_value)}</Text>
                    </View>
                  </View>
                  <View style={styles.allocationTrack}>
                    <View style={[styles.allocationSegment, { backgroundColor: tokens.color.protein, flex: Math.max(proteinBar.value, 0) }]} />
                    <View style={[styles.allocationSegment, { backgroundColor: tokens.color.carbs, flex: Math.max(carbsBar.value, 0) }]} />
                    <View style={[styles.allocationSegment, { backgroundColor: tokens.color.fat, flex: Math.max(fatBar.value, 0) }]} />
                  </View>
                </Pressable>
              );
            })}
          </View>
        </Card>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  allocationLegend: { flexDirection: "row", flexShrink: 0, gap: tokens.spacing.sm },
  allocationKey: { color: tokens.color.textMain, fontWeight: tokens.weight.regular },
  allocationSegment: { height: "100%" },
  allocationTrack: { borderRadius: tokens.radius.pill, flexDirection: "row", height: 10, overflow: "hidden" },
  allocationValue: { fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: "700" },
  barIdentity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.xs, minWidth: 0 },
  barLabel: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.caption, fontWeight: "700" },
  barMeta: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  barRow: { gap: tokens.spacing.sm },
  barValue: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: "700" },
  bars: { gap: tokens.spacing.lg },
  container: { gap: tokens.spacing.md },
  fill: { borderRadius: 5, height: "100%" },
  metricHeading: { alignItems: "baseline", flexDirection: "row", justifyContent: "space-between" },
  metricTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  pressed: { opacity: 0.7 },
  quantity: { color: tokens.color.textSoft, fontWeight: "500" },
  track: { backgroundColor: tokens.color.allocationPanelTrack, borderRadius: tokens.radius.pill, height: 10, overflow: "hidden" },
});
