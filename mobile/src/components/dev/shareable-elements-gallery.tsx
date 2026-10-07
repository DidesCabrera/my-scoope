import { useState } from "react";
import { Image, StyleSheet, Text, View } from "react-native";

import { DailyPlanMealDetailList, type DailyPlanMealDetailItem, EntityDetailPage, EntityDetailSection, FoodDetailCardList } from "@/components/details";
import { ProgramDetailPreview } from "@/components/libraries/program-detail-preview";
import { FoodPanels, MealPanels, type FoodPanelItem, type MealPanelItem } from "@/components/panels";
import { Button, InlineNotice, MyScoopeLogo, ScrollableTabBar } from "@/components/ui";
import { tokens } from "@/design/tokens";

type SocialCardPreview = "food" | "meal" | "dailyPlan" | "program";

type PreviewData = {
  calories: number;
  carbs: number;
  fat: number;
  label: string;
  protein: number;
  rows?: { detail?: string; items?: { label: string; value: string }[]; title: string; value?: string }[];
  sectionTitle?: string;
  source: number;
  summary: string;
  title: string;
  weeksCount?: number;
};

const previews: Record<SocialCardPreview, PreviewData> = {
  food: { calories: 97, carbs: 3.8, fat: 5, label: "Alimento", protein: 9, source: require("../../assets/dev/share-card-food.png"), summary: "Valores nutricionales por 100 g", title: "Yogur griego natural" },
  meal: {
    calories: 544, carbs: 68.4, fat: 14.1, label: "Comida", protein: 35.8,
    rows: [{ items: [{ label: "Avena integral", value: "80 g" }, { label: "Yogur griego", value: "180 g" }, { label: "Plátano", value: "120 g" }], title: "Alimentos" }],
    sectionTitle: "Alimentos", source: require("../../assets/dev/share-card-meal.png"), summary: "3 alimentos", title: "Desayuno proteico",
  },
  dailyPlan: {
    calories: 1924, carbs: 219.6, fat: 55.8, label: "Plan diario", protein: 137.2,
    rows: [
      { detail: "08:00", items: [{ label: "Avena integral", value: "80 g" }, { label: "Yogur griego", value: "180 g" }, { label: "Plátano", value: "120 g" }], title: "Desayuno proteico", value: "544 kcal" },
      { detail: "13:30", items: [{ label: "Pechuga de pollo", value: "180 g" }, { label: "Arroz integral", value: "200 g" }, { label: "Ensalada mediterránea", value: "180 g" }], title: "Almuerzo", value: "720 kcal" },
      { detail: "20:00", items: [{ label: "Salmón al horno", value: "170 g" }, { label: "Papas asadas", value: "220 g" }, { label: "Verduras salteadas", value: "160 g" }], title: "Cena", value: "660 kcal" },
    ],
    sectionTitle: "Comidas", source: require("../../assets/dev/share-card-daily-plan.png"), summary: "3 comidas · 9 alimentos", title: "Plan equilibrado de entrenamiento",
  },
  program: {
    calories: 2140, carbs: 238, fat: 63, label: "Programa semanal", protein: 155,
    rows: [
      { items: [{ label: "Desayuno proteico", value: "544 kcal" }, { label: "Almuerzo", value: "720 kcal" }, { label: "Cena", value: "660 kcal" }], title: "Semana 1 · Día 1", value: "1924 kcal" },
      { items: [{ label: "Desayuno ligero", value: "420 kcal" }, { label: "Almuerzo", value: "760 kcal" }, { label: "Cena", value: "680 kcal" }], title: "Semana 1 · Día 2", value: "1860 kcal" },
    ],
    sectionTitle: "Días planificados", source: require("../../assets/dev/share-card-program.png"), summary: "8 semanas · 36 días planificados", title: "Programa de recomposición", weeksCount: 8,
  },
};

const tabs = (Object.entries(previews) as [SocialCardPreview, (typeof previews)[SocialCardPreview]][])
  .map(([key, preview]) => ({ key, label: preview.label }));

export function ShareableElementsGallery() {
  const [activePreview, setActivePreview] = useState<SocialCardPreview>("dailyPlan");
  const effectiveActivePreview = previews[activePreview] ? activePreview : "dailyPlan";
  const preview = previews[effectiveActivePreview];

  return (
    <View style={styles.gallery}>
      <ScrollableTabBar<SocialCardPreview>
        accessibilityLabel="Tarjetas para compartir en redes sociales"
        activeTab={effectiveActivePreview}
        density="compact"
        onChange={setActivePreview}
        tabs={tabs}
      />
      <InlineNotice>
        Preview real de <Text style={styles.code}>og:image</Text>, generado con el renderer de producción y datos ficticios.
      </InlineNotice>
      <View style={styles.previewFrame}>
        <Image
          accessibilityLabel={`Tarjeta social de ${preview.label}: ${preview.summary}`}
          resizeMode="contain"
          source={preview.source}
          style={styles.previewImage}
        />
      </View>
      <View style={styles.metadata}>
        <Text style={styles.metadataTitle}>{preview.label}</Text>
        <Text style={styles.metadataDetail}>1200 × 630 px · {preview.summary}</Text>
      </View>
      <View style={styles.destinationHeading}>
        <Text style={styles.destinationTitle}>Vista al abrir el enlace</Text>
        <Text style={styles.destinationDetail}>Página pública responsive</Text>
      </View>
      <ShareLinkDestinationPreview kind={effectiveActivePreview} preview={preview} />
    </View>
  );
}

function nutrition(preview: PreviewData) {
  const macroCalories = preview.protein * 4 + preview.carbs * 4 + preview.fat * 9;
  const allocation = (value: number, factor: number) => macroCalories ? value * factor * 100 / macroCalories : 0;
  return {
    calories: preview.calories,
    protein: { grams: preview.protein, allocation: allocation(preview.protein, 4) },
    carbs: { grams: preview.carbs, allocation: allocation(preview.carbs, 4) },
    fat: { grams: preview.fat, allocation: allocation(preview.fat, 9) },
  };
}

function foodItems(preview: PreviewData): FoodPanelItem[] {
  return (preview.rows?.[0]?.items ?? []).map((item, index) => ({
    id: `shared-food-${index}`, name: item.label, quantity: Number(item.value.replace(/[^0-9.,]/g, "").replace(",", ".")), quantityUnit: "g",
    calories: [311, 126, 107][index] ?? 90, calorieShare: [57, 23, 20][index] ?? 0,
    proteinGrams: [10.5, 24, 1.3][index] ?? 0, carbsGrams: [52.8, 7.4, 8.2][index] ?? 0, fatGrams: [5.5, 0.8, 7.8][index] ?? 0,
    proteinAllocation: [26, 30, 28][index] ?? 0, carbsAllocation: [50, 48, 39][index] ?? 0, fatAllocation: [23, 23, 31][index] ?? 0,
  }));
}

function mealItems(preview: PreviewData): MealPanelItem[] {
  return (preview.rows ?? []).map((row, index) => ({
    id: `shared-meal-${index}`, name: row.title, time: row.detail, foods: (row.items ?? []).map((item) => ({ name: item.label, quantity: Number(item.value.replace(/[^0-9.,]/g, "").replace(",", ".")), quantityUnit: "g" })),
    calories: [544, 720, 660][index] ?? 0, calorieShare: [28, 37, 35][index] ?? 0,
    proteinGrams: [35.8, 54.4, 47][index] ?? 0, carbsGrams: [68.4, 86.2, 65][index] ?? 0, fatGrams: [14.1, 18.7, 23][index] ?? 0,
    proteinAllocation: [26, 30, 28][index] ?? 0, carbsAllocation: [50, 48, 39][index] ?? 0, fatAllocation: [23, 23, 31][index] ?? 0,
  }));
}

function mealDetailItems(preview: PreviewData): DailyPlanMealDetailItem[] {
  const meals = mealItems(preview);
  return meals.map((meal, mealIndex) => ({
    id: `shared-meal-detail-${mealIndex}`,
    name: meal.name,
    time: meal.time,
    foods: (preview.rows?.[mealIndex]?.items ?? []).map((item, foodIndex) => ({
      id: `shared-meal-${mealIndex}-food-${foodIndex}`,
      name: item.label,
      quantity: Number(item.value.replace(/[^0-9.,]/g, "").replace(",", ".")),
      quantityUnit: "g",
      calories: [[311, 126, 107], [297, 246, 177], [350, 220, 90]][mealIndex]?.[foodIndex] ?? 0,
      calorieShare: 0,
      proteinGrams: 0,
      carbsGrams: 0,
      fatGrams: 0,
      proteinAllocation: 0,
      carbsAllocation: 0,
      fatAllocation: 0,
    })),
    nutrition: {
      calories: meal.calories,
      protein: { grams: meal.proteinGrams, allocation: meal.proteinAllocation },
      carbs: { grams: meal.carbsGrams, allocation: meal.carbsAllocation },
      fat: { grams: meal.fatGrams, allocation: meal.fatAllocation },
    },
  }));
}

function ShareLinkDestinationPreview({ kind, preview }: { kind: SocialCardPreview; preview: PreviewData }) {
  const foods = foodItems(preview);
  const meals = mealItems(preview);
  const mealDetails = mealDetailItems(preview);
  const sharedEyebrow = kind === "meal" ? "Comida compartida" : kind === "food" ? "Alimento compartido" : kind === "dailyPlan" ? "Plan diario compartido" : "Programa compartido";
  if (kind === "program") {
    return (
      <View style={styles.destinationSurface}>
        <View style={styles.destinationLogo}><MyScoopeLogo /></View>
        <ProgramDetailPreview fallbackWeeksCount={preview.weeksCount} footer={<View style={styles.destinationActions}><Button label="Abrir en la app" onPress={() => undefined} /></View>} showWeekAnalytics={false} />
      </View>
    );
  }
  return (
    <View style={styles.destinationSurface}>
      <View style={styles.destinationLogo}><MyScoopeLogo /></View>
      <EntityDetailPage
        entity={kind}
        eyebrow={sharedEyebrow}
        indicators={kind === "meal" ? [{ icon: "food", label: "alimentos", value: foods.length }] : kind === "dailyPlan" ? [{ icon: "meal", label: "comidas", value: meals.length }, { icon: "food", label: "alimentos", value: 9 }] : undefined}
        nutrition={nutrition(preview)}
        subtitle={kind === "food" ? "100 g" : undefined}
        title={preview.title}>
        {kind === "meal" ? <EntityDetailSection detail={`${foods.length} alimentos`} title="Composición"><FoodPanels items={foods} /></EntityDetailSection> : null}
        {kind === "meal" ? <EntityDetailSection detail={`${foods.length} alimentos`} title="Detalle de cada Alimento"><FoodDetailCardList items={foods} /></EntityDetailSection> : null}
        {kind === "dailyPlan" ? <EntityDetailSection detail={`${meals.length} comidas`} title="Composición"><MealPanels items={meals} /></EntityDetailSection> : null}
        {kind === "dailyPlan" ? <EntityDetailSection detail={`${mealDetails.length} comidas`} title="Detalle de cada Comida"><DailyPlanMealDetailList items={mealDetails} /></EntityDetailSection> : null}
        <View style={styles.destinationActions}>
          <Button label="Abrir en la app" onPress={() => undefined} />
        </View>
      </EntityDetailPage>
    </View>
  );
}

const styles = StyleSheet.create({
  code: { fontWeight: tokens.weight.bold },
  destinationDetail: { color: tokens.color.textMuted, fontSize: tokens.type.caption }, destinationHeading: { gap: tokens.spacing.xs, marginTop: tokens.spacing.md }, destinationTitle: { color: tokens.color.textMain, fontSize: tokens.type.title, fontWeight: tokens.weight.bold },
  destinationActions: { gap: tokens.spacing.sm },
  destinationLogo: { alignItems: "center", justifyContent: "center", minHeight: 44 },
  destinationSurface: { backgroundColor: tokens.color.surfaceApp, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.lg, overflow: "hidden", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.lg },
  gallery: { gap: tokens.spacing.md, minWidth: 0, width: "100%" },
  metadata: { gap: tokens.spacing.xs },
  metadataDetail: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  metadataTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  previewFrame: { aspectRatio: 1200 / 630, backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.card, borderWidth: 1, overflow: "hidden", width: "100%" },
  previewImage: { height: "100%", width: "100%" },
});
