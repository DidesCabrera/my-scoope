import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { LibraryEntity, LibraryItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { CollectionPageHeader, DistributedTabBar, Field, LoadingState } from "@/components/ui";
import { Button, InlineNotice, textStyles } from "@/components/ui/primitives";
import { pickerHref } from "@/components/pickers/picker-routes";
import { tokens } from "@/design/tokens";
import { internalHref } from "@/navigation/internal-href";

type CreatableEntity = LibraryEntity;
type MealType = "breakfast" | "snack" | "lunch" | "shake" | "dinner";

const mealTypes: { value: MealType; label: string }[] = [
  { value: "breakfast", label: "Desayuno" },
  { value: "snack", label: "Snack" },
  { value: "lunch", label: "Comida" },
  { value: "shake", label: "Batido" },
  { value: "dinner", label: "Cena" },
];

type CreateConfig = {
  endpoint: string;
  headerTitle: string;
  pageTitle: string;
  namePlaceholder: string;
  segment: "foods" | "meals" | "daily-plans" | "programs";
  submitLabel: string;
  guidance?: string;
};

const configs: Record<CreatableEntity, CreateConfig> = {
  food: {
    endpoint: "/api/v1/library/foods",
    headerTitle: "Crear alimento",
    pageTitle: "Crear nuevo alimento",
    namePlaceholder: "Ej: Yogur natural",
    segment: "foods",
    submitLabel: "Crear alimento",
  },
  meal: {
    endpoint: "/api/v1/library/meals",
    headerTitle: "Crear comida",
    pageTitle: "Crear nueva comida",
    namePlaceholder: "Según ingredientes, propósito u otro",
    segment: "meals",
    submitLabel: "Crear y continuar",
  },
  dailyPlan: {
    endpoint: "/api/v1/library/daily-plans",
    headerTitle: "Crear minuta diaria",
    pageTitle: "Crear nueva minuta diaria",
    namePlaceholder: "Un día, objetivo o tipo de jornada",
    segment: "daily-plans",
    submitLabel: "Crear y continuar",
  },
  program: {
    endpoint: "/api/v1/library/programs",
    guidance: "El programa comenzará con una semana. Después podrás agregar más semanas.",
    headerTitle: "Crear programa",
    pageTitle: "Crear nuevo programa",
    namePlaceholder: "Ej: Volumen controlado",
    segment: "programs",
    submitLabel: "Crear y continuar",
  },
};

function macroNumber(value: string): number | null {
  const normalized = value.trim().replace(",", ".");
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) && parsed >= 0 && parsed <= 100 ? parsed : null;
}

function NutritionValueRow({ label, last = false, onChangeText, value }: { label: string; last?: boolean; onChangeText(value: string): void; value: string }) {
  return (
    <View style={[styles.nutritionRow, last && styles.nutritionRowLast]}>
      <Text style={styles.nutritionLabel}>{label}</Text>
      <View style={styles.nutritionInputSurface}>
        <TextInput
          accessibilityLabel={label}
          keyboardType="decimal-pad"
          onChangeText={onChangeText}
          placeholder="0"
          selectTextOnFocus
          style={styles.nutritionInput}
          value={value}
        />
        <Text style={styles.nutritionUnit}>g</Text>
      </View>
    </View>
  );
}

export function LibraryCreateScreen() {
  const params = useLocalSearchParams<{ entity?: string; id?: string; pickerEntryTo?: string; pickerKind?: string; pickerRelationId?: string; pickerTargetId?: string; returnTo?: string }>();
  const entity = typeof params.entity === "string" && Object.prototype.hasOwnProperty.call(configs, params.entity)
    ? params.entity as CreatableEntity
    : null;
  const config = entity ? configs[entity] : null;
  const requestedFoodId = Number(params.id);
  const editingFoodId = entity === "food" && Number.isInteger(requestedFoodId) && requestedFoodId > 0 ? requestedFoodId : null;
  const returnHref = internalHref(params.returnTo);
  const pickerEntryHref = internalHref(params.pickerEntryTo);
  const pickerKind = params.pickerKind === "meal-to-dailyplan" || params.pickerKind === "meal-to-calendarized-day" ? params.pickerKind : null;
  const pickerTargetId = Number(params.pickerTargetId);
  const pickerRelationId = Number(params.pickerRelationId) || undefined;
  const mealCreationContext = entity === "meal" && returnHref && pickerEntryHref && pickerKind && Number.isInteger(pickerTargetId) && pickerTargetId > 0
    ? { pickerEntryHref, pickerKind, pickerRelationId, pickerTargetId, returnHref }
    : null;
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [name, setName] = useState("");
  const [mealType, setMealType] = useState<MealType | null>(null);
  const [protein, setProtein] = useState("");
  const [carbs, setCarbs] = useState("");
  const [fat, setFat] = useState("");
  const [portionUnit, setPortionUnit] = useState<"g" | "ml">("g");
  const [submitting, setSubmitting] = useState(false);
  const [initializing, setInitializing] = useState(editingFoodId != null);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(useCallback(() => {
    if (!config) return;
    setHeaderPresentation({
      mode: "back",
      fallback: `/libraries/${config.segment}` as Href,
      identityVisible: false,
      title: editingFoodId ? "Editar alimento" : config.headerTitle,
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [config, editingFoodId, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    if (!editingFoodId || status !== "authenticated") return;
    let active = true;
    setInitializing(true);
    setError(null);
    void apiRequest<LibraryItem>(`/api/v1/library/foods/${editingFoodId}`)
      .then((food) => {
        if (!active) return;
        setName(food.name);
        setProtein(String(food.nutrition.protein.grams));
        setCarbs(String(food.nutrition.carbs.grams));
        setFat(String(food.nutrition.fat.grams));
        setPortionUnit(food.quantity_unit ?? "g");
      })
      .catch((nextError) => active && setError(userFacingError(nextError)))
      .finally(() => active && setInitializing(false));
    return () => { active = false; };
  }, [apiRequest, editingFoodId, status]));

  const macroValues = useMemo(() => ({
    carbs: macroNumber(carbs),
    fat: macroNumber(fat),
    protein: macroNumber(protein),
  }), [carbs, fat, protein]);
  const cleanName = name.trim();
  const validFood = entity !== "food" || Object.values(macroValues).every((value) => value !== null);
  const canSubmit = Boolean(cleanName && cleanName.length <= 100 && validFood && (entity !== "meal" || mealType) && !submitting);

  async function submit() {
    if (!config || !entity || !canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const body = entity === "food"
        ? { name: cleanName, protein: macroValues.protein, carbs: macroValues.carbs, fat: macroValues.fat, portion_unit: portionUnit }
        : entity === "meal" ? { name: cleanName, meal_type: mealType } : { name: cleanName };
      const saved = await apiRequest<LibraryItem>(editingFoodId ? `/api/v1/library/foods/${editingFoodId}/edit` : config.endpoint, {
        body: JSON.stringify(body),
        headers: { "Content-Type": "application/json" },
        method: editingFoodId ? "PUT" : "POST",
      });
      if (entity === "meal") {
        const detailParams = mealCreationContext ? new URLSearchParams({
          pickerEntryTo: String(mealCreationContext.pickerEntryHref),
          pickerKind: mealCreationContext.pickerKind,
          ...(mealCreationContext.pickerRelationId ? { pickerRelationId: String(mealCreationContext.pickerRelationId) } : {}),
          pickerTargetId: String(mealCreationContext.pickerTargetId),
          returnTo: String(mealCreationContext.returnHref),
        }) : null;
        const detailHref = `/libraries/meals/${saved.id}${detailParams ? `?${detailParams.toString()}` : "?createdFromLibrary=1"}`;
        router.replace(pickerHref("food-to-meal", { mealId: saved.id, returnTo: detailHref }));
      } else if (entity === "dailyPlan") {
        router.replace(pickerHref("meal-to-dailyplan", { dailyPlanId: saved.id, returnTo: `/libraries/daily-plans/${saved.id}?createdFromLibrary=1` }));
      } else if (entity === "program") {
        router.replace(pickerHref("dailyplan-to-program", { dayNumber: 1, programId: saved.id, returnTo: `/libraries/programs/${saved.id}?createdFromLibrary=1`, weekNumber: 1 }));
      } else {
        router.replace(`/libraries/${config.segment}/${saved.id}` as Href);
      }
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (!config || !entity) return <Redirect href="/today" />;
  if (initializing) return <LoadingState label="Cargando alimento…" />;

  const submitButton = <Button disabled={!canSubmit} label={editingFoodId ? "Guardar cambios" : config.submitLabel} loading={submitting} onPress={() => void submit()} />;

  return (
    <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.flex}>
        <ScrollView automaticallyAdjustKeyboardInsets contentContainerStyle={styles.content} keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "on-drag"} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          <CollectionPageHeader entity={entity} title={editingFoodId ? "Editar alimento" : config.pageTitle} />
          <View style={styles.formBody}>
            <Field autoCapitalize="sentences" label="Nombre" labelStyle={entity === "food" ? styles.foodFieldLabel : undefined} onChangeText={setName} placeholder={config.namePlaceholder} value={name} />
            {entity === "meal" ? (
              <View style={styles.mealTypeSection}>
                <Text style={styles.mealTypeLabel}>Tipo de comida</Text>
                <View accessibilityRole="radiogroup" style={styles.mealTypeChoices}>
                  {[mealTypes.slice(0, 3), mealTypes.slice(3)].map((row, rowIndex) => (
                    <View key={rowIndex} style={styles.mealTypeRow}>
                      {row.map(({ value, label }) => {
                        const selected = mealType === value;
                        return (
                          <Pressable
                            key={value}
                            accessibilityLabel={label}
                            accessibilityRole="radio"
                            accessibilityState={{ selected }}
                            onPress={() => setMealType(value)}
                            style={({ pressed }) => [styles.mealTypeChip, selected && styles.mealTypeChipSelected, pressed && styles.mealTypeChipPressed]}>
                            <Text style={[styles.mealTypeChipText, selected && styles.mealTypeChipTextSelected]}>{label}</Text>
                          </Pressable>
                        );
                      })}
                    </View>
                  ))}
                </View>
              </View>
            ) : null}
            {entity === "food" ? (
              <View style={styles.macroFields}>
                <View style={styles.portionTabs}>
                  <DistributedTabBar<"g" | "ml">
                    accessibilityLabel="Unidad de porción"
                    activeTab={portionUnit}
                    bleed
                    onChange={(unit) => setPortionUnit(unit)}
                    tabs={[{ key: "g", label: "Gramos" }, { key: "ml", label: "Mililitros" }]}
                  />
                </View>
                <View style={styles.macroHeading}>
                  <Text style={styles.macroTitle}>Valores por 100 {portionUnit}</Text>
                  <Text style={textStyles.caption}>Ingresa cada macronutriente entre 0 y 100 g.</Text>
                </View>
                <View style={styles.nutritionRows}>
                  <NutritionValueRow label="Proteínas" onChangeText={setProtein} value={protein} />
                  <NutritionValueRow label="Carbohidratos" onChangeText={setCarbs} value={carbs} />
                  <NutritionValueRow label="Grasas totales" last onChangeText={setFat} value={fat} />
                </View>
              </View>
            ) : null}
            {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
            <View style={[styles.formSubmit, entity === "food" && styles.foodFormSubmit]}>{submitButton}</View>
          </View>
          {config.guidance ? <Text style={styles.guidance}>{config.guidance}</Text> : null}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  flex: { flex: 1 },
  content: { flexGrow: 1, gap: tokens.spacing.lg, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  formBody: { gap: tokens.spacing.lg },
  guidance: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  formSubmit: { marginTop: tokens.spacing.md },
  foodFormSubmit: { marginTop: tokens.spacing.lg },
  mealTypeSection: { gap: tokens.spacing.md, marginTop: tokens.spacing.md },
  mealTypeLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  mealTypeChoices: { gap: tokens.spacing.sm },
  mealTypeRow: { flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "center" },
  mealTypeChip: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, justifyContent: "center", minHeight: 40, paddingHorizontal: tokens.spacing.lg },
  mealTypeChipSelected: { backgroundColor: `${tokens.color.meal}1A`, borderColor: tokens.color.meal, borderWidth: 2 },
  mealTypeChipPressed: { opacity: 0.72 },
  mealTypeChipText: { color: tokens.color.textMuted, fontSize: 14, fontWeight: tokens.weight.semibold },
  mealTypeChipTextSelected: { color: tokens.color.textMain },
  foodFieldLabel: { color: tokens.color.textMuted },
  macroFields: { gap: tokens.spacing.md },
  portionTabs: { marginBottom: tokens.spacing.md, marginTop: tokens.spacing.md },
  macroHeading: { gap: tokens.spacing.xs },
  macroTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: tokens.weight.extraBold },
  nutritionRows: { marginTop: -tokens.spacing.xs },
  nutritionRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 46, paddingLeft: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  nutritionRowLast: { borderBottomWidth: 0 },
  nutritionLabel: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontWeight: tokens.weight.bold, lineHeight: 20 },
  nutritionInputSurface: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, flexDirection: "row", height: 32, minWidth: 112, paddingHorizontal: tokens.spacing.sm },
  nutritionInput: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, height: 30, padding: 0, textAlign: "right" },
  nutritionUnit: { color: tokens.color.textSoft, fontSize: 12, marginLeft: 5 },
});
