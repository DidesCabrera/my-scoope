import { StyleSheet, Text, View } from "react-native";

import type { ProposalDailyPlan, ProposalFact, ProposalKpis, ProposalMeal } from "@/api/types";
import { Card, Pill, SectionTitle, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

function value(value: number | null): string {
  return value == null ? "—" : Math.round(value).toString();
}

function Kpis({ kpis }: { kpis: ProposalKpis | null }) {
  if (!kpis) return null;
  return (
    <View style={styles.kpis}>
      <View style={styles.kpi}><Text style={styles.kpiValue}>{value(kpis.total_kcal)}</Text><Text style={textStyles.caption}>kcal</Text></View>
      <View style={styles.kpi}><Text style={[styles.kpiValue, { color: tokens.color.protein }]}>{value(kpis.protein)} g</Text><Text style={textStyles.caption}>Proteína</Text></View>
      <View style={styles.kpi}><Text style={[styles.kpiValue, { color: tokens.color.carbs }]}>{value(kpis.carbs)} g</Text><Text style={textStyles.caption}>Carbos</Text></View>
      <View style={styles.kpi}><Text style={[styles.kpiValue, { color: tokens.color.fat }]}>{value(kpis.fat)} g</Text><Text style={textStyles.caption}>Grasas</Text></View>
    </View>
  );
}

export function ProposalFacts({ title, facts }: { title: string; facts: ProposalFact[] }) {
  if (!facts.length) return null;
  return (
    <Card muted>
      <SectionTitle title={title} />
      {facts.map((fact, index) => <View key={`${fact.label}-${index}`} style={styles.fact}><Text style={textStyles.muted}>{fact.label}</Text><Text style={textStyles.strong}>{fact.value}</Text></View>)}
    </Card>
  );
}

export function ProposalMealPreview({ meal, title = "Comida propuesta" }: { meal: ProposalMeal; title?: string }) {
  return (
    <Card accent={tokens.color.meal}>
      <View style={styles.header}><View style={styles.copy}><Text style={styles.eyebrow}>{title}</Text><Text style={styles.name}>{meal.name || "Comida"}</Text></View><Pill color={tokens.color.meal} label={`${meal.foods.length} alimentos`} /></View>
      <Kpis kpis={meal.kpis} />
      {meal.foods.map((food, index) => <View key={`${food.food_id}-${food.food_name}-${index}`} style={styles.food}><Text style={styles.foodName}>{food.food_name || "Alimento"}</Text><Text style={textStyles.caption}>{food.quantity == null ? "—" : `${Math.round(food.quantity)} ${food.unit}`}</Text></View>)}
    </Card>
  );
}

export function ProposalDailyPlanPreview({ dailyplan }: { dailyplan: ProposalDailyPlan }) {
  return (
    <View style={styles.stack}>
      <Card accent={tokens.color.dailyPlan}>
        <View style={styles.header}><View style={styles.copy}><Text style={styles.dailyEyebrow}>PLAN DIARIO PROPUESTO</Text><Text style={styles.name}>{dailyplan.name || "Plan diario"}</Text></View><Pill color={tokens.color.dailyPlan} label={`${dailyplan.meals.length} comidas`} /></View>
        <Kpis kpis={dailyplan.kpis} />
      </Card>
      {dailyplan.meals.map((item, index) => <ProposalMealPreview key={`${item.hour}-${item.meal.name}-${index}`} meal={item.meal} title={item.hour ? `${item.hour.slice(0, 5)} · ${item.note || "Comida"}` : item.note || "Comida"} />)}
    </View>
  );
}

const styles = StyleSheet.create({
  copy: { flex: 1, gap: 4 },
  dailyEyebrow: { color: tokens.color.dailyPlan, fontSize: 11, fontWeight: "900", letterSpacing: 1.1 },
  eyebrow: { color: tokens.color.meal, fontSize: 11, fontWeight: "900", letterSpacing: 1.1, textTransform: "uppercase" },
  fact: { alignItems: "center", borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", paddingTop: 10 },
  food: { alignItems: "center", borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", paddingTop: 10 },
  foodName: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontWeight: "700" },
  header: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  kpi: { gap: 2, minWidth: "21%" },
  kpis: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm, justifyContent: "space-between" },
  kpiValue: { color: tokens.color.textMain, fontSize: 17, fontWeight: "900", fontVariant: ["tabular-nums"] },
  name: { color: tokens.color.textMain, fontSize: 21, fontWeight: "900" },
  stack: { gap: tokens.spacing.md },
});
