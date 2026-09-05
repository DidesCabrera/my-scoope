import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { Search } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type {
  FoodPickerPageData,
  FoodPickerOption,
  LibraryEntity,
  LibraryIndicator,
  LibraryItem,
  LibraryNutrition,
  LibraryPageData,
  PickerCommitResult,
  PickerPreview,
} from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { FoodPanels, MealPanels } from "@/components/libraries/entity-panels";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";
import { NutritionEntityCard } from "@/components/nutrition";
import { Button, Card, Field, InlineNotice, LoadingState, Screen, SectionTitle, textStyles } from "@/components/ui";
import { ConfirmationState, RecoverableErrorState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";
import { PickerCardAction } from "./picker-card-action";
import { PickerEntryTabs } from "./picker-entry-tabs";
import { PickerResultCard } from "./picker-result-card";

export type PickerKind = "food-to-meal" | "meal-to-dailyplan" | "dailyplan-to-program";

type PickerOption = {
  id: number;
  name: string;
  entity: "food" | "meal" | "dailyPlan";
  indicators?: LibraryIndicator[];
  nutrition: LibraryNutrition;
  panel?: LibraryItem["panel"];
  subtitle?: string;
};

type PickerConfig = {
  createEntity: LibraryEntity;
  createLabel: string;
  title: string;
  searchLabel: string;
  searchPlaceholder: string;
  targetSlug: "meals" | "daily-plans" | "programs";
  previewPath(targetId: number): string;
  commitPath(targetId: number): string;
};

const configs: Record<PickerKind, PickerConfig> = {
  "food-to-meal": {
    createEntity: "food",
    createLabel: "Crear alimento",
    title: "Agregar alimento",
    searchLabel: "Buscar alimento",
    searchPlaceholder: "Escribe el nombre de un alimento",
    targetSlug: "meals",
    previewPath: (id) => `/api/v1/library/meals/${id}/food-picker/preview`,
    commitPath: (id) => `/api/v1/library/meals/${id}/food-picker/commit`,
  },
  "meal-to-dailyplan": {
    createEntity: "meal",
    createLabel: "Crear comida",
    title: "Agregar comida",
    searchLabel: "Buscar comida",
    searchPlaceholder: "Escribe el nombre de una comida",
    targetSlug: "daily-plans",
    previewPath: (id) => `/api/v1/library/daily-plans/${id}/meal-picker/preview`,
    commitPath: (id) => `/api/v1/library/daily-plans/${id}/meal-picker/commit`,
  },
  "dailyplan-to-program": {
    createEntity: "dailyPlan",
    createLabel: "Crear plan diario",
    title: "Asignar plan diario",
    searchLabel: "Buscar plan diario",
    searchPlaceholder: "Escribe el nombre de un plan diario",
    targetSlug: "programs",
    previewPath: (id) => `/api/v1/library/programs/${id}/daily-plan-picker/preview`,
    commitPath: (id) => `/api/v1/library/programs/${id}/daily-plan-picker/commit`,
  },
};

const dayOptions = [
  { id: 1, short: "L", label: "Lunes" },
  { id: 2, short: "M", label: "Martes" },
  { id: 3, short: "X", label: "Miércoles" },
  { id: 4, short: "J", label: "Jueves" },
  { id: 5, short: "V", label: "Viernes" },
  { id: 6, short: "S", label: "Sábado" },
  { id: 7, short: "D", label: "Domingo" },
];

function optionFromLibrary(item: LibraryItem): PickerOption {
  return {
    id: item.id,
    name: item.name,
    entity: item.entity === "dailyPlan" ? "dailyPlan" : "meal",
    indicators: item.indicators,
    nutrition: item.nutrition,
    panel: item.panel,
    subtitle: item.subtitle || undefined,
  };
}

function optionFromFood(item: FoodPickerOption): PickerOption {
  return {
    id: item.id,
    name: item.display_name,
    entity: "food",
    indicators: [{ label: "base nutricional", value: "100 g" }],
    nutrition: {
      calories: item.total_kcal,
      protein: { grams: item.protein, allocation: item.protein_allocation, per_kilogram: null },
      carbs: { grams: item.carbs, allocation: item.carbs_allocation },
      fat: { grams: item.fat, allocation: item.fat_allocation },
    },
  };
}

function PickerOptionCard({ actionLabel, onAction, option }: { actionLabel: string; onAction(): void; option: PickerOption }) {
  return (
    <NutritionEntityCard
      actions={(
        <PickerCardAction label={actionLabel} onPress={onAction} subject={option.name} />
      )}
      entity={option.entity}
      indicators={option.indicators}
      nutrition={libraryNutrition(option.nutrition)}
      subtitle={option.subtitle}
      title={option.name}>
      {option.panel?.kind === "foods" ? <FoodPanels items={option.panel.foods} /> : null}
      {option.panel?.kind === "meals" ? <MealPanels items={option.panel.meals} /> : null}
    </NutritionEntityCard>
  );
}

export function CompositionPickerScreen({
  kind,
  targetId,
  relationId,
  selectedId,
  weekNumber = 1,
  initialDayNumber,
  returnTo,
}: {
  kind: PickerKind;
  targetId: number;
  relationId?: number;
  selectedId?: number;
  weekNumber?: number;
  initialDayNumber?: number;
  returnTo?: Href;
}) {
  const config = configs[kind];
  const title = relationId
    ? kind === "food-to-meal" ? "Reemplazar alimento" : "Reemplazar comida"
    : config.title;
  const router = useRouter();
  const detailHref = returnTo ?? `/libraries/${config.targetSlug}/${targetId}` as Href;
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<PickerOption[]>([]);
  const [selected, setSelected] = useState<PickerOption | null>(null);
  const [quantity, setQuantity] = useState("100");
  const [hour, setHour] = useState("08:00");
  const [note, setNote] = useState("");
  const [dayNumbers, setDayNumbers] = useState<number[]>(() => initialDayNumber ? [initialDayNumber] : [1]);
  const [preview, setPreview] = useState<PickerPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);

  useFocusEffect(useCallback(() => {
    const close = () => router.dismissTo(detailHref);
    setHeaderPresentation({ action: { label: "Cancelar", onPress: close }, mode: "back", fallback: detailHref, title });
    return () => setHeaderPresentation({ mode: "default" });
  }, [detailHref, router, setHeaderPresentation, title]));

  useEffect(() => {
    if (status !== "authenticated" || !targetId) return;
    let active = true;
    const selectionRequest = selectedId
      ? kind === "food-to-meal"
        ? apiRequest<FoodPickerOption>(`/api/v1/food-picker-options/${selectedId}`).then(optionFromFood)
        : apiRequest<LibraryItem>(`/api/v1/library/${kind === "meal-to-dailyplan" ? "meals" : "daily-plans"}/${selectedId}`).then(optionFromLibrary)
      : Promise.resolve(null);
    Promise.all([
      apiRequest<LibraryItem>(`/api/v1/library/${config.targetSlug}/${targetId}`),
      selectionRequest,
    ])
      .then(([target, option]) => {
        if (!active) return;
        setSelected(option);
        if (kind === "food-to-meal" && relationId && target.panel.kind === "foods") {
          const relation = target.panel.foods.find((item) => item.relation_id === relationId);
          if (relation) setQuantity(String(relation.quantity));
        }
        if (kind === "meal-to-dailyplan" && relationId && target.panel.kind === "meals") {
          const slot = target.panel.meals.find((item) => item.relation_id === relationId);
          if (slot) { setHour(slot.time?.slice(0, 5) || "08:00"); setNote(slot.note || ""); }
        }
      })
      .catch((nextError) => active && setError(userFacingError(nextError)))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [apiRequest, config.targetSlug, kind, relationId, retryNonce, selectedId, status, targetId]);

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated" || selectedId) return;
    // Recreate the focused request after an explicit retry, even when the search text is unchanged.
    void retryNonce;
    let active = true;
    const timer = setTimeout(() => {
      setSearching(true);
      const search = query.trim() ? `&search=${encodeURIComponent(query.trim())}` : "";
      const request = kind === "food-to-meal"
        ? apiRequest<FoodPickerPageData>(`/api/v1/foods?limit=50${search}`).then((page) => page.items.map(optionFromFood))
        : apiRequest<LibraryPageData>(`/api/v1/library/${kind === "meal-to-dailyplan" ? "meals" : "daily-plans"}?limit=50${search}`).then((page) => page.items.map(optionFromLibrary));
      void request
        .then((items) => active && setOptions(items))
        .catch((nextError) => active && setError(userFacingError(nextError)))
        .finally(() => active && setSearching(false));
    }, 220);
    return () => { active = false; clearTimeout(timer); };
  }, [apiRequest, kind, query, retryNonce, selectedId, status]));

  const hourValid = kind !== "meal-to-dailyplan" || /^([01]\d|2[0-3]):[0-5]\d$/.test(hour);
  const quantityValid = kind !== "food-to-meal" || Number(quantity) > 0;
  const configurationValid = Boolean(selected) && hourValid && quantityValid && (kind !== "dailyplan-to-program" || dayNumbers.length > 0);

  const payload = useMemo(() => {
    if (!selected) return null;
    if (kind === "food-to-meal") return { food_id: selected.id, meal_food_id: relationId, quantity: Number(quantity) };
    if (kind === "meal-to-dailyplan") return { meal_id: selected.id, dailyplan_meal_id: relationId, hour, note };
    return { dailyplan_id: selected.id, week_number: weekNumber, day_numbers: dayNumbers };
  }, [dayNumbers, hour, kind, note, quantity, relationId, selected, weekNumber]);

  useEffect(() => {
    if (!configurationValid || !payload) return;
    let active = true;
    const timer = setTimeout(() => {
      setPreviewing(true);
      setError(null);
      void apiRequest<PickerPreview>(config.previewPath(targetId), { method: "POST", body: JSON.stringify(payload) })
        .then((result) => active && setPreview(result))
        .catch((nextError) => active && setError(userFacingError(nextError)))
        .finally(() => active && setPreviewing(false));
    }, 180);
    return () => { active = false; clearTimeout(timer); };
  }, [apiRequest, config, configurationValid, payload, retryNonce, targetId]);

  function toggleDay(day: number) {
    setDayNumbers((current) => current.includes(day) ? current.filter((value) => value !== day) : [...current, day].sort());
    setPreview(null);
    setConfirming(false);
  }

  async function commit(confirmReplacements = false) {
    if (!payload || !preview) return;
    setSubmitting(true);
    setError(null);
    try {
      const body = kind === "dailyplan-to-program" ? { ...payload, confirm_replacements: confirmReplacements } : payload;
      const result = await apiRequest<PickerCommitResult>(config.commitPath(targetId), { method: "POST", body: JSON.stringify(body) });
      Alert.alert("Listo", result.message, [{ text: "Aceptar", onPress: () => router.dismissTo(detailHref) }]);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Preparando el selector…" />;

  if (!selectedId) {
    return (
      <SafeAreaView edges={["left", "right"]} style={styles.selectionSafeArea}>
        <ScrollView
          contentContainerStyle={styles.selectionScrollContent}
          keyboardDismissMode="on-drag"
          keyboardShouldPersistTaps="handled"
          stickyHeaderIndices={[0]}>
          <View style={styles.selectionSticky}>
            <PickerEntryTabs
              createLabel={config.createLabel}
              onCreate={() => router.push({ pathname: "/libraries/create", params: { entity: config.createEntity } })}
            />
            <View style={styles.searchField}>
              <Search color={tokens.color.textSoft} size={19} />
              <TextInput
                accessibilityLabel={config.searchLabel}
                autoCapitalize="words"
                onChangeText={setQuery}
                placeholder={config.searchPlaceholder}
                placeholderTextColor={tokens.color.textSubtle}
                style={styles.searchInput}
                value={query}
              />
              {searching ? <ActivityIndicator color={tokens.color.interactivePrimary} size="small" /> : null}
            </View>
          </View>

          <View style={styles.options}>
            {options.map((option) => (
              <PickerOptionCard
                actionLabel="Seleccionar"
                key={`${option.entity}-${option.id}`}
                onAction={() => router.push(pickerConfigureHref(kind, { dayNumber: initialDayNumber, relationId, returnTo, selectedId: option.id, targetId, weekNumber }))}
                option={option}
              />
            ))}
            {!searching && options.length === 0 ? <Text style={textStyles.muted}>No encontramos resultados.</Text> : null}
            {error ? <RecoverableErrorState message={error} onRetry={() => { setError(null); setRetryNonce((value) => value + 1); }} /> : null}
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <Screen headerMode="preserve">
      {selected ? (
        <PickerOptionCard
          actionLabel="Cambiar selección"
          onAction={() => router.back()}
          option={selected}
        />
      ) : null}

      {selected ? (
        <Card>
          <SectionTitle title="Configura la selección" />
          {kind === "food-to-meal" ? <Field keyboardType="decimal-pad" label="Porción (g)" onChangeText={(value) => { setQuantity(value); setPreview(null); }} value={quantity} /> : null}
          {kind === "meal-to-dailyplan" ? (
            <>
              <Field keyboardType="numbers-and-punctuation" label="Hora (HH:MM)" onChangeText={(value) => { setHour(value); setPreview(null); }} placeholder="08:00" value={hour} />
              {!hourValid ? <InlineNotice tone="warning">Ingresa una hora válida entre 00:00 y 23:59.</InlineNotice> : null}
              <Field autoCapitalize="sentences" label="Nota (opcional)" onChangeText={(value) => { setNote(value); setPreview(null); }} placeholder="Ej. antes de entrenar" value={note} />
            </>
          ) : null}
          {kind === "dailyplan-to-program" ? (
            <View style={styles.daysBlock}>
              <Text style={styles.fieldLabel}>Días de la Semana {weekNumber}</Text>
              <View accessibilityRole="radiogroup" style={styles.days}>
                {dayOptions.map((day) => {
                  const isSelected = dayNumbers.includes(day.id);
                  return (
                    <Pressable
                      accessibilityLabel={day.label}
                      accessibilityRole="checkbox"
                      accessibilityState={{ checked: isSelected }}
                      key={day.id}
                      onPress={() => toggleDay(day.id)}
                      style={[styles.day, isSelected && styles.daySelected]}>
                      <Text style={[styles.dayText, isSelected && styles.dayTextSelected]}>{day.short}</Text>
                    </Pressable>
                  );
                })}
              </View>
              {!dayNumbers.length ? <InlineNotice tone="warning">Selecciona al menos un día.</InlineNotice> : null}
            </View>
          ) : null}
        </Card>
      ) : null}

      {previewing ? <View style={styles.previewLoading}><ActivityIndicator color={tokens.color.interactivePrimary} /><Text style={textStyles.muted}>{kind === "dailyplan-to-program" ? "Validando asignación…" : "Actualizando previsualización…"}</Text></View> : null}
      {error ? <RecoverableErrorState message={error} onRetry={() => { setError(null); setRetryNonce((value) => value + 1); }} /> : null}

      {preview?.result ? (
        <View style={styles.previewSection}>
          <SectionTitle title="Previsualización del impacto" />
          <PickerResultCard preview={preview} />
          {preview.replacements.length ? <InlineNotice tone="warning">Se reemplazarán: {preview.replacements.join(", ")}.</InlineNotice> : null}
        </View>
      ) : null}

      {preview && confirming ? (
        <ConfirmationState
          busy={submitting}
          confirmLabel="Reemplazar y asignar"
          message={`Los días ${preview.replacements.join(", ")} ya tienen un plan. Se reemplazarán por ${preview.selection.name}.`}
          onCancel={() => setConfirming(false)}
          onConfirm={() => void commit(true)}
          title="Confirmar reemplazos"
        />
      ) : preview ? (
        <Button
          bleed
          label={kind === "food-to-meal" ? relationId ? "Reemplazar alimento" : "Agregar alimento" : kind === "meal-to-dailyplan" ? relationId ? "Reemplazar comida" : "Agregar comida" : "Asignar plan diario"}
          loading={submitting}
          onPress={() => preview.confirmation_required ? setConfirming(true) : void commit()}
        />
      ) : null}
    </Screen>
  );
}

export function pickerHref(kind: PickerKind, params: Record<string, string | number>): Href {
  const query = new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)])).toString();
  return `/pickers/${kind}?${query}` as Href;
}

export function pickerConfigureHref(
  kind: PickerKind,
  { dayNumber, relationId, returnTo, selectedId, targetId, weekNumber }: { dayNumber?: number; relationId?: number; returnTo?: Href; selectedId: number; targetId: number; weekNumber: number },
): Href {
  const params: Record<string, string> = {
    kind,
    selectedId: String(selectedId),
    targetId: String(targetId),
    weekNumber: String(weekNumber),
  };
  if (dayNumber) params.dayNumber = String(dayNumber);
  if (relationId) params.relationId = String(relationId);
  if (returnTo) params.returnTo = String(returnTo);
  return `/pickers/configure?${new URLSearchParams(params).toString()}` as Href;
}

const styles = StyleSheet.create({
  day: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, height: 42, justifyContent: "center", width: 42 },
  daySelected: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  dayText: { color: tokens.color.textMuted, fontSize: 14, fontWeight: "800" },
  dayTextSelected: { color: tokens.color.surfaceApp },
  days: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  daysBlock: { gap: tokens.spacing.sm },
  fieldLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  options: { gap: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen },
  previewLoading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  previewSection: { gap: tokens.spacing.lg },
  searchField: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, marginHorizontal: tokens.spacing.screen, minHeight: 38, paddingHorizontal: tokens.spacing.md },
  searchInput: { color: tokens.color.textMain, flex: 1, fontSize: 16, minHeight: 36, paddingVertical: 0 },
  selectionSafeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  selectionScrollContent: { flexGrow: 1, paddingBottom: 42 },
  selectionSticky: { backgroundColor: tokens.color.surfaceApp, gap: tokens.spacing.xs, paddingBottom: tokens.spacing.lg, zIndex: 2 },
});
