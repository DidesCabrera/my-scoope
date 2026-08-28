import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Carrot, ClipboardList, Utensils } from "lucide-react-native";
import { useCallback, useEffect, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type {
  ComparisonKind,
  ComparisonMetadata,
  ComparisonResult,
  ComparisonSelection,
  SavedComparisonDetail,
  SavedComparisonListData,
  SavedComparisonSummary,
  SelectedComparisonOption,
} from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ComparisonResultCards } from "@/components/comparisons/comparison-result";
import { useComparatorSelectionTransfer } from "@/components/comparisons/comparator-selection-context";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { NutritionKpiSection } from "@/components/nutrition";
import { EntityCard, SectionPageHeader } from "@/components/ui";
import { EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { Button, Card, Field, LoadingState, Pill, Screen, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

type ComparisonSlot = {
  key: number;
  option: SelectedComparisonOption | null;
  quantity: string;
};

const fallbackKinds = [
  { value: "foods" as const, icon: Carrot, label: "Alimentos" },
  { value: "meals" as const, icon: Utensils, label: "Comidas" },
  { value: "dailyplans" as const, icon: ClipboardList, label: "Planes" },
];

const comparisonEntities = {
  foods: "food",
  meals: "meal",
  dailyplans: "dailyPlan",
} as const satisfies Record<ComparisonKind, "food" | "meal" | "dailyPlan">;

function emptySlots(): ComparisonSlot[] {
  return [
    { key: 1, option: null, quantity: "100" },
    { key: 2, option: null, quantity: "100" },
  ];
}

function creationHref(kind: ComparisonKind): Href {
  return { pathname: "/comparator", params: { create: "1", kind } } as Href;
}

function SavedCard({ item, onPress }: { item: SavedComparisonSummary; onPress(): void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => pressed && styles.pressed}>
      <Card>
        <View style={styles.savedRow}>
          <View style={styles.savedCopy}>
            <Text style={styles.savedTitle}>{item.name}</Text>
            <Text style={textStyles.caption}>{new Intl.DateTimeFormat("es-CL", { dateStyle: "medium" }).format(new Date(item.updated_at))}</Text>
          </View>
          <Pill label={`${item.item_count} elementos`} />
        </View>
        <Text style={textStyles.muted}>Ver comparación guardada ›</Text>
      </Card>
    </Pressable>
  );
}

function ComparisonKindTabs({ kind, onChange }: { kind: ComparisonKind; onChange(nextKind: ComparisonKind): void }) {
  return (
    <View accessibilityLabel="Tipo de comparación" accessibilityRole="tablist" style={styles.kindTabs}>
      {fallbackKinds.map((tab) => {
        const selected = kind === tab.value;
        const Icon = tab.icon;
        return (
          <Pressable
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            key={tab.value}
            onPress={() => onChange(tab.value)}
            style={({ pressed }) => [styles.kindTab, selected && styles.kindTabActive, pressed && styles.pressed]}
          >
            <Icon color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />
            <Text style={[styles.kindTabText, selected && styles.kindTabTextActive]}>{tab.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function ComparatorDashboard() {
  const router = useRouter();
  const params = useLocalSearchParams<{ kind?: string }>();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [kind, setKind] = useState<ComparisonKind>(params.kind === "meals" || params.kind === "dailyplans" ? params.kind : "foods");
  const [page, setPage] = useState<SavedComparisonListData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPage(await apiRequest<SavedComparisonListData>(`/api/v1/comparisons/saved?limit=50&kind=${kind}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, kind]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ action: { icon: "plus", label: "Crear una comparación", onPress: () => router.push(creationHref(kind)) }, mode: "default" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [kind, router, setHeaderPresentation]));
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !page) return <LoadingState label="Buscando tus comparaciones…" />;

  return (
    <>
      <Screen headerMode="preserve">
        <SectionPageHeader count={page?.total} countLabel="comparaciones" section="comparator" title="Comparador" />
        <ComparisonKindTabs kind={kind} onChange={(nextKind) => { setKind(nextKind); router.setParams({ kind: nextKind }); }} />
        {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
        {page?.items.length ? page.items.map((item) => <SavedCard item={item} key={item.id} onPress={() => router.push(`/comparator/saved/${item.id}` as Href)} />) : (
          <EmptyState actionLabel="Crear nueva comparación" message={`Todavía no tienes comparaciones guardadas de ${fallbackKinds.find((item) => item.value === kind)?.label.toLowerCase()}.`} onAction={() => router.push(creationHref(kind))} title="Aún no hay comparaciones" />
        )}
      </Screen>
    </>
  );
}

function ComparatorBuilderScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ kind?: string; savedId?: string }>();
  const savedId = Number(params.savedId || 0) || null;
  const { status, apiRequest } = useSession();
  const { consumeSelection } = useComparatorSelectionTransfer();
  const setHeaderPresentation = useHeaderPresentation();
  const nextSlotKey = useRef(3);
  const [metadata, setMetadata] = useState<ComparisonMetadata | null>(null);
  const [kind, setKind] = useState<ComparisonKind>(params.kind === "meals" || params.kind === "dailyplans" ? params.kind : "foods");
  const [slots, setSlots] = useState<ComparisonSlot[]>(emptySlots);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(useCallback(() => {
    const fallback = { pathname: "/comparator", params: { kind } } as Href;
    const cancel = () => { if (router.canGoBack()) router.back(); else router.replace(fallback); };
    setHeaderPresentation({ action: { label: "Cancelar", onPress: cancel }, fallback, mode: "back", title: savedId ? "Editar comparación" : "Nueva comparación" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [kind, router, savedId, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    const selection = consumeSelection();
    if (!selection || selection.kind !== kind) return;
    setSlots((current) => current.map((slot) => slot.key === selection.slotKey ? { ...slot, option: selection.option } : slot));
    setResult(null);
    setError(null);
  }, [consumeSelection, kind]));

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

  const usesQuantity = metadata?.kinds.find((item) => item.key === kind)?.uses_quantity ?? kind === "foods";
  const selectedCount = slots.filter((slot) => slot.option).length;
  const entity = comparisonEntities[kind];

  function invalidateResult() {
    setResult(null);
    setError(null);
  }

  function changeKind(nextKind: ComparisonKind) {
    setKind(nextKind);
    setSlots(emptySlots());
    nextSlotKey.current = 3;
    invalidateResult();
  }

  function openSelector(slotKey: number) {
    router.push({ pathname: "/comparator/select", params: { kind, savedId: savedId ? String(savedId) : undefined, slotKey: String(slotKey) } } as Href);
  }

  function addSlot() {
    const key = nextSlotKey.current++;
    setSlots((current) => [...current, { key, option: null, quantity: "100" }]);
    openSelector(key);
    invalidateResult();
  }

  function removeSlot(slotKey: number) {
    if (slots.length <= 2) return;
    setSlots((current) => current.filter((slot) => slot.key !== slotKey));
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
    <View style={styles.builderRoot}>
      <View style={styles.builderTabs}>
        <ComparisonKindTabs kind={kind} onChange={changeKind} />
      </View>
      <Screen headerMode="preserve">

        <View style={styles.slots}>
          {slots.map((slot, index) => {
            return (
              <EntityCard
                accessory={slots.length > 2 ? (
                    <Pressable accessibilityLabel={`Eliminar slot ${index + 1}`} accessibilityRole="button" onPress={() => removeSlot(slot.key)} style={styles.remove}>
                      <Text style={styles.removeText}>×</Text>
                    </Pressable>
                ) : undefined}
                entity={entity}
                eyebrow={`${metadata?.kinds.find((item) => item.key === kind)?.entity_label ?? "Elemento"} ${index + 1}`}
                key={slot.key}
                title={slot.option?.name ?? "Sin seleccionar"}>

                {slot.option?.nutrition ? (
                  <NutritionKpiSection variant="nested" {...libraryNutrition(slot.option.nutrition)} />
                ) : null}
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

              </EntityCard>
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
    </View>
  );
}

export default function ComparatorScreen() {
  const params = useLocalSearchParams<{ create?: string; savedId?: string }>();
  return params.create === "1" || params.savedId ? <ComparatorBuilderScreen /> : <ComparatorDashboard />;
}

const styles = StyleSheet.create({
  builderRoot: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  builderTabs: { backgroundColor: tokens.color.surfaceApp, borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, paddingBottom: tokens.spacing.sm, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.xs },
  kindTab: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "center", minHeight: 30, paddingHorizontal: tokens.spacing.md },
  kindTabActive: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  kindTabText: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "500" },
  kindTabTextActive: { color: tokens.color.surfaceApp },
  kindTabs: { flexDirection: "row", gap: tokens.spacing.compact },
  remove: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 18, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  removeText: { color: tokens.color.textMuted, fontSize: 24, lineHeight: 26 },
  pressed: { opacity: 0.68 },
  savedCopy: { flex: 1, gap: tokens.spacing.xs },
  savedRow: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md },
  savedTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  slots: { gap: tokens.spacing.md },
});
