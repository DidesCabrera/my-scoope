import { ClipboardList, MoreHorizontal, Plus } from "lucide-react-native";
import type { ReactNode } from "react";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Defs, LinearGradient, Stop } from "react-native-svg";

import { Card } from "@/components/ui/primitives";
import { FoodPanels, type FoodPanelItem } from "@/components/panels";
import { SectionHeading } from "@/components/ui/typography";
import { tokens } from "@/design/tokens";
import { EntityHeading, EntityIcon, StructuralIndicators } from "./entity-card";
import { ProgramMetricPreview } from "./program-child-card";
import { ProgramDailyPlanPreview } from "./program-daily-plan-preview";
import { ProgramDayComparisonPanels } from "./program-day-comparison-panels";
import { ProgramWeekComparisonPanels, type ProgramWeekSummary } from "./program-week-comparison-panels";

const weekSummaries: ProgramWeekSummary[] = [
  { allocation: { carbs: 47, fat: 29, protein: 24 }, averageCalories: 2040, calories: 14280, carbsGrams: 1546, dailyPlans: 7, fatGrams: 427, id: "week-1", proteinGrams: 1064, week: 1 },
  { allocation: { carbs: 46, fat: 29, protein: 25 }, averageCalories: 2087, calories: 14610, carbsGrams: 1574, dailyPlans: 7, fatGrams: 438, id: "week-2", proteinGrams: 1108, week: 2 },
];

const dayLabels = ["L", "M", "X", "J", "V", "S", "D"];

const weekFoodItems: FoodPanelItem[] = [
  { calories: 1210, calorieShare: 21, carbsAllocation: 75, carbsGrams: 226, fatAllocation: 12, fatGrams: 16, id: "week-rice", name: "Arroz cocido", proteinAllocation: 13, proteinGrams: 39, quantity: 1260, quantityUnit: "g" },
  { calories: 1848, calorieShare: 32, carbsAllocation: 0, carbsGrams: 0, fatAllocation: 24, fatGrams: 49, id: "week-chicken", name: "Pechuga de pollo", proteinAllocation: 76, proteinGrams: 322, quantity: 1120, quantityUnit: "g" },
  { calories: 842, calorieShare: 15, carbsAllocation: 39, carbsGrams: 82, fatAllocation: 33, fatGrams: 31, id: "week-yogurt", name: "Yogur griego", proteinAllocation: 28, proteinGrams: 59, quantity: 1260, quantityUnit: "g" },
  { calories: 624, calorieShare: 11, carbsAllocation: 92, carbsGrams: 144, fatAllocation: 3, fatGrams: 2, id: "week-banana", name: "Plátano", proteinAllocation: 5, proteinGrams: 8, quantity: 840, quantityUnit: "g" },
];

function CompactAction({ label, onPress, children }: { label: string; onPress(): void; children: ReactNode }) {
  return (
    <Pressable accessibilityLabel={label} accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.compactAction, pressed && styles.pressed]}>
      {children}
    </Pressable>
  );
}

function SelectedDayRing() {
  return (
    <View pointerEvents="none" style={styles.daySelectedRing}>
      <Svg height="100%" viewBox="0 0 100 100" width="100%">
        <Defs>
          <LinearGradient id="selected-day-gradient" x1="0" x2="1" y1="1" y2="0">
            <Stop offset="0" stopColor="#FEDA75" />
            <Stop offset="0.24" stopColor="#FA7E1E" />
            <Stop offset="0.52" stopColor="#D62976" />
            <Stop offset="0.76" stopColor="#962FBF" />
            <Stop offset="1" stopColor="#4F5BD5" />
          </LinearGradient>
        </Defs>
        <Circle cx="50" cy="50" fill="none" r="44" stroke="url(#selected-day-gradient)" strokeWidth="8" />
      </Svg>
    </View>
  );
}

function ProgramDaysGrid({ week }: { week: number }) {
  const filledDays = week === 1 ? [true, true, true, true, true, false, true] : [true, true, false, true, true, true, true];
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  return (
    <View style={styles.daySelection}>
      <View accessibilityLabel={`Planes diarios de Semana ${week}`} style={styles.daysGrid}>
        {dayLabels.map((label, index) => {
          const filled = filledDays[index];
          const selected = selectedDay === index;
          return (
            <View key={`${week}-${label}`} style={styles.dayCell}>
              <Text style={styles.dayLabel}>{label}</Text>
              <Pressable
                accessibilityLabel={filled ? `${label}: ver plan diario` : `${label}: agregar plan diario`}
                accessibilityRole="button"
                accessibilityState={{ expanded: filled ? selected : undefined, selected }}
                onPress={() => { if (filled) setSelectedDay((current) => current === index ? null : index); }}
                style={({ pressed }) => [styles.dayCircle, !filled && styles.dayCircleEmpty, selected && styles.dayCircleSelected, pressed && styles.pressed]}>
                {selected ? <SelectedDayRing /> : null}
                {filled
                  ? <View style={styles.dayPlanIcon}><ClipboardList color={tokens.color.entityIconForeground} size={14} /></View>
                  : <Plus color={tokens.color.program} size={24} />}
              </Pressable>
            </View>
          );
        })}
      </View>
      {selectedDay !== null ? <ProgramDailyPlanPreview dayLabel={dayLabels[selectedDay]} week={week} /> : null}
    </View>
  );
}

function ProgramWeekDetail({ week }: { week: number }) {
  return (
    <Card style={styles.weekCard}>
      <View style={styles.weekCardHeader}>
        <View style={styles.weekIdentity}>
          <View style={styles.weekEyebrow}>
            <EntityIcon entity="program" size="compact" />
            <Text style={styles.weekEyebrowText}>SEMANA {week}</Text>
          </View>
          <StructuralIndicators
            entity="program"
            indicators={[
              { icon: "dailyPlan", label: "planes diarios", value: 6 },
              { icon: "meal", label: "comidas", value: 24 },
              { icon: "food", label: "alimentos", value: 28 },
            ]}
          />
        </View>
        <CompactAction label={`Más acciones para Semana ${week}`} onPress={() => undefined}>
          <MoreHorizontal color={tokens.color.textMuted} size={21} />
        </CompactAction>
      </View>

      <SectionHeading title="Gráfico de KPIs de la semana" />
      <ProgramMetricPreview axisLabels={dayLabels} days={7} style={styles.systemBleed} />

      <SectionHeading title="Tabla de comparación entre planes diarios" />
      <View style={styles.systemBleed}><ProgramDayComparisonPanels key={`comparison-${week}`} week={week} /></View>

      <View style={styles.sectionDivider} />
      <SectionHeading detail="6 asignados" title="Planes diarios esta semana" />
      <ProgramDaysGrid key={week} week={week} />

      <View style={styles.sectionDivider} />
      <SectionHeading detail="28 alimentos" title="Alimentos en esta semana" />
      <View style={styles.systemBleed}><FoodPanels items={weekFoodItems} /></View>
    </Card>
  );
}

export function ProgramDetailPreview() {
  const [activeWeek, setActiveWeek] = useState(1);

  return (
    <View style={styles.page}>
      <View style={styles.overview}>
        <EntityHeading
          entity="program"
          indicators={[
            { label: "semanas", value: "2 SEMANAS" },
            { icon: "dailyPlan", label: "planes asignados", value: 12 },
            { icon: "food", label: "alimentos", value: 36 },
          ]}
          title="Programa de recomposición"
          variant="page"
        />

        <SectionHeading title="Gráficos de KPIs del Programa" />
        <ProgramMetricPreview style={styles.systemBleed} />

        <View style={styles.sectionTitleWithAction}>
          <SectionHeading title="Tabla de comparación entre semanas" />
          <Pressable accessibilityRole="button" onPress={() => undefined} style={({ pressed }) => [styles.addWeekButton, pressed && styles.pressed]}>
            <Plus color={tokens.color.surfaceApp} size={17} />
            <Text style={styles.addWeekText}>Agregar semana</Text>
          </Pressable>
        </View>
        <View style={styles.systemBleed}><ProgramWeekComparisonPanels weeks={weekSummaries} /></View>
      </View>

      <View style={styles.majorDivider} />

      <View style={styles.planningSection}>
        <View style={styles.planningHeader}>
          <View style={styles.planningIdentity}>
            <EntityIcon entity="program" />
            <Text style={styles.planningTitle}>Planificación por semanas</Text>
          </View>
          <StructuralIndicators entity="program" indicators={[{ icon: "week", label: "semanas", value: "2 SEMANAS" }]} />
        </View>

        <View accessibilityLabel="Semanas del programa" accessibilityRole="tablist" style={styles.weekTabs}>
          {[1, 2].map((week) => {
            const selected = activeWeek === week;
            return (
              <Pressable
                accessibilityLabel={`Semana ${week}`}
                accessibilityRole="tab"
                accessibilityState={{ selected }}
                key={week}
                onPress={() => setActiveWeek(week)}
                style={({ pressed }) => [styles.weekTab, selected && styles.weekTabActive, pressed && styles.pressed]}>
                <Text style={[styles.weekTabText, selected && styles.weekTabTextActive]}>Semana {week}</Text>
              </Pressable>
            );
          })}
        </View>

        <ProgramWeekDetail week={activeWeek} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { gap: tokens.spacing.xl, minWidth: 0, width: "100%" },
  overview: { gap: tokens.spacing.lg, minWidth: 0 },
  planningSection: { gap: tokens.spacing.md, minWidth: 0 },
  majorDivider: { backgroundColor: tokens.color.borderDefault, height: 1 },
  sectionDivider: { backgroundColor: tokens.color.borderSoft, height: 1, marginVertical: tokens.spacing.xs },
  systemBleed: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  sectionTitleWithAction: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.md, justifyContent: "space-between" },
  addWeekButton: { alignItems: "center", backgroundColor: tokens.color.textMain, borderRadius: tokens.radius.md, flexDirection: "row", gap: tokens.spacing.xs, minHeight: 38, paddingHorizontal: tokens.spacing.md },
  addWeekText: { color: tokens.color.surfaceApp, fontSize: tokens.type.caption, fontWeight: "700" },
  planningHeader: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.md, justifyContent: "space-between" },
  planningIdentity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  planningTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "700" },
  weekTabs: { flexDirection: "row", gap: tokens.spacing.compact, paddingBottom: tokens.spacing.sm },
  weekTab: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, justifyContent: "center", minHeight: 30, paddingHorizontal: tokens.spacing.md },
  weekTabActive: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  weekTabText: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "500" },
  weekTabTextActive: { color: tokens.color.surfaceApp },
  weekCard: { gap: tokens.spacing.lg, marginHorizontal: -tokens.spacing.screen },
  weekCardHeader: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  weekIdentity: { alignItems: "flex-start", flex: 1, gap: tokens.spacing.sm, minWidth: 0 },
  weekEyebrow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  weekEyebrowText: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: "700" },
  compactAction: { alignItems: "center", height: 34, justifyContent: "center", width: 34 },
  daysGrid: { flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "space-between" },
  daySelection: { gap: tokens.spacing.lg, minWidth: 0 },
  dayCell: { alignItems: "center", flex: 1, gap: tokens.spacing.sm, minWidth: 0 },
  dayLabel: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: "700" },
  dayCircle: { alignItems: "center", aspectRatio: 1, backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 2, justifyContent: "center", maxWidth: 58, overflow: "visible", position: "relative", width: "100%" },
  dayCircleEmpty: { borderStyle: "dashed" },
  dayCircleSelected: { borderColor: tokens.color.surfaceApp },
  dayPlanIcon: { alignItems: "center", backgroundColor: tokens.color.dailyPlan, borderRadius: tokens.spacing.compact, height: 24, justifyContent: "center", width: 24 },
  daySelectedRing: { bottom: -7, left: -7, position: "absolute", right: -7, top: -7 },
  pressed: { opacity: 0.68 },
});
