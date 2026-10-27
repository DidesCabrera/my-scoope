import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Carrot, ClipboardList, Plus, RefreshCcw, Search, Utensils } from "lucide-react-native";
import { useCallback, useEffect, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type {
  ComparisonKind,
  ComparisonMetadata,
  ComparisonResult,
  ComparisonSelection,
  EntitlementsData,
  SavedComparisonDetail,
  SavedComparisonListData,
  ShareResource,
} from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ComparisonResultCards } from "@/components/comparisons/comparison-result";
import { ComparisonCreateActions, SavedComparisonListCard } from "@/components/comparisons";
import {
  applyComparatorSelection,
  initialComparisonSlots,
  type ComparisonSlot,
} from "@/components/comparisons/comparison-state";
import { useComparatorSelectionTransfer } from "@/components/comparisons/comparator-selection-context";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { NutritionKpiSection } from "@/components/nutrition";
import { isCommercialLimitError, reachedCommercialLimit } from "@/components/subscriptions/commercial-limit";
import { CommercialLimitSheet, type CommercialLimitState } from "@/components/subscriptions/commercial-limit-sheet";
import {
  DistributedTabBar,
  EntityCard,
  SectionPageHeader,
} from "@/components/ui";
import { EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { Button, Field, LoadingState, Screen } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

const fallbackKinds = [
  { value: "foods" as const, icon: Carrot, label: "Alimentos" },
  { value: "meals" as const, icon: Utensils, label: "Comidas" },
  { value: "dailyplans" as const, icon: ClipboardList, label: "Minutas" },
];

const comparisonEntities = {
  foods: "food",
  meals: "meal",
  dailyplans: "dailyPlan",
} as const satisfies Record<ComparisonKind, "food" | "meal" | "dailyPlan">;

type ComparisonPages = Record<ComparisonKind, SavedComparisonListData>;

function creationHref(kind: ComparisonKind): Href {
  return { pathname: "/comparator", params: { create: "1", kind } } as Href;
}

function ComparisonKindTabs({ counts, kind, onChange }: { counts?: Record<ComparisonKind, number>; kind: ComparisonKind; onChange(nextKind: ComparisonKind): void }) {
  return (
    <DistributedTabBar<ComparisonKind>
      accessibilityLabel="Tipo de comparación"
      activeTab={kind}
      onChange={onChange}
      tabs={fallbackKinds.map((tab) => ({
        count: counts?.[tab.value],
        icon: (selected) => {
          const Icon = tab.icon;
          return <Icon color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />;
        },
        key: tab.value,
        label: tab.label,
      }))}
    />
  );
}

function ComparatorDashboard() {
  const router = useRouter();
  const params = useLocalSearchParams<{ kind?: string }>();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [kind, setKind] = useState<ComparisonKind>(params.kind === "meals" || params.kind === "dailyplans" ? params.kind : "foods");
  const [counts, setCounts] = useState<Record<ComparisonKind, number>>({ dailyplans: 0, foods: 0, meals: 0 });
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [pages, setPages] = useState<ComparisonPages | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createActionsVisible, setCreateActionsVisible] = useState(false);
  const page = pages?.[kind] ?? null;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const loadedPages = await Promise.all(fallbackKinds.map((item) => apiRequest<SavedComparisonListData>(`/api/v1/comparisons/saved?limit=50&kind=${item.value}`)));
      const nextPages = { dailyplans: loadedPages[2], foods: loadedPages[0], meals: loadedPages[1] };
      setCounts({ dailyplans: nextPages.dailyplans.total, foods: nextPages.foods.total, meals: nextPages.meals.total });
      setPages(nextPages);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ action: { icon: "plus", label: "Crear una comparación", onPress: () => setCreateActionsVisible(true) }, identityVisible: compactHeaderVisible, mode: "default", title: "Comparaciones" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, setHeaderPresentation]));
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !page) return <LoadingState label="Buscando tus comparaciones…" />;

  return (
    <>
      <Screen
        headerMode="preserve"
        onHeaderVisibilityChange={setCompactHeaderVisible}
        scrollHeader={<SectionPageHeader countLabel="comparaciones" section="comparator" subtitle="Compara los elementos de tu librería. Comprende las similitudes y diferencias, y reemplázalos en tu dieta." title="Comparaciones" />}
        stickyHeader={<ComparisonKindTabs counts={counts} kind={kind} onChange={(nextKind) => { setKind(nextKind); router.setParams({ kind: nextKind }); }} />}
        stickyHeaderStyle={styles.dashboardStickyHeader}>
        {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
        {page?.items.length ? page.items.map((item) => <SavedComparisonListCard
          item={item}
          key={item.id}
          onDelete={async () => {
            await apiRequest<{ deleted_id: number }>(`/api/v1/comparisons/saved/${item.id}`, { method: "DELETE" });
            await load();
          }}
          onEdit={() => router.push({ pathname: "/comparator", params: { kind: item.kind, savedId: String(item.id) } } as Href)}
          onPress={() => router.push({ pathname: "/comparator/saved/[id]", params: { id: String(item.id), kind: item.kind } } as Href)}
          onRename={async (name) => {
            await apiRequest<SavedComparisonDetail>(`/api/v1/comparisons/saved/${item.id}/name`, {
              body: JSON.stringify({ name }),
              headers: { "Content-Type": "application/json" },
              method: "PATCH",
            });
            await load();
          }}
          onShare={() => apiRequest<ShareResource>(`/api/v1/shares/comparisons/${item.id}`, {
            body: JSON.stringify({ claim_policy: "multiple" }),
            headers: { "Content-Type": "application/json" },
            method: "POST",
          })}
        />) : (
          <EmptyState actionLabel="Crear nueva comparación" message={`Todavía no tienes comparaciones guardadas de ${fallbackKinds.find((item) => item.value === kind)?.label.toLowerCase()}.`} onAction={() => router.push(creationHref(kind))} title="Aún no hay comparaciones" />
        )}
      </Screen>
      <ComparisonCreateActions
        onClose={() => setCreateActionsVisible(false)}
        onSelect={(selectedKind) => router.push(creationHref(selectedKind))}
        visible={createActionsVisible}
      />
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
  const [slots, setSlots] = useState<ComparisonSlot[]>(initialComparisonSlots);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [commercialLimit, setCommercialLimit] = useState<CommercialLimitState | null>(null);

  useFocusEffect(useCallback(() => {
    const fallback = { pathname: "/comparator", params: { kind } } as Href;
    setHeaderPresentation({ fallback, mode: "back", title: savedId ? "Editar comparación" : "Nueva comparación" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [kind, savedId, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    const selection = consumeSelection();
    if (!selection || selection.kind !== kind) return;
    setSlots((current) => applyComparatorSelection(current, selection));
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
          const restored: ComparisonSlot[] = saved.editable_selections.map((selection, index) => ({
            key: index + 1,
            option: {
              id: selection.id,
              name: saved.items[index]?.name ?? `Elemento ${selection.id}`,
              quantity_unit: saved.items[index]?.quantity_unit === "ml" ? "ml" : "g",
            },
            quantity: String(selection.quantity ?? 100),
          }));
          setSlots(restored.length >= 2 ? restored : initialComparisonSlots());
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
  const entityLabel = metadata?.kinds.find((item) => item.key === kind)?.entity_label ?? "Elemento";
  const anotherEntityLabel = `Agregar ${kind === "meals" ? "otra" : "otro"} ${entityLabel}`;

  function invalidateResult() {
    setResult(null);
    setError(null);
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
      if (!savedId) {
        const entitlements = await apiRequest<EntitlementsData>("/api/v1/entitlements", { cache: "no-store" });
        const reachedLimit = reachedCommercialLimit(entitlements, "comparison");
        if (reachedLimit) {
          setCommercialLimit(reachedLimit);
          return;
        }
      }
      const path = savedId ? `/api/v1/comparisons/saved/${savedId}` : "/api/v1/comparisons/saved";
      const saved = await apiRequest<SavedComparisonDetail>(path, {
        method: savedId ? "PUT" : "POST",
        body: JSON.stringify({ kind, selections: requestSelections() }),
      });
      router.replace({ pathname: "/comparator/saved/[id]", params: { id: String(saved.saved_comparison_id), kind: saved.kind } } as Href);
    } catch (nextError) {
      if (!savedId && isCommercialLimitError(nextError, "comparison")) {
        try {
          const entitlements = await apiRequest<EntitlementsData>("/api/v1/entitlements", { cache: "no-store" });
          const reachedLimit = reachedCommercialLimit(entitlements, "comparison");
          if (reachedLimit) {
            setCommercialLimit(reachedLimit);
            return;
          }
        } catch {
          // Preserve the original server response when the refresh also fails.
        }
      }
      setError(userFacingError(nextError));
    } finally {
      setWorking(false);
    }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Preparando la comparación…" />;

  return (
    <>
    <View style={styles.builderRoot}>
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
                eyebrow={`${entityLabel} ${index + 1}`}
                key={slot.key}
                title={slot.option?.name ?? "Sin seleccionar"}>

                {slot.option?.nutrition ? (
                  <NutritionKpiSection variant="nested" {...libraryNutrition(slot.option.nutrition)} />
                ) : null}
                <Button
                  contentStyle={styles.comparisonButtonContent}
                  icon={slot.option
                    ? <RefreshCcw color={tokens.color.textMain} size={18} />
                    : <Search color={tokens.color.textMain} size={18} />}
                  label={slot.option ? "Cambiar selección" : `Seleccionar ${entityLabel}`}
                  onPress={() => openSelector(slot.key)}
                  variant="secondary"
                />
                {usesQuantity && slot.option ? (
                  <Field
                    keyboardType="decimal-pad"
                    label={`Cantidad (${slot.option.quantity_unit ?? "g"})`}
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

        <Button contentStyle={styles.comparisonButtonContent} icon={<Plus color={tokens.color.textMain} size={19} />} label={anotherEntityLabel} onPress={addSlot} variant="secondary" />
        {error ? <RecoverableErrorState message={error} onRetry={() => void compare()} /> : null}
        <View style={styles.compareAction}>
          <Button disabled={selectedCount < 2 || result != null} label="Comparar" loading={working} onPress={() => void compare()} />
        </View>
        {result ? (
          <>
            <ComparisonResultCards result={result} />
            <View style={styles.saveAction}>
              <Button label={savedId ? "Guardar cambios" : "Guardar comparación"} loading={working} onPress={() => void persist()} />
            </View>
          </>
        ) : null}
      </Screen>
    </View>
    {commercialLimit ? <CommercialLimitSheet {...commercialLimit} onClose={() => setCommercialLimit(null)} onUpgrade={() => { setCommercialLimit(null); router.push("/subscription"); }} visible /> : null}
    </>
  );
}

export default function ComparatorScreen() {
  const params = useLocalSearchParams<{ create?: string; savedId?: string }>();
  return params.create === "1" || params.savedId ? <ComparatorBuilderScreen /> : <ComparatorDashboard />;
}

const styles = StyleSheet.create({
  builderRoot: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  comparisonButtonContent: { transform: [{ translateX: -10 }] },
  compareAction: { marginTop: 28 },
  dashboardStickyHeader: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, paddingTop: tokens.spacing.sm },
  remove: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 18, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  removeText: { color: tokens.color.textMuted, fontSize: 24, lineHeight: 26 },
  saveAction: { marginTop: 40 },
  slots: { gap: tokens.spacing.md },
});
