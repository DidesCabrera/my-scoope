import { Fragment } from "react";
import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

import { formatNutritionPortion, nutritionFactRows, type NutritionFacts } from "./nutrition-facts";
import { Card } from "./surfaces";
import { SectionTitle } from "./typography";

export type NutritionFactsCardProps = {
  facts: NutritionFacts;
  portion: { quantity: number | null; unit: "g" | "ml" };
};

export function NutritionFactsCard({ facts, portion }: NutritionFactsCardProps) {
  const rows = nutritionFactRows(facts, portion.quantity);
  return (
    <Fragment>
      <SectionTitle detail={`Tamaño porción aprox: ${formatNutritionPortion(portion.quantity, portion.unit)}`} title="Información Nutricional" />
      <Card muted style={styles.card}>
        <View style={styles.table}>
          <View accessibilityRole="header" style={[styles.row, styles.header]}>
            <Text style={[styles.headerText, styles.labelColumn]}>Nutriente</Text>
            <Text style={[styles.headerText, styles.valueColumn]}>{`100 ${portion.unit}`.toUpperCase()}</Text>
            <Text style={[styles.headerText, styles.valueColumn, styles.portionColumn]}>PORCIÓN</Text>
          </View>
          {rows.map((row, index) => (
            <View key={row.id} style={[styles.row, index === rows.length - 1 && styles.lastRow]}>
              <Text style={[styles.label, styles.labelColumn, row.emphasized && styles.labelEmphasized]}>{row.label}</Text>
              <Text adjustsFontSizeToFit minimumFontScale={0.72} numberOfLines={1} style={[styles.value, styles.valueColumn, row.emphasized && styles.valueEmphasized]}>{row.per100Value}</Text>
              <Text adjustsFontSizeToFit minimumFontScale={0.72} numberOfLines={1} style={[styles.value, styles.valueColumn, styles.portionColumn, row.emphasized && styles.valueEmphasized]}>{row.portionValue}</Text>
            </View>
          ))}
        </View>
      </Card>
    </Fragment>
  );
}

const styles = StyleSheet.create({
  card: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, marginTop: -(tokens.spacing.sm + 2), paddingBottom: tokens.spacing.sm, paddingTop: tokens.spacing.sm + 2 },
  table: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, marginTop: -tokens.spacing.xs },
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", minHeight: 46 },
  lastRow: { borderBottomWidth: 0 },
  header: { backgroundColor: tokens.color.surfaceMuted, minHeight: 32 },
  headerText: { color: tokens.color.textMuted, fontSize: 10, fontWeight: tokens.weight.semibold, textTransform: "uppercase" },
  labelColumn: { flex: 1, minWidth: 0, paddingHorizontal: tokens.spacing.xs, textAlign: "left" },
  valueColumn: { flexGrow: 0, flexShrink: 0, textAlign: "center", width: 64 },
  portionColumn: { marginLeft: tokens.spacing.lg },
  label: { color: tokens.color.textMain, fontSize: 14, lineHeight: 20 },
  labelEmphasized: { fontWeight: tokens.weight.bold },
  value: { color: tokens.color.textMain, fontSize: 13, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.regular, lineHeight: 20 },
  valueEmphasized: { fontWeight: tokens.weight.bold },
});
