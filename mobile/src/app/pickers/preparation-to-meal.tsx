import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { PreparationDetail } from "@/api/preparations";
import type { LibraryItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { FoodPortionField } from "@/components/pickers/food-portion-field";
import { formatPreparationAllergens, formatPreparationNumber } from "@/components/preparations/preparation-ingredients-card";
import { PreparationMealPreviewCard } from "@/components/preparations/preparation-meal-preview-card";
import { PreparationPickerCard } from "@/components/preparations/preparation-picker-card";
import { Button } from "@/components/ui/controls";
import { Screen } from "@/components/ui/layout";
import { InlineNotice } from "@/components/ui/primitives";
import { SearchField } from "@/components/ui/search-field";
import { Card } from "@/components/ui/surfaces";
import { LoadingState } from "@/components/ui";
import { tokens } from "@/design/tokens";

const unitOptions = Array.from({ length: 20 }, (_, index) => (index + 1) / 2);

export default function PreparationToMealPicker() {
  const { mealId, relationId, preparationId, replace } = useLocalSearchParams<{ mealId?: string; relationId?: string; preparationId?: string; replace?: string }>();
  const meal = Number(mealId);
  const relation = Number(relationId);
  const selectedPreparationId = Number(preparationId);
  const router = useRouter();
  const setHeaderPresentation = useHeaderPresentation();
  const { status, apiRequest } = useSession();
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<PreparationDetail[]>([]);
  const [selected, setSelected] = useState<PreparationDetail | null>(null);
  const [mealItem, setMealItem] = useState<LibraryItem | null>(null);
  const [mode, setMode] = useState<"units" | "grams">("units");
  const [amount, setAmount] = useState("1");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showEvidence, setShowEvidence] = useState(false);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ mode: "back", fallback: `/libraries/meals/${meal}` as Href, title: replace === "1" ? "Reemplazar preparación" : relation ? "Editar porción" : "Agregar preparación" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [meal, relation, replace, setHeaderPresentation]));

  useEffect(() => {
    if (status !== "authenticated" || selectedPreparationId) return;
    let active = true;
    void apiRequest<{ items: PreparationDetail[] }>(`/api/v1/preparations?search=${encodeURIComponent(search)}`)
      .then((page) => { if (active) setItems(page.items); })
      .catch((failure) => { if (active) setError(userFacingError(failure)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, search, selectedPreparationId, status]);

  useEffect(() => {
    if (status !== "authenticated" || !selectedPreparationId) return;
    let active = true;
    void (async () => {
      try {
        const [detail, saved] = await Promise.all([
          apiRequest<PreparationDetail>(`/api/v1/preparations/${selectedPreparationId}`),
          apiRequest<LibraryItem>(`/api/v1/library/meals/${meal}`),
        ]);
        if (relation) {
          const row = saved.panel.preparations?.find((item) => item.relation_id === relation);
          if (row && active) {
            setMode(row.selection_mode);
            setAmount(String(row.selection_mode === "units" ? row.selected_units ?? 1 : row.quantity_g));
          }
        }
        if (active) { setSelected(detail); setMealItem(saved); }
      } catch (failure) {
        if (active) setError(userFacingError(failure));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [apiRequest, meal, relation, selectedPreparationId, status]);

  const selectedId = selected?.id;
  const numericAmount = Number(amount.replace(",", "."));
  const amountValid = mode === "units"
    ? numericAmount >= 0.5 && numericAmount <= 10
    : numericAmount > 0 && numericAmount <= (selected?.default_portion_g ?? 0) * 10;
  const previewReady = Boolean(selected && amountValid && selected.selection_mode === mode && Math.abs((mode === "units" ? selected.selected_units ?? 1 : selected.grams) - numericAmount) < 0.001);
  useEffect(() => {
    if (!selectedId || !amountValid || status !== "authenticated") return;
    let active = true;
    const query = mode === "units" ? `units=${numericAmount}` : `grams=${numericAmount}`;
    void apiRequest<PreparationDetail>(`/api/v1/preparations/${selectedId}?${query}`)
      .then((detail) => { if (active) setSelected(detail); })
      .catch((failure) => { if (active) setError(userFacingError(failure)); });
    return () => { active = false; };
  }, [amountValid, apiRequest, mode, numericAmount, selectedId, status]);

  async function save() {
    if (!selected || !previewReady || !mealItem || busy) return;
    setBusy(true);
    setError(null);
    try {
      const payload = mode === "units" ? { units: numericAmount, grams: null } : { units: null, grams: numericAmount };
      const url = relation
        ? `/api/v1/library/meals/${meal}/preparations/${relation}`
        : `/api/v1/library/meals/${meal}/preparations`;
      await apiRequest(url, { method: relation ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(relation && replace !== "1" ? payload : { preparation_id: selected.id, ...payload }) });
      router.dismissTo(`/libraries/meals/${meal}` as Href);
    } catch (failure) {
      setError(userFacingError(failure));
    } finally {
      setBusy(false);
    }
  }

  if (!Number.isInteger(meal) || meal <= 0) return <Redirect href="/libraries/meals" />;
  if (status === "anonymous") return <Redirect href="/login" />;
  if (selectedPreparationId && loading && !selected) return <LoadingState label="Preparando la porción…" />;

  return <Screen contentStyle={styles.content} headerMode="preserve">
    {!selectedPreparationId ? <>
      <SearchField accessibilityLabel="Buscar preparación" autoCapitalize="words" onChangeText={(value) => { setSearch(value); setLoading(true); }} onClear={() => { setSearch(""); setLoading(true); }} placeholder="Busca una preparación" value={search} />
      <View style={styles.results}>
        {items.map((item) => <PreparationPickerCard
          actionLabel="Seleccionar"
          detail={item}
          key={item.id}
          onAction={() => router.push({ pathname: "/pickers/preparation-to-meal", params: { mealId: String(meal), preparationId: String(item.id), ...(relation && replace === "1" ? { relationId: String(relation), replace } : {}) } })}
          onOpenItem={(component) => {
            if (component.detailId != null) router.push((component.kind === "preparation" ? `/libraries/preparations/${component.detailId}` : `/libraries/foods/${component.detailId}`) as Href);
          }}
        />)}
      </View>
      {!loading && !items.length && !error ? <Text style={styles.empty}>No encontramos preparaciones con ese nombre.</Text> : null}
    </> : selected ? <>
      <Card style={styles.portionCard}>
        <FoodPortionField
          accentColor={tokens.color.preparation}
          equivalentMetricAmount={selected.grams}
          householdDefaultAmount={1}
          householdMeasureLabel={selected.household_label === "completo mediano" ? "completo" : selected.household_label}
          householdPluralLabel={selected.household_label === "completo mediano" ? "completos" : undefined}
          householdPortionValues={unitOptions}
          initiallyExpanded
          label="Porción"
          measure={mode === "units" ? "household" : "metric"}
          metricDefaultAmount={selected.default_portion_g}
          metricUnit="g"
          onChange={setAmount}
          onMeasureChange={(measure) => setMode(measure === "household" ? "units" : "grams")}
          value={amount}
        />
      </Card>
      <PreparationPickerCard detail={selected} onOpenItem={(item) => {
        if (item.detailId != null) router.push((item.kind === "preparation" ? `/libraries/preparations/${item.detailId}` : `/libraries/foods/${item.detailId}`) as Href);
      }} selected />
      {previewReady && mealItem ? <PreparationMealPreviewCard meal={mealItem} relationId={relation || undefined} selected={selected} /> : <Text style={styles.empty}>Actualizando la previsualización de la comida…</Text>}
      <Card muted>
        <Text style={styles.cardTitle}>Información adicional</Text>
        <View style={styles.infoRow}><Text style={styles.infoLabel}>Sodio</Text><Text style={styles.infoValue}>{selected.nutrition.sodium_mg == null ? "Sin dato" : `${formatPreparationNumber(selected.nutrition.sodium_mg, 0)} mg`}</Text></View>
        <View style={styles.infoRow}><Text style={styles.infoLabel}>Alérgenos declarados</Text><Text style={styles.infoValue}>{formatPreparationAllergens(selected.allergens)}</Text></View>
        <View style={styles.infoRow}><Text style={styles.infoLabel}>Fuente</Text><Text style={styles.infoValue}>{selected.evidence.source_name || "No indicada"}</Text></View>
        <Pressable accessibilityRole="button" onPress={() => setShowEvidence((current) => !current)} style={styles.evidenceToggle}><Text style={styles.evidenceToggleText}>{showEvidence ? "Ocultar estimación" : "Ver cómo se estimó la porción"}</Text></Pressable>
        {showEvidence ? <Text style={styles.sourceNote}>Versión {selected.version}{selected.evidence.yield_evidence ? ` · ${selected.evidence.yield_evidence}` : ""}</Text> : null}
      </Card>
      <Button disabled={!previewReady || !mealItem} label={replace === "1" ? "Reemplazar preparación" : relation ? "Actualizar porción" : "Agregar a la comida"} loading={busy} onPress={() => void save()} />
    </> : null}
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
  </Screen>;
}

const styles = StyleSheet.create({
  content: { gap: tokens.spacing.lg },
  results: { gap: tokens.spacing.lg },
  portionCard: { paddingVertical: tokens.spacing.sm },
  empty: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  cardTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.bold },
  infoRow: { alignItems: "flex-start", flexDirection: "row", justifyContent: "space-between", gap: tokens.spacing.md },
  infoLabel: { color: tokens.color.textMuted, flex: 1, fontSize: tokens.type.caption },
  infoValue: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, textAlign: "right" },
  sourceNote: { color: tokens.color.textSoft, fontSize: tokens.type.label, lineHeight: 17 },
  evidenceToggle: { alignSelf: "flex-start", minHeight: 32, justifyContent: "center" },
  evidenceToggleText: { color: tokens.color.interactivePrimary, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
});
