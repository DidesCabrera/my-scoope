import { type Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type {
  ComparisonKind,
  ComparisonMetadata,
  ComparisonOption,
  ComparisonOptionsData,
  ComparisonResult,
  ComparisonSelection,
  SavedComparisonDetail,
} from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ComparisonResultCards } from "@/components/comparisons/comparison-result";
import { EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { AppHeader, Button, Card, ChoiceRow, Field, LoadingState, Screen, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

type ComparisonSlot = {
  key: number;
  option: ComparisonOption | null;
  quantity: string;
};

const fallbackKinds = [
  { value: "foods" as const, label: "Alimentos" },
  { value: "meals" as const, label: "Comidas" },
  { value: "dailyplans" as const, label: "Planes" },
];

function emptySlots(): ComparisonSlot[] {
  return [
    { key: 1, option: null, quantity: "100" },
    { key: 2, option: null, quantity: "100" },
  ];
}

export default function ComparatorScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ kind?: string; savedId?: string }>();
  const savedId = Number(params.savedId || 0) || null;
  const { status, apiRequest } = useSession();
  const nextSlotKey = useRef(3);
  const [metadata, setMetadata] = useState<ComparisonMetadata | null>(null);
  const [kind, setKind] = useState<ComparisonKind>(params.kind === "meals" || params.kind === "dailyplans" ? params.kind : "foods");
  const [slots, setSlots] = useState<ComparisonSlot[]>(emptySlots);
  const [activeSlotKey, setActiveSlotKey] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<ComparisonOption[]>([]);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "authenticated") return;
    let active = true;
    Promise.all([
      apiRequest<ComparisonMetadata>("/api/v1/comparisons/metadata"),
      savedId ? apiRequest<SavedComparisonDetail>(`/api/v1/comparisons/saved/${savedId}`) : Promise.resolve(null),
    ])
      .then(([nextMetadata, saved]) => {
        if (!active) return;
        setMetadata(nextMetadata);
        if (saved) {
          setKind(saved.kind);
          const restored = saved.editable_selections.map((selection, index) => ({
            key: index + 1,
            option: {
              id: selection.id,
              name: saved.items[index]?.name ?? `Elemento ${selection.id}`,
            },
            quantity: String(selection.quantity ?? 100),
          }));
          setSlots(restored.length >= 2 ? restored : emptySlots());
          nextSlotKey.current = Math.max(restored.length + 1, 3);
        }
      })
      .catch((nextError) => active && setError(userFacingError(nextError)))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [apiRequest, savedId, status]);

  useEffect(() => {
    if (status !== "authenticated" || loading || activeSlotKey == null) return;
    let active = true;
    const timer = setTimeout(() => {
      setOptionsLoading(true);
      const search = query.trim() ? `&search=${encodeURIComponent(query.trim())}` : "";
      void apiRequest<ComparisonOptionsData>(`/api/v1/comparisons/options/${kind}?limit=100${search}`)
        .then((page) => active && setOptions(page.items))
        .catch((nextError) => active && setError(userFacingError(nextError)))
        .finally(() => active && setOptionsLoading(false));
    }, 250);
    return () => { active = false; clearTimeout(timer); };
  }, [activeSlotKey, apiRequest, kind, loading, query, status]);

  const kindChoices = useMemo(() => metadata?.kinds.map((item) => ({ value: item.key, label: item.label })) ?? fallbackKinds, [metadata]);
  const usesQuantity = metadata?.kinds.find((item) => item.key === kind)?.uses_quantity ?? kind === "foods";
  const selectedCount = slots.filter((slot) => slot.option).length;

  function invalidateResult() {
    setResult(null);
    setError(null);
  }

  function changeKind(nextKind: ComparisonKind) {
    setKind(nextKind);
    setSlots(emptySlots());
    nextSlotKey.current = 3;
    setActiveSlotKey(null);
    setQuery("");
    setOptions([]);
    invalidateResult();
  }

  function openSelector(slotKey: number) {
    setActiveSlotKey(slotKey);
    setQuery("");
    setOptions([]);
  }

  function selectOption(slotKey: number, option: ComparisonOption) {
    setSlots((current) => current.map((slot) => slot.key === slotKey ? { ...slot, option } : slot));
    setActiveSlotKey(null);
    setQuery("");
    invalidateResult();
  }

  function addSlot() {
    const key = nextSlotKey.current++;
    setSlots((current) => [...current, { key, option: null, quantity: "100" }]);
    setActiveSlotKey(key);
    setQuery("");
    invalidateResult();
  }

  function removeSlot(slotKey: number) {
    if (slots.length <= 2) return;
    setSlots((current) => current.filter((slot) => slot.key !== slotKey));
    if (activeSlotKey === slotKey) setActiveSlotKey(null);
    invalidateResult();
  }

  function requestSelections(): ComparisonSelection[] {
    return slots.flatMap((slot) => slot.option ? [{
      id: slot.option.id,
      quantity: usesQuantity ? Number(slot.quantity) : undefined,
    }] : []);
  }

  async function compare() {
    setWorking(true);
    setError(null);
    try {
      setResult(await apiRequest<ComparisonResult>("/api/v1/comparisons/compare", {
        method: "POST",
        body: JSON.stringify({ kind, selections: requestSelections() }),
      }));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setWorking(false);
    }
  }

  async function persist() {
    setWorking(true);
    setError(null);
    try {
      const path = savedId ? `/api/v1/comparisons/saved/${savedId}` : "/api/v1/comparisons/saved";
      const saved = await apiRequest<SavedComparisonDetail>(path, {
        method: savedId ? "PUT" : "POST",
        body: JSON.stringify({ kind, selections: requestSelections() }),
      });
      router.replace(`/comparator/saved/${saved.saved_comparison_id}` as Href);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setWorking(false);
    }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Preparando el comparador…" />;

  return (
    <Screen>
      <AppHeader eyebrow={savedId ? "Edición de comparación guardada" : "Herramienta nutricional"} title="Comparador" />
      <Button label="Ver comparaciones guardadas" onPress={() => router.push("/comparator/saved" as Href)} variant="secondary" />
      <ChoiceRow<ComparisonKind> label="Tipo de comparación" onChange={changeKind} options={kindChoices} value={kind} />

      <View style={styles.slots}>
        {slots.map((slot, index) => {
          const selectorOpen = activeSlotKey === slot.key;
          return (
            <Card key={slot.key} muted={!slot.option}>
              <View style={styles.slotHeading}>
                <View style={styles.slotIdentity}>
                  <View style={styles.slotBadge}><Text style={styles.slotBadgeText}>{index + 1}</Text></View>
                  <View style={styles.slotCopy}>
                    <Text style={styles.slotLabel}>{metadata?.kinds.find((item) => item.key === kind)?.entity_label ?? "Elemento"} {index + 1}</Text>
                    <Text style={slot.option ? styles.slotName : textStyles.muted}>{slot.option?.name ?? "Sin seleccionar"}</Text>
                  </View>
                </View>
                {slots.length > 2 ? (
                  <Pressable accessibilityLabel={`Eliminar slot ${index + 1}`} accessibilityRole="button" onPress={() => removeSlot(slot.key)} style={styles.remove}>
                    <Text style={styles.removeText}>×</Text>
                  </Pressable>
                ) : null}
              </View>

              <Button label={slot.option ? "Cambiar selección" : "Seleccionar"} onPress={() => openSelector(slot.key)} variant="secondary" />
              {usesQuantity && slot.option ? (
                <Field
                  keyboardType="decimal-pad"
                  label="Cantidad (g)"
                  onChangeText={(quantity) => {
                    setSlots((current) => current.map((row) => row.key === slot.key ? { ...row, quantity } : row));
                    invalidateResult();
                  }}
                  value={slot.quantity}
                />
              ) : null}

              {selectorOpen ? (
                <View style={styles.selector}>
                  <Field autoCapitalize="words" label="Buscar en tu librería" onChangeText={setQuery} placeholder="Escribe un nombre" value={query} />
                  {optionsLoading ? <Text style={textStyles.caption}>Buscando…</Text> : null}
                  {options.map((option) => (
                    <Pressable accessibilityLabel={`Seleccionar ${option.name}`} accessibilityRole="button" key={option.id} onPress={() => selectOption(slot.key, option)} style={styles.option}>
                      <Text style={styles.optionText}>{option.name}</Text><Text style={styles.optionMark}>›</Text>
                    </Pressable>
                  ))}
                  {!optionsLoading && options.length === 0 ? <Text style={textStyles.muted}>No encontramos opciones.</Text> : null}
                  <Button label="Cerrar selector" onPress={() => setActiveSlotKey(null)} variant="secondary" />
                </View>
              ) : null}
            </Card>
          );
        })}
      </View>

      <Button label={`Agregar ${metadata?.kinds.find((item) => item.key === kind)?.entity_label ?? "elemento"}`} onPress={addSlot} variant="secondary" />
      {error ? <RecoverableErrorState message={error} onRetry={() => void compare()} /> : null}
      <Button disabled={selectedCount < 2} label="Comparar" loading={working} onPress={() => void compare()} />
      {result ? (
        <>
          <ComparisonResultCards result={result} />
          <Button label={savedId ? "Guardar cambios" : "Guardar comparación"} loading={working} onPress={() => void persist()} variant="secondary" />
        </>
      ) : (
        <EmptyState message="Completa al menos dos slots. Puedes repetir una entidad con cantidades diferentes para comparar porciones." title="Aún no hay resultado" />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  option: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 48, paddingVertical: tokens.spacing.sm },
  optionMark: { color: tokens.color.interactivePrimary, fontSize: 24 },
  optionText: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, fontWeight: "700" },
  remove: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 18, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  removeText: { color: tokens.color.textMuted, fontSize: 24, lineHeight: 26 },
  selector: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, gap: tokens.spacing.sm, paddingTop: tokens.spacing.md },
  slotBadge: { alignItems: "center", backgroundColor: tokens.color.interactivePrimary, borderRadius: 6, height: 28, justifyContent: "center", width: 28 },
  slotBadgeText: { color: "#FFFFFF", fontSize: 13, fontWeight: "900" },
  slotCopy: { flex: 1, gap: 3 },
  slotHeading: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  slotIdentity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm },
  slotLabel: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: "800", textTransform: "uppercase" },
  slotName: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: "800" },
  slots: { gap: tokens.spacing.md },
});
