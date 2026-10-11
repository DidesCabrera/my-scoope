import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { LibraryEntity, LibraryItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { DistributedTabBar, EntityIcon, Field, LoadingState } from "@/components/ui";
import { Button, Card, InlineNotice, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";
import { internalHref } from "@/navigation/internal-href";

type CreatableEntity = LibraryEntity;

type CreateConfig = {
  endpoint: string;
  headerTitle: string;
  identityLabel: string;
  namePlaceholder: string;
  segment: "foods" | "meals" | "daily-plans" | "programs";
  submitLabel: string;
  guidance?: string;
};

const configs: Record<CreatableEntity, CreateConfig> = {
  food: {
    endpoint: "/api/v1/library/foods",
    headerTitle: "Crear alimento",
    identityLabel: "Nuevo alimento",
    namePlaceholder: "Ej: Yogur natural",
    segment: "foods",
    submitLabel: "Crear alimento",
  },
  meal: {
    endpoint: "/api/v1/library/meals",
    guidance: "Después podrás agregar los alimentos y configurar sus porciones.",
    headerTitle: "Crear comida",
    identityLabel: "Nueva comida",
    namePlaceholder: "Según ingredientes, propósito u otro",
    segment: "meals",
    submitLabel: "Crear y continuar",
  },
  dailyPlan: {
    endpoint: "/api/v1/library/daily-plans",
    guidance: "Después podrás agregar las comidas y elegir sus horarios.",
    headerTitle: "Crear plan diario",
    identityLabel: "Nuevo plan diario",
    namePlaceholder: "Un día, objetivo o tipo de jornada",
    segment: "daily-plans",
    submitLabel: "Crear y continuar",
  },
  program: {
    endpoint: "/api/v1/library/programs",
    guidance: "El programa comenzará con una semana. Después podrás asignar planes diarios o agregar más semanas.",
    headerTitle: "Crear programa",
    identityLabel: "Nuevo programa",
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

function NutritionValueRow({ label, onChangeText, value }: { label: string; onChangeText(value: string): void; value: string }) {
  return (
    <View style={styles.nutritionRow}>
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
  const [protein, setProtein] = useState("");
  const [carbs, setCarbs] = useState("");
  const [fat, setFat] = useState("");
  const [portionUnit, setPortionUnit] = useState<"g" | "ml">("g");
  const [submitting, setSubmitting] = useState(false);
  const [initializing, setInitializing] = useState(editingFoodId != null);
  const [error, setError] = useState<string | null>(null);

  const cancel = useCallback(() => {
    if (router.canGoBack()) router.back();
    else if (config) router.replace(`/libraries/${config.segment}` as Href);
  }, [config, router]);

  useFocusEffect(useCallback(() => {
    if (!config) return;
    setHeaderPresentation({
      mode: "back",
      action: { label: "Cancelar", onPress: cancel },
      fallback: `/libraries/${config.segment}` as Href,
      title: editingFoodId ? "Editar alimento" : config.headerTitle,
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [cancel, config, editingFoodId, setHeaderPresentation]));

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
  const canSubmit = Boolean(cleanName && cleanName.length <= 100 && validFood && !submitting);

  async function submit() {
    if (!config || !entity || !canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const body = entity === "food"
        ? { name: cleanName, protein: macroValues.protein, carbs: macroValues.carbs, fat: macroValues.fat, portion_unit: portionUnit }
        : { name: cleanName };
      const saved = await apiRequest<LibraryItem>(editingFoodId ? `/api/v1/library/foods/${editingFoodId}/edit` : config.endpoint, {
        body: JSON.stringify(body),
        headers: { "Content-Type": "application/json" },
        method: editingFoodId ? "PUT" : "POST",
      });
      router.replace(mealCreationContext
        ? {
          pathname: "/libraries/meals/[id]",
          params: {
            id: String(saved.id),
            pickerEntryTo: String(mealCreationContext.pickerEntryHref),
            pickerKind: mealCreationContext.pickerKind,
            ...(mealCreationContext.pickerRelationId ? { pickerRelationId: String(mealCreationContext.pickerRelationId) } : {}),
            pickerTargetId: String(mealCreationContext.pickerTargetId),
            returnTo: String(mealCreationContext.returnHref),
          },
        }
        : `/libraries/${config.segment}/${saved.id}` as Href);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (!config || !entity) return <Redirect href="/today" />;
  if (initializing) return <LoadingState label="Cargando alimento…" />;

  return (
    <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={styles.flex}>
        <ScrollView automaticallyAdjustKeyboardInsets contentContainerStyle={styles.content} keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "on-drag"} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          <Card accent={tokens.color[entity]} style={styles.formCard}>
            <View style={styles.identityRow}>
              <EntityIcon entity={entity} size="compact" />
              <Text style={styles.eyebrow}>{editingFoodId ? "Editar alimento" : config.identityLabel}</Text>
            </View>
            <Field autoCapitalize="sentences" label="Nombre" labelStyle={entity === "food" ? styles.foodFieldLabel : undefined} onChangeText={setName} placeholder={config.namePlaceholder} value={name} />
            {entity === "food" ? (
              <View style={styles.macroFields}>
                <DistributedTabBar<"g" | "ml">
                  accessibilityLabel="Unidad de porción"
                  activeTab={portionUnit}
                  bleed
                  onChange={(unit) => setPortionUnit(unit)}
                  tabs={[{ key: "g", label: "Gramos" }, { key: "ml", label: "Mililitros" }]}
                />
                <View style={styles.macroHeading}>
                  <Text style={styles.macroTitle}>Valores por 100 {portionUnit}</Text>
                  <Text style={textStyles.caption}>Ingresa cada macronutriente entre 0 y 100 g.</Text>
                </View>
                <View style={styles.nutritionRows}>
                  <NutritionValueRow label="Proteínas" onChangeText={setProtein} value={protein} />
                  <NutritionValueRow label="Carbohidratos" onChangeText={setCarbs} value={carbs} />
                  <NutritionValueRow label="Grasas totales" onChangeText={setFat} value={fat} />
                </View>
              </View>
            ) : null}
            {config.guidance ? <InlineNotice>{config.guidance}</InlineNotice> : null}
            {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
            <Button disabled={!canSubmit} label={editingFoodId ? "Guardar cambios" : config.submitLabel} loading={submitting} onPress={() => void submit()} />
          </Card>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  flex: { flex: 1 },
  content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.sm },
  formCard: { gap: tokens.spacing.lg },
  identityRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  eyebrow: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, textTransform: "uppercase" },
  foodFieldLabel: { color: tokens.color.textMain },
  macroFields: { gap: tokens.spacing.md },
  macroHeading: { gap: tokens.spacing.xs },
  macroTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: tokens.weight.extraBold },
  nutritionRows: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, marginTop: -tokens.spacing.xs },
  nutritionRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 46, paddingLeft: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  nutritionLabel: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontWeight: tokens.weight.bold, lineHeight: 20 },
  nutritionInputSurface: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, flexDirection: "row", height: 32, minWidth: 112, paddingHorizontal: tokens.spacing.sm },
  nutritionInput: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, height: 30, padding: 0, textAlign: "right" },
  nutritionUnit: { color: tokens.color.textSoft, fontSize: 12, marginLeft: 5 },
});
