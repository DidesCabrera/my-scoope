import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Minus, Plus } from "lucide-react-native";
import { useCallback, useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { LibraryItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { PreparationIngredientsCard, formatPreparationAllergens, formatPreparationNumber, type PreparationIngredient } from "@/components/preparations/preparation-ingredients-card";
import { Screen } from "@/components/ui/layout";
import { Button, ChoiceRow, Field } from "@/components/ui/controls";
import { InlineNotice } from "@/components/ui/primitives";
import { SearchField } from "@/components/ui/search-field";
import { Card } from "@/components/ui/surfaces";
import { tokens } from "@/design/tokens";

type PreparationDetail = {
  id: number; name: string; version: number; household_label: string; default_portion_g: number;
  selected_units: number | null; grams: number; nutrition: { calories: number; protein_g: number; carbs_g: number; fat_g: number; sodium_mg: number | null };
  allergens: string[]; allergen_status: string; evidence: { source_name?: string; source_url?: string; yield_evidence?: string };
  ingredients: PreparationIngredient[];
};

export default function PreparationToMealPicker() {
  const { mealId, relationId, preparationId } = useLocalSearchParams<{ mealId?: string; relationId?: string; preparationId?: string }>();
  const meal = Number(mealId);
  const relation = Number(relationId);
  const initialPreparation = Number(preparationId);
  const router = useRouter();
  const setHeaderPresentation = useHeaderPresentation();
  const { status, apiRequest } = useSession();
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<PreparationDetail[]>([]);
  const [selected, setSelected] = useState<PreparationDetail | null>(null);
  const [mode, setMode] = useState<"units" | "grams">("units");
  const [units, setUnits] = useState(1);
  const [grams, setGrams] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showEvidence, setShowEvidence] = useState(false);
  const [scrollSignal, setScrollSignal] = useState(0);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ mode: "back", fallback: `/libraries/meals/${meal}` as Href, title: relation ? "Editar porción" : "Agregar preparación" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [meal, relation, setHeaderPresentation]));

  useEffect(() => {
    if (status !== "authenticated") return;
    let active = true;
    void apiRequest<{ items: PreparationDetail[] }>(`/api/v1/preparations?search=${encodeURIComponent(search)}`)
      .then((page) => { if (active) setItems(page.items); })
      .catch((failure) => { if (active) setError(userFacingError(failure)); });
    return () => { active = false; };
  }, [apiRequest, search, status]);
  useEffect(() => {
    if (status !== "authenticated" || !initialPreparation) return;
    void (async () => {
      try {
        const detail = await apiRequest<PreparationDetail>(`/api/v1/preparations/${initialPreparation}`);
        setSelected(detail);
        if (relation) {
          const saved = await apiRequest<LibraryItem>(`/api/v1/library/meals/${meal}`);
          const row = saved.panel.preparations?.find((item) => item.relation_id === relation);
          if (row) {
            setMode(row.selection_mode);
            setUnits(row.selected_units ?? 1);
            setGrams(String(row.quantity_g));
          }
        }
      } catch (failure) { setError(userFacingError(failure)); }
    })();
  }, [apiRequest, initialPreparation, meal, relation, status]);

  const selectedId = selected?.id;
  useEffect(() => {
    if (!selectedId || status !== "authenticated") return;
    const query = mode === "units" ? `units=${units}` : `grams=${encodeURIComponent(grams)}`;
    if (mode === "grams" && !(Number(grams) > 0)) return;
    let active = true;
    void apiRequest<PreparationDetail>(`/api/v1/preparations/${selectedId}?${query}`)
      .then((detail) => { if (active) setSelected(detail); })
      .catch((failure) => { if (active) setError(userFacingError(failure)); });
    return () => { active = false; };
  }, [apiRequest, mode, units, grams, selectedId, status]);

  async function save() {
    if (!selected || busy) return;
    setBusy(true); setError(null);
    try {
      const payload = mode === "units" ? { units, grams: null } : { units: null, grams: Number(grams) };
      const url = relation
        ? `/api/v1/library/meals/${meal}/preparations/${relation}`
        : `/api/v1/library/meals/${meal}/preparations`;
      await apiRequest(url, { method: relation ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(relation ? payload : { preparation_id: selected.id, ...payload }) });
      router.dismissTo(`/libraries/meals/${meal}` as Href);
    } catch (failure) { setError(userFacingError(failure)); }
    finally { setBusy(false); }
  }

  if (!Number.isInteger(meal) || meal <= 0) return <Redirect href="/libraries/meals" />;
  if (status === "anonymous") return <Redirect href="/login" />;
  return <Screen contentStyle={styles.content} headerMode="preserve" scrollToTopSignal={scrollSignal}>
    {!selected && !relation ? <>
      <SearchField accessibilityLabel="Buscar preparación" autoCapitalize="words" onChangeText={setSearch} onClear={() => setSearch("")} placeholder="Busca una preparación" value={search} />
      <Text style={styles.sectionHint}>Elige una preparación para revisar su porción e ingredientes.</Text>
      {items.map((item) => <Pressable
        accessibilityLabel={`Seleccionar ${item.name}`}
        accessibilityRole="button"
        key={item.id}
        onPress={() => { setSelected(item); setMode("units"); setUnits(1); setGrams(""); setScrollSignal((current) => current + 1); }}
        style={({ pressed }) => [styles.result, pressed && styles.pressed]}>
        <View style={styles.resultCopy}><Text style={styles.resultName}>{item.name}</Text><Text style={styles.resultMeta}>{formatPreparationNumber(item.default_portion_g)} g por {item.household_label}</Text></View>
        <Text style={styles.resultAction}>Elegir</Text>
      </Pressable>)}
      {!items.length ? <Text style={styles.empty}>No encontramos preparaciones con ese nombre.</Text> : null}
    </> : null}
    {selected ? <>
      {!relation ? <Pressable accessibilityRole="button" onPress={() => { setSelected(null); setScrollSignal((current) => current + 1); }} style={styles.changeSelection}><Text style={styles.changeSelectionText}>‹  Cambiar preparación</Text></Pressable> : null}
      <Card accent={tokens.color.meal}>
        <Text style={styles.eyebrow}>PREPARACIÓN SELECCIONADA</Text>
        <Text style={styles.selectedName}>{selected.name}</Text>
        <Text style={styles.selectedSubtitle}>{formatPreparationNumber(selected.grams)} g para esta porción · Estimación editorial</Text>
        <View style={styles.energyRow}><Text style={styles.energyValue}>{formatPreparationNumber(selected.nutrition.calories, 0)}</Text><Text style={styles.energyUnit}>kcal</Text></View>
        <View style={styles.macros}>
          <View style={styles.macro}><Text style={[styles.macroValue, { color: tokens.color.protein }]}>{formatPreparationNumber(selected.nutrition.protein_g)} g</Text><Text style={styles.macroLabel}>Proteína</Text></View>
          <View style={styles.macro}><Text style={[styles.macroValue, { color: tokens.color.carbs }]}>{formatPreparationNumber(selected.nutrition.carbs_g)} g</Text><Text style={styles.macroLabel}>Carbohidratos</Text></View>
          <View style={styles.macro}><Text style={[styles.macroValue, { color: tokens.color.fat }]}>{formatPreparationNumber(selected.nutrition.fat_g)} g</Text><Text style={styles.macroLabel}>Grasas</Text></View>
        </View>
      </Card>
      <Card>
        <Text style={styles.cardTitle}>Tu porción</Text>
        <ChoiceRow label="Medir por" onChange={(nextMode) => { setMode(nextMode); if (nextMode === "grams") setGrams(String(selected.grams)); }} options={[{ value: "units", label: "Unidades" }, { value: "grams", label: "Gramos" }]} value={mode} />
        {mode === "units" ? <>
          <View style={styles.stepper}>
            <Pressable accessibilityLabel="Reducir media unidad" accessibilityRole="button" accessibilityState={{ disabled: units <= 0.5 }} disabled={units <= 0.5} onPress={() => setUnits(Math.max(0.5, units - 0.5))} style={[styles.stepperButton, units <= 0.5 && styles.disabled]}><Minus color={tokens.color.textMain} size={21} /></Pressable>
            <View style={styles.stepperValue}><Text style={styles.unitsValue}>{formatPreparationNumber(units)}</Text><Text style={styles.unitsLabel}>{selected.household_label}</Text></View>
            <Pressable accessibilityLabel="Aumentar media unidad" accessibilityRole="button" accessibilityState={{ disabled: units >= 10 }} disabled={units >= 10} onPress={() => setUnits(Math.min(10, units + 0.5))} style={[styles.stepperButton, units >= 10 && styles.disabled]}><Plus color={tokens.color.textMain} size={21} /></Pressable>
          </View>
          <Text style={styles.portionHint}>Equivale aproximadamente a {formatPreparationNumber(selected.grams)} g.</Text>
        </> : <Field keyboardType="decimal-pad" label="Cantidad en gramos" onChangeText={setGrams} value={grams} />}
      </Card>
      <PreparationIngredientsCard ingredients={selected.ingredients} onOpenFood={(foodId) => router.push(`/libraries/foods/${foodId}` as Href)} />
      <Card muted>
        <Text style={styles.cardTitle}>Información adicional</Text>
        <View style={styles.infoRow}><Text style={styles.infoLabel}>Sodio</Text><Text style={styles.infoValue}>{selected.nutrition.sodium_mg == null ? "Sin dato" : `${formatPreparationNumber(selected.nutrition.sodium_mg, 0)} mg`}</Text></View>
        <View style={styles.infoRow}><Text style={styles.infoLabel}>Alérgenos declarados</Text><Text style={styles.infoValue}>{formatPreparationAllergens(selected.allergens)}</Text></View>
        <View style={styles.infoRow}><Text style={styles.infoLabel}>Fuente</Text><Text style={styles.infoValue}>{selected.evidence.source_name || "No indicada"}</Text></View>
        <Pressable accessibilityRole="button" onPress={() => setShowEvidence((current) => !current)} style={styles.evidenceToggle}><Text style={styles.evidenceToggleText}>{showEvidence ? "Ocultar estimación" : "Ver cómo se estimó la porción"}</Text></Pressable>
        {showEvidence ? <Text style={styles.sourceNote}>Versión {selected.version}{selected.evidence.yield_evidence ? ` · ${selected.evidence.yield_evidence}` : ""}</Text> : null}
      </Card>
      <Button disabled={mode === "grams" && !(Number(grams) > 0)} label={relation ? "Actualizar porción" : "Agregar a la comida"} loading={busy} onPress={() => void save()} />
    </> : null}
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
  </Screen>;
}

const styles = StyleSheet.create({
  content: { gap: tokens.spacing.lg },
  sectionHint: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 19 },
  result: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.panel, flexDirection: "row", gap: tokens.spacing.md, marginHorizontal: -tokens.spacing.screen, minHeight: 76, padding: tokens.card.outerPadding },
  resultCopy: { flex: 1, gap: tokens.spacing.xs, minWidth: 0 },
  resultName: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  resultMeta: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  resultAction: { color: tokens.color.interactivePrimary, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  pressed: { opacity: 0.7 },
  empty: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  changeSelection: { alignSelf: "flex-start", minHeight: 32, justifyContent: "center" },
  changeSelectionText: { color: tokens.color.interactivePrimary, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.semibold, letterSpacing: 1.1 },
  selectedName: { color: tokens.color.textMain, fontSize: 24, fontWeight: tokens.weight.extraBold, lineHeight: 29 },
  selectedSubtitle: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 19 },
  energyRow: { alignItems: "baseline", flexDirection: "row", gap: tokens.spacing.xs, marginTop: tokens.spacing.xs },
  energyValue: { color: tokens.color.textMain, fontSize: 38, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.extraBold, lineHeight: 42 },
  energyUnit: { color: tokens.color.textMuted, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  macros: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, paddingTop: tokens.spacing.md },
  macro: { flex: 1, gap: tokens.spacing.xs },
  macroValue: { fontSize: tokens.type.body, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold },
  macroLabel: { color: tokens.color.textMuted, fontSize: tokens.type.label },
  cardTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.bold },
  stepper: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  stepperButton: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, height: 48, justifyContent: "center", width: 48 },
  disabled: { opacity: 0.4 },
  stepperValue: { alignItems: "center", gap: 2 },
  unitsValue: { color: tokens.color.textMain, fontSize: 28, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.extraBold },
  unitsLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  portionHint: { color: tokens.color.textSoft, fontSize: tokens.type.caption, textAlign: "center" },
  infoRow: { alignItems: "flex-start", flexDirection: "row", justifyContent: "space-between", gap: tokens.spacing.md },
  infoLabel: { color: tokens.color.textMuted, flex: 1, fontSize: tokens.type.caption },
  infoValue: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, textAlign: "right" },
  sourceNote: { color: tokens.color.textSoft, fontSize: tokens.type.label, lineHeight: 17 },
  evidenceToggle: { alignSelf: "flex-start", minHeight: 32, justifyContent: "center" },
  evidenceToggleText: { color: tokens.color.interactivePrimary, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
});
