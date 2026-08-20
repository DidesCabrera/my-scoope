import { Redirect } from "expo-router";
import { ChevronDown } from "lucide-react-native";
import { useState } from "react";
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from "react-native";

import {
  ComparisonBuilder,
  ComparisonEditorCard,
  ComparisonMetricCard,
  ComparisonScopeTabs,
  ComparisonSelectionCard,
  type ComparisonScope,
  SavedComparisonCard,
  SavedComparisonDetailPage,
} from "@/components/comparisons";
import {
  DailyPlanMealDetailList,
  type DailyPlanMealDetailItem,
  EntityDetailMetadata,
  EntityDetailPage,
  EntityDetailSection,
} from "@/components/details";
import { ProgramChildCard } from "@/components/libraries/program-child-card";
import { ProgramDetailPreview } from "@/components/libraries/program-detail-preview";
import {
  KpiAllocationBar,
  NutritionEntityCard,
  NutritionKpiSection,
  PanelAllocationBar,
} from "@/components/nutrition";
import { FoodPanels, type FoodPanelItem, MealPanels, type MealPanelItem } from "@/components/panels";
import {
  ChatProposalCard,
  ProposalCard,
  ProposalDetailPage,
  ProposalEntitySection,
  ProposalObjectiveSection,
  ProposalReviewActions,
} from "@/components/proposals";
import {
  AppHeader,
  Brand,
  Button,
  Card,
  CardHeader,
  ChoiceRow,
  CollectionPageHeader,
  CollectionEmptyState,
  ContentPanel,
  DetailSection,
  EntityCard,
  type EntityKind,
  Field,
  InlineNotice,
  MessageCard,
  Pill,
  ProgressBar,
  Screen,
  SectionIcon,
  type SectionKind,
  SectionTitle,
  textStyles,
} from "@/components/ui";
import { tokens } from "@/design/tokens";

const entities: { key: EntityKind; label: string }[] = [
  { key: "food", label: "Food" },
  { key: "meal", label: "Meal" },
  { key: "dailyPlan", label: "DailyPlan" },
  { key: "dpm", label: "DPM" },
  { key: "program", label: "Program" },
];

const sections: { key: SectionKind; label: string; lucide: string }[] = [
  { key: "home", label: "Inicio", lucide: "house" },
  { key: "profile", label: "Perfil", lucide: "circle-user-round" },
  { key: "chatNew", label: "Nuevo chat", lucide: "message-square-plus" },
  { key: "chat", label: "Chats", lucide: "messages-square" },
  { key: "proposal", label: "Propuestas", lucide: "sparkles" },
  { key: "calendarization", label: "Calendarizar", lucide: "calendar-clock" },
  { key: "comparator", label: "Comparaciones", lucide: "columns-3" },
  { key: "explore", label: "Explorar", lucide: "search" },
  { key: "inbox", label: "Inbox", lucide: "inbox" },
  { key: "create", label: "Crear", lucide: "circle-fading-plus" },
  { key: "import", label: "Importar", lucide: "file-down" },
];

const foodPanelItems: FoodPanelItem[] = [
  { id: "oats", name: "Avena integral", quantity: 80, quantityUnit: "g", calories: 311, calorieShare: 34, proteinGrams: 10.5, carbsGrams: 52.8, fatGrams: 5.5, proteinAllocation: 14, carbsAllocation: 71, fatAllocation: 15 },
  { id: "yogurt", name: "Yogur griego", quantity: 180, quantityUnit: "g", calories: 176, calorieShare: 19, proteinGrams: 18, carbsGrams: 8.2, fatGrams: 7.1, proteinAllocation: 41, carbsAllocation: 19, fatAllocation: 40 },
  { id: "banana", name: "Plátano", quantity: 120, quantityUnit: "g", calories: 107, calorieShare: 12, proteinGrams: 1.3, carbsGrams: 27.4, fatGrams: 0.4, proteinAllocation: 5, carbsAllocation: 92, fatAllocation: 3 },
];

const comparisonFoodItems: FoodPanelItem[] = [
  { id: "comparison-yogurt", name: "Yogur griego natural", quantity: 100, quantityUnit: "g", calories: 97, calorieShare: 61, proteinGrams: 9, carbsGrams: 3.8, fatGrams: 5, proteinAllocation: 37, carbsAllocation: 16, fatAllocation: 47 },
  { id: "comparison-skyr", name: "Skyr natural", quantity: 100, quantityUnit: "g", calories: 62, calorieShare: 39, proteinGrams: 12, carbsGrams: 4, fatGrams: 0.2, proteinAllocation: 75, carbsAllocation: 24, fatAllocation: 1 },
];

const mealPanelItems: MealPanelItem[] = [
  { id: "breakfast", name: "Desayuno", time: "08:00", foods: [{ name: "Avena", quantity: 80, quantityUnit: "g" }, { name: "Yogur", quantity: 180, quantityUnit: "g" }, { name: "Plátano", quantity: 120, quantityUnit: "g" }], calories: 594, calorieShare: 28, proteinGrams: 29.8, carbsGrams: 88.4, fatGrams: 13, proteinAllocation: 20, carbsAllocation: 60, fatAllocation: 20 },
  { id: "lunch", name: "Almuerzo", time: "13:30", foods: [{ name: "Arroz", quantity: 180, quantityUnit: "g" }, { name: "Pollo", quantity: 160, quantityUnit: "g" }, { name: "Ensalada", quantity: 120, quantityUnit: "g" }], calories: 720, calorieShare: 34, proteinGrams: 52, carbsGrams: 82, fatGrams: 20, proteinAllocation: 29, carbsAllocation: 46, fatAllocation: 25 },
  { id: "dinner", name: "Cena", time: "20:00", foods: [{ name: "Salmón", quantity: 170, quantityUnit: "g" }, { name: "Papas", quantity: 220, quantityUnit: "g" }, { name: "Verduras", quantity: 140, quantityUnit: "g" }], calories: 610, calorieShare: 29, proteinGrams: 43, carbsGrams: 58, fatGrams: 23, proteinAllocation: 28, carbsAllocation: 38, fatAllocation: 34 },
];

const dailyPlanMealDetailItems: DailyPlanMealDetailItem[] = [
  {
    id: "breakfast-detail",
    name: "Desayuno",
    time: "08:00",
    foods: foodPanelItems,
    nutrition: {
      calories: 594,
      carbs: { grams: 88.4, allocation: 60 },
      fat: { grams: 13, allocation: 20 },
      protein: { grams: 29.8, allocation: 20, perKilogram: 0.35 },
    },
  },
  {
    id: "lunch-detail",
    name: "Almuerzo",
    time: "13:30",
    foods: [
      { ...foodPanelItems[0], id: "rice", name: "Arroz", quantity: 180, calories: 234 },
      { ...foodPanelItems[1], id: "chicken", name: "Pollo", quantity: 160, calories: 264 },
      { ...foodPanelItems[2], id: "salad", name: "Ensalada", calories: 72 },
    ],
    nutrition: {
      calories: 720,
      carbs: { grams: 82, allocation: 46 },
      fat: { grams: 20, allocation: 25 },
      protein: { grams: 52, allocation: 29, perKilogram: 0.61 },
    },
  },
  {
    id: "dinner-detail",
    name: "Cena",
    time: "20:00",
    foods: [
      { ...foodPanelItems[0], id: "salmon", name: "Salmón", quantity: 170, calories: 350 },
      { ...foodPanelItems[1], id: "potatoes", name: "Papas", quantity: 220, calories: 170 },
      { ...foodPanelItems[2], id: "vegetables", name: "Verduras", quantity: 140, calories: 90 },
    ],
    nutrition: {
      calories: 610,
      carbs: { grams: 58, allocation: 38 },
      fat: { grams: 23, allocation: 34 },
      protein: { grams: 43, allocation: 28, perKilogram: 0.51 },
    },
  },
];

type GalleryTab = "components" | "program" | "details" | "proposals" | "comparisons" | "states" | "tokens";
type Choice = "daily" | "weekly";

const galleryTabs: { key: GalleryTab; label: string }[] = [
  { key: "components", label: "Componentes" },
  { key: "program", label: "Programa" },
  { key: "details", label: "Detalle" },
  { key: "proposals", label: "Propuestas" },
  { key: "comparisons", label: "Comparaciones" },
  { key: "states", label: "Estados" },
  { key: "tokens", label: "Tokens" },
];

const comparisonExamples: Record<ComparisonScope, { label: string }> = {
  food: { label: "Yogur griego natural" },
  meal: { label: "Desayuno proteico" },
  dailyPlan: { label: "Plan semanal equilibrado" },
};

function GalleryNavigation({ activeTab, onChange, wide }: { activeTab: GalleryTab; onChange: (tab: GalleryTab) => void; wide: boolean }) {
  const [open, setOpen] = useState(false);
  const activeLabel = galleryTabs.find((item) => item.key === activeTab)?.label ?? "Sección";

  if (!wide) {
    return (
      <View style={styles.dropdown}>
        <Text style={styles.sidebarLabel}>Sección de la galería</Text>
        <Pressable
          accessibilityLabel={`Sección actual: ${activeLabel}`}
          accessibilityRole="button"
          accessibilityState={{ expanded: open }}
          onPress={() => setOpen((current) => !current)}
          style={({ pressed }) => [styles.dropdownTrigger, pressed && styles.sidebarItemPressed]}>
          <Text style={styles.dropdownValue}>{activeLabel}</Text>
          <ChevronDown color={tokens.color.textMuted} size={18} style={open && styles.dropdownChevronOpen} />
        </Pressable>
        {open ? (
          <View accessibilityLabel="Secciones disponibles" style={styles.dropdownMenu}>
            {galleryTabs.map((item) => {
              const active = activeTab === item.key;
              return (
                <Pressable
                  accessibilityRole="button"
                  accessibilityState={{ selected: active }}
                  key={item.key}
                  onPress={() => { onChange(item.key); setOpen(false); }}
                  style={({ pressed }) => [styles.dropdownItem, active && styles.dropdownItemActive, pressed && styles.sidebarItemPressed]}>
                  <Text style={[styles.sidebarItemText, active && styles.sidebarItemTextActive]}>{item.label}</Text>
                </Pressable>
              );
            })}
          </View>
        ) : null}
      </View>
    );
  }

  return (
    <View accessibilityLabel="Secciones de la galería" accessibilityRole="tablist" style={[styles.sidebar, styles.sidebarWide]}>
      <Text style={styles.sidebarLabel}>Secciones</Text>
      {galleryTabs.map((item) => {
        const active = activeTab === item.key;
        return (
          <Pressable
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
            key={item.key}
            onPress={() => onChange(item.key)}
            style={({ pressed }) => [styles.sidebarItem, active && styles.sidebarItemActive, pressed && styles.sidebarItemPressed]}>
            <Text style={[styles.sidebarItemText, active && styles.sidebarItemTextActive]}>{item.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export default function UiGalleryScreen() {
  const { width } = useWindowDimensions();
  const [tab, setTab] = useState<GalleryTab>("components");
  const [choice, setChoice] = useState<Choice>("daily");
  const [comparisonScope, setComparisonScope] = useState<ComparisonScope>("food");
  const [comparisonQuantity, setComparisonQuantity] = useState("100");
  const [field, setField] = useState("");

  if (!__DEV__) return <Redirect href="/" />;

  return (
    <Screen>
      <Brand />
      <AppHeader eyebrow="Solo desarrollo" title="Galería del sistema UI" />
      <InlineNotice>Referencia interna construida con los componentes reales de la app.</InlineNotice>
      <View style={[styles.galleryLayout, width >= 700 && styles.galleryLayoutWide]}>
        <GalleryNavigation activeTab={tab} onChange={setTab} wide={width >= 700} />
        <View style={styles.galleryContent}>

      {tab === "components" ? (
        <>
          <SectionTitle detail="Genérico y anidado" title="Títulos de card" />
          <Card>
            <CardHeader
              accessory={<Pill label="Acción" />}
              description="Encabezado estándar para una superficie de contenido."
              title="Título de card"
            />
            <CardHeader
              density="compact"
              description="Variante para contenido anidado o de mayor densidad."
              title="Título compacto"
            />
          </Card>
          <ContentPanel description="Panel principal que agrupa información relacionada." title="ContentPanel">
            <DetailSection description="Sección anidada con encabezado y acción opcional." title="DetailSection">
              <Text style={textStyles.body}>Contenido compuesto sin replicar estilos de superficie.</Text>
            </DetailSection>
          </ContentPanel>
          <SectionTitle detail="Identidad semántica" title="Título de entidad" />
          <EntityCard
            accessory={<Pill color={tokens.color.dailyPlan} label="Activo" />}
            entity="dailyPlan"
            indicators={[
              { icon: "meal", label: "comidas", value: 4 },
              { icon: "food", label: "alimentos", value: 12 },
            ]}
            title="Día de entrenamiento">
            <Text style={textStyles.muted}>El icono, eyebrow, título e indicadores reproducen la jerarquía de la web.</Text>
          </EntityCard>
          <EntityCard
            entity="food"
            indicators={[{ label: "base nutricional", value: "100 g" }]}
            title="Yogur griego natural"
          />
          <EntityCard
            entity="meal"
            indicators={[{ icon: "food", label: "alimentos", value: 5 }]}
            title="Desayuno pre-entreno"
          />
          <EntityCard
            entity="program"
            indicators={[
              { icon: "week", label: "semanas", value: 8 },
              { icon: "food", label: "alimentos", value: 36 },
            ]}
            title="Programa de recomposición"
          />
          <SectionTitle detail="Título, gráfico y acciones" title="Card-child de programa" />
          <ProgramChildCard
            filledDaysCount={12}
            foodsCount={36}
            onMore={() => undefined}
            onOpen={() => undefined}
            owner="Tú"
            title="Programa de recomposición"
            weeksCount={2}
          />
          <SectionTitle detail="Identidad + colección + cantidad" title="Encabezados de páginas de lista" />
          <CollectionPageHeader count={8} countIcon="day" entity="dailyPlan" title="Planes diarios" />
          <CollectionPageHeader count={14} countIcon="meal" entity="meal" title="Comidas" />
          <SectionTitle detail="Base nutricional por 100 g" title="Card de alimento" />
          <NutritionEntityCard
            entity="food"
            indicators={[{ label: "base nutricional", value: "100 g" }]}
            nutrition={{
              calories: 97,
              carbs: { grams: 3.9, allocation: 16 },
              fat: { grams: 5, allocation: 47 },
              protein: { grams: 9, allocation: 37, perKilogram: 0.1 },
            }}
            title="Yogur griego natural"
          />
          <SectionTitle detail="Título + KPI" title="Card nutricional compuesta" />
          <NutritionEntityCard
            accessory={<Pill color={tokens.color.dailyPlan} label="Activo" />}
            entity="dailyPlan"
            indicators={[
              { icon: "meal", label: "comidas", value: 4 },
              { icon: "food", label: "alimentos", value: 12 },
            ]}
            nutrition={{
              calories: 2140,
              carbs: { grams: 238, allocation: 44 },
              fat: { grams: 62, allocation: 26 },
              protein: { grams: 155, allocation: 30, perKilogram: 1.8 },
            }}
            title="Día de entrenamiento"
          />
          <SectionTitle detail="Meal y DPM" title="Paneles de alimentos" />
          <NutritionEntityCard
            entity="meal"
            indicators={[{ icon: "food", label: "alimentos", value: foodPanelItems.length }]}
            nutrition={{
              calories: 594,
              carbs: { grams: 88.4, allocation: 60 },
              fat: { grams: 13, allocation: 20 },
              protein: { grams: 29.8, allocation: 20, perKilogram: 0.35 },
            }}
            title="Desayuno pre-entreno">
            <FoodPanels items={foodPanelItems} />
          </NutritionEntityCard>
          <SectionTitle detail="DailyPlan" title="Paneles de comidas" />
          <NutritionEntityCard
            entity="dailyPlan"
            indicators={[
              { icon: "meal", label: "comidas", value: mealPanelItems.length },
              { icon: "food", label: "alimentos", value: 9 },
            ]}
            nutrition={{
              calories: 2140,
              carbs: { grams: 238, allocation: 44 },
              fat: { grams: 62, allocation: 26 },
              protein: { grams: 155, allocation: 30, perKilogram: 1.8 },
            }}
            title="Día de entrenamiento">
            <MealPanels items={mealPanelItems} />
          </NutritionEntityCard>
          <CollectionEmptyState
            actionLabel="Crear elemento"
            description="Este estado mantiene la acción principal junto al contexto de la colección."
            onAction={() => undefined}
            title="Todavía no hay elementos"
          />

          <SectionTitle detail="Identidad de marca" title="Alloc en KPI" />
          <Card>
            <View style={styles.allocationRow}>
              <Text style={styles.allocationLabel}>Proteína</Text>
              <KpiAllocationBar style={styles.allocationBarInRow} tone="protein" value={72} />
            </View>
            <View style={styles.allocationRow}>
              <Text style={styles.allocationLabel}>Carbos</Text>
              <KpiAllocationBar style={styles.allocationBarInRow} tone="carbs" value={48} />
            </View>
            <View style={styles.allocationRow}>
              <Text style={styles.allocationLabel}>Grasas</Text>
              <KpiAllocationBar style={styles.allocationBarInRow} tone="fat" value={26} />
            </View>
          </Card>

          <SectionTitle detail="Adaptativa · breakpoint 420 pt" title="Sección KPI" />
          <Card>
            <NutritionKpiSection
              calories={2140}
              carbs={{ grams: 238, allocation: 44 }}
              fat={{ grams: 62, allocation: 26 }}
              protein={{ grams: 155, allocation: 30, perKilogram: 1.8 }}
            />
          </Card>
          <ContentPanel description="La misma jerarquía con menor densidad para cards anidadas." muted title="Sección KPI compacta">
            <NutritionKpiSection
              calories={640}
              carbs={{ grams: 72, allocation: 45 }}
              density="compact"
              fat={{ grams: 18, allocation: 25 }}
              protein={{ grams: 48, allocation: 30, perKilogram: 0.6 }}
            />
          </ContentPanel>

          <SectionTitle detail="Regular y compacta" title="Alloc en paneles" />
          <ContentPanel description="El mismo porcentaje base cambia de composición según su contexto." title="Distribución objetivo">
            <View style={styles.allocationRow}>
              <Text style={styles.allocationLabel}>Proteína</Text>
              <PanelAllocationBar style={styles.allocationBarInRow} tone="protein" value={84} />
            </View>
            <View style={styles.allocationRow}>
              <Text style={styles.allocationLabel}>Carbos</Text>
              <PanelAllocationBar style={styles.allocationBarInRow} tone="carbs" value={51} />
            </View>
            <View style={styles.allocationRow}>
              <Text style={styles.allocationLabel}>Grasas</Text>
              <PanelAllocationBar style={styles.allocationBarInRow} tone="fat" value={18} />
            </View>
            <DetailSection description="Para filas densas, pickers y cards secundarias." title="Tamaño compacto">
              <PanelAllocationBar size="compact" tone="protein" value={100} />
              <PanelAllocationBar size="compact" tone="carbs" value={4} />
              <PanelAllocationBar size="compact" tone="fat" value={0} />
            </DetailSection>
          </ContentPanel>
        </>
      ) : null}

      {tab === "details" ? (
        <>
          <SectionTitle detail="Primera composición reutilizable" title="Página de detalle" />
          <EntityDetailPage
            action={<Pill color={tokens.color.dailyPlan} label="Editar" />}
            entity="dailyPlan"
            indicators={[
              { icon: "meal", label: "comidas", value: mealPanelItems.length },
              { icon: "food", label: "alimentos", value: 9 },
            ]}
            nutrition={{
              calories: 2140,
              carbs: { grams: 238, allocation: 44 },
              fat: { grams: 62, allocation: 26 },
              protein: { grams: 155, allocation: 30, perKilogram: 1.8 },
            }}
            onBack={() => undefined}
            title="Día de entrenamiento">
            <EntityDetailSection detail="3 comidas" title="Comidas en este plan">
              <MealPanels items={mealPanelItems} />
            </EntityDetailSection>
            <EntityDetailSection detail="3 comidas" title="Detalle de cada comida">
              <DailyPlanMealDetailList items={dailyPlanMealDetailItems} />
            </EntityDetailSection>
            <EntityDetailMetadata creator="Felipe Dides" updatedAt="Hoy, 14:30" />
          </EntityDetailPage>
        </>
      ) : null}

      {tab === "program" ? (
        <>
          <SectionTitle detail="Vista completa" title="Detalle de programa" />
          <ProgramDetailPreview />
        </>
      ) : null}

      {tab === "proposals" ? (
        <>
          <SectionTitle detail="Respuesta dentro del chat" title="Propuesta generada" />
          <ChatProposalCard
            adjustments={["Más proteína", "Mantener alimentos"]}
            metrics={[
              { label: "Actual", value: "2.050 kcal" },
              { label: "Objetivo", value: "2.140 kcal" },
              { label: "Alimentos", value: "Sin cambios" },
            ]}
            onPress={() => undefined}
            summary="Ajusté las porciones para acercar el plan al objetivo sin reemplazar sus alimentos."
            title="Día de entrenamiento ajustado"
          />
          <SectionTitle detail="Resumen de bandeja" title="Card de propuesta" />
          <ProposalCard
            attachment={{ kind: "dailyPlan", name: "Día de entrenamiento propuesto" }}
            isRead={false}
            onPress={() => undefined}
            receivedAt="Recibida hoy, 14:30"
            status="pending"
            summary="Crear un DailyPlan alto en proteína para un día de entrenamiento."
            title="Propuesta de DailyPlan"
          />
          <SectionTitle detail="Revisión antes de aplicar" title="Detalle de propuesta" />
          <ProposalDetailPage
            isRead
            objectives={
              <ProposalObjectiveSection
                calories={2140}
                carbs={{ grams: 238, allocation: 44 }}
                fat={{ grams: 62, allocation: 26 }}
                protein={{ grams: 155, allocation: 30, perKilogram: 1.8 }}
              />
            }
            receivedAt="Recibida hoy, 14:30"
            status="pending"
            summary="Crear un DailyPlan alto en proteína para un día de entrenamiento."
            title="Propuesta de DailyPlan"
            typeLabel="Nuevo DailyPlan"
            proposedEntity={
              <ProposalEntitySection entity="dailyPlan">
                <NutritionEntityCard
                  entity="dailyPlan"
                  indicators={[
                    { icon: "meal", label: "comidas", value: 3 },
                    { icon: "food", label: "alimentos", value: 9 },
                  ]}
                  nutrition={{
                    calories: 2140,
                    carbs: { grams: 238, allocation: 44 },
                    fat: { grams: 62, allocation: 26 },
                    protein: { grams: 155, allocation: 30, perKilogram: 1.8 },
                  }}
                  title="Día de entrenamiento propuesto">
                  <MealPanels items={mealPanelItems} />
                </NutritionEntityCard>
              </ProposalEntitySection>
            }>
            <ProposalReviewActions
              description="Aprobar confirma la revisión; aplicar cambios reales será un paso posterior y explícito."
              onApprove={() => undefined}
              onCancel={() => undefined}
              onReject={() => undefined}
            />
          </ProposalDetailPage>
        </>
      ) : null}

      {tab === "comparisons" ? (
        <>
          <SectionTitle detail="Alimentos, comidas y planes" title="Alcance de comparación" />
          <ComparisonScopeTabs activeScope={comparisonScope} onChange={setComparisonScope} />
          <SectionTitle detail="Selección, cantidad y acciones" title="Construir comparación" />
          <ComparisonBuilder onAdd={() => undefined} onCompare={() => undefined} onSave={() => undefined} scope={comparisonScope}>
            <ComparisonEditorCard
              entity={comparisonScope}
              index={1}
              label={comparisonExamples[comparisonScope].label}
              onOpenSelector={() => undefined}
              onQuantityChange={setComparisonQuantity}
              quantity={comparisonQuantity}
            />
            <ComparisonEditorCard
              entity={comparisonScope}
              index={2}
              onOpenSelector={() => undefined}
              onRemove={() => undefined}
            />
          </ComparisonBuilder>
          <SectionTitle detail="Estado resumido de lectura" title="Elementos comparados" />
          <ComparisonSelectionCard entity="food" index={1} label="Yogur griego natural" quantity="100 g" />
          <ComparisonSelectionCard entity="food" index={2} label="Skyr natural" onRemove={() => undefined} quantity="100 g" />
          <SectionTitle detail="Primera propuesta de resultados" title="Métricas comparativas" />
          <ComparisonMetricCard
            items={[
              { entity: "food", formattedValue: "97 kcal", id: "yogurt-kcal", label: "Yogur griego natural", labelSuffix: "(100 g)", width: 78 },
              { entity: "food", formattedValue: "62 kcal", id: "skyr-kcal", label: "Skyr natural", labelSuffix: "(100 g)", width: 50 },
            ]}
            label="Calorías"
            tone="calories"
            unit="kcal"
          />
          <ComparisonMetricCard
            items={[
              { entity: "food", formattedValue: "9,0 g", id: "yogurt-protein", label: "Yogur griego natural", width: 75 },
              { entity: "food", formattedValue: "12,0 g", id: "skyr-protein", label: "Skyr natural", width: 100 },
            ]}
            label="Proteína"
            tone="protein"
            unit="g"
          />
          <SectionTitle detail="Alloc de panel compacto · sin valor interior" title="Métrica alternativa" />
          <ComparisonMetricCard
            barVariant="compactAlloc"
            items={[
              { entity: "food", formattedValue: "9,0 g", id: "alt-yogurt-protein", label: "Yogur griego natural", width: 75 },
              { entity: "food", formattedValue: "12,0 g", id: "alt-skyr-protein", label: "Skyr natural", width: 100 },
            ]}
            label="Proteína"
            tone="protein"
            unit="g"
          />
          <SectionTitle detail="Resumen de comparaciones persistidas" title="Comparación guardada" />
          <SavedComparisonCard
            items={comparisonFoodItems}
            title="Yogures altos en proteína"
          />
          <SectionTitle detail="Vista extendida en modo lectura" title="Page-card guardada" />
          <SavedComparisonDetailPage
            itemCount={2}
            onEdit={() => undefined}
            scope="food"
            selections={
              <>
                <ComparisonSelectionCard entity="food" index={1} label="Yogur griego natural" quantity="100 g" />
                <ComparisonSelectionCard entity="food" index={2} label="Skyr natural" quantity="100 g" />
              </>
            }
            title="Yogures altos en proteína">
            <ComparisonMetricCard
              items={[
                { entity: "food", formattedValue: "97 kcal", id: "saved-yogurt-kcal", label: "Yogur griego natural", labelSuffix: "(100 g)", width: 78 },
                { entity: "food", formattedValue: "62 kcal", id: "saved-skyr-kcal", label: "Skyr natural", labelSuffix: "(100 g)", width: 50 },
              ]}
              label="Calorías"
              tone="calories"
              unit="kcal"
            />
            <ComparisonMetricCard
              items={[
                { entity: "food", formattedValue: "9,0 g", id: "saved-yogurt-protein", label: "Yogur griego natural", width: 75 },
                { entity: "food", formattedValue: "12,0 g", id: "saved-skyr-protein", label: "Skyr natural", width: 100 },
              ]}
              label="Proteína"
              tone="protein"
              unit="g"
            />
          </SavedComparisonDetailPage>
        </>
      ) : null}

      {tab === "states" ? (
        <>
          <SectionTitle detail="Interactivos" title="Controles" />
          <Button label="Acción principal" onPress={() => undefined} />
          <Button label="Acción secundaria" onPress={() => undefined} variant="secondary" />
          <Button label="Acción destructiva" onPress={() => undefined} variant="danger" />
          <Button disabled label="Acción deshabilitada" onPress={() => undefined} />
          <Button label="Procesando" loading onPress={() => undefined} />
          <Field label="Campo de ejemplo" onChangeText={setField} placeholder="Escribe un valor" value={field} />
          <ChoiceRow<Choice>
            label="Frecuencia"
            onChange={setChoice}
            options={[{ value: "daily", label: "Diaria" }, { value: "weekly", label: "Semanal" }]}
            value={choice}
          />
          <ProgressBar value={64} />
          <InlineNotice>Información contextual.</InlineNotice>
          <InlineNotice tone="warning">Requiere atención antes de continuar.</InlineNotice>
          <InlineNotice tone="error">No fue posible completar la acción.</InlineNotice>
          <MessageCard title="Cambio guardado" tone="success">La configuración ya está disponible en tus dispositivos.</MessageCard>
          <MessageCard title="Revisión pendiente" tone="warning">Confirma los datos nutricionales antes de aplicarlos.</MessageCard>
          <MessageCard title="Error de sincronización" tone="danger">Conservamos tus cambios locales para reintentarlo.</MessageCard>
        </>
      ) : null}

      {tab === "tokens" ? (
        <>
          <SectionTitle detail={tokens.contract} title="Entidades" />
          {entities.map((entity) => (
            <EntityCard entity={entity.key} key={entity.key} subtitle={`tokens.color.${entity.key}`} title={entity.label} />
          ))}
          <SectionTitle detail="Lucide · fondo transparente" title="Iconos de secciones" />
          <View style={styles.sectionIconList}>
            {sections.map((section) => (
              <View key={section.key} style={styles.sectionIconRow}>
                <SectionIcon section={section.key} />
                <Text style={styles.sectionIconLabel}>{section.label}</Text>
                <Text style={textStyles.caption}>{section.lucide}</Text>
              </View>
            ))}
          </View>
          <SectionTitle detail="Escala semántica" title="Tipografía" />
          {Object.entries(tokens.type).map(([name, size]) => (
            <View key={name} style={styles.typeRow}>
              <Text style={[styles.typeSample, { fontSize: size }]}>{name}</Text>
              <Text style={textStyles.caption}>{size} pt</Text>
            </View>
          ))}
          <SectionTitle detail="400 → 900" title="Grosores" />
          {Object.entries(tokens.weight).map(([name, weight]) => (
            <View key={name} style={styles.typeRow}>
              <Text style={[styles.weightSample, { fontWeight: weight }]}>My Scoope · {name}</Text>
              <Text style={textStyles.caption}>{weight}</Text>
            </View>
          ))}
          <SectionTitle detail="xs → xxl" title="Espaciado" />
          {Object.entries(tokens.spacing).map(([name, size]) => (
            <View key={name} style={styles.scaleRow}>
              <Text style={styles.scaleLabel}>{name}</Text>
              <View style={[styles.scaleBar, { width: size * 3 }]} />
              <Text style={textStyles.caption}>{size}</Text>
            </View>
          ))}
          <SectionTitle detail="Padding y separación interna" title="Dimensiones de card" />
          {Object.entries(tokens.card).map(([name, size]) => (
            <View key={name} style={styles.scaleRow}>
              <Text style={styles.scaleLabel}>{name}</Text>
              <View style={[styles.scaleBar, { width: size * 3 }]} />
              <Text style={textStyles.caption}>{size} px</Text>
            </View>
          ))}
          <View style={styles.scaleRow}>
            <Text style={styles.scaleLabel}>reducedInset</Text>
            <View style={[styles.scaleBar, { width: tokens.layout.reducedInset * 3 }]} />
            <Text style={textStyles.caption}>{tokens.layout.reducedInset} px</Text>
          </View>
          <SectionTitle detail="sm → pill" title="Radios" />
          <View style={styles.radiusGrid}>
            {Object.entries(tokens.radius).map(([name, radius]) => (
              <View key={name} style={styles.radiusItem}>
                <View style={[styles.radiusSample, { borderRadius: radius }]} />
                <Text style={textStyles.caption}>{name} · {radius}</Text>
              </View>
            ))}
          </View>
        </>
      ) : null}
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  galleryLayout: { gap: tokens.spacing.lg, minWidth: 0, width: "100%" },
  galleryLayoutWide: { alignItems: "flex-start", flexDirection: "row" },
  galleryContent: { flex: 1, gap: tokens.spacing.lg, minWidth: 0, width: "100%" },
  dropdown: { alignSelf: "stretch", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, gap: tokens.spacing.xs, padding: tokens.spacing.sm },
  dropdownTrigger: { alignItems: "center", backgroundColor: tokens.color.surfaceElevated, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, flexDirection: "row", justifyContent: "space-between", minHeight: 44, paddingHorizontal: tokens.spacing.md },
  dropdownValue: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  dropdownChevronOpen: { transform: [{ rotate: "180deg" }] },
  dropdownMenu: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, gap: tokens.spacing.xs, marginTop: tokens.spacing.xs, paddingTop: tokens.spacing.sm },
  dropdownItem: { borderRadius: tokens.radius.md, minHeight: 40, paddingHorizontal: tokens.spacing.md, paddingVertical: 10 },
  dropdownItemActive: { backgroundColor: tokens.color.surfaceElevated },
  sidebar: { alignSelf: "stretch", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, gap: tokens.spacing.xs, padding: tokens.spacing.sm },
  sidebarWide: { flexBasis: 156, flexGrow: 0, flexShrink: 0 },
  sidebarLabel: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs, textTransform: "uppercase" },
  sidebarItem: { borderRadius: tokens.radius.md, minHeight: 40, paddingHorizontal: tokens.spacing.sm, paddingVertical: 10 },
  sidebarItemActive: { backgroundColor: tokens.color.surfaceElevated, borderLeftColor: tokens.color.interactivePrimary, borderLeftWidth: 3 },
  sidebarItemPressed: { opacity: 0.7 },
  sidebarItemText: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium },
  sidebarItemTextActive: { color: tokens.color.textMain, fontWeight: tokens.weight.bold },
  typeRow: { alignItems: "baseline", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingVertical: tokens.spacing.sm },
  typeSample: { color: tokens.color.textMain, fontWeight: tokens.weight.bold },
  weightSample: { color: tokens.color.textMain, fontSize: tokens.type.body },
  scaleRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, minHeight: 34 },
  scaleLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, width: 48 },
  scaleBar: { backgroundColor: tokens.color.interactivePrimary, borderRadius: tokens.radius.pill, height: 8 },
  radiusGrid: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.md },
  radiusItem: { alignItems: "center", gap: tokens.spacing.sm, width: "29%" },
  radiusSample: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.interactivePrimary, borderWidth: 1, height: 58, width: 58 },
  sectionIconList: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, paddingHorizontal: tokens.spacing.md },
  sectionIconRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 44 },
  sectionIconLabel: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  allocationRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  allocationLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700", width: 96 },
  allocationBarInRow: { flex: 1, minWidth: 0, width: "auto" },
});
