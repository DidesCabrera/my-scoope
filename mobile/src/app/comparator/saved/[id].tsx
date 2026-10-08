import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Carrot, ClipboardList, LayoutGrid, Utensils } from "lucide-react-native";
import { useCallback, useMemo, useState } from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { LibraryItem, SavedComparisonDetail } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ComparisonResultCards } from "@/components/comparisons/comparison-result";
import { SavedComparisonActions } from "@/components/comparisons/saved-comparison-actions";
import { LibraryCard } from "@/components/libraries/library-card";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { DistributedTabBar, EntityIcon } from "@/components/ui";
import { RecoverableErrorState } from "@/components/ui/screen-states";
import { AppHeader, LoadingState, Screen } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

type DetailTab = "cards" | "entities";

const entityTabLabels = { dailyplans: "Planes", foods: "Alimentos", meals: "Comidas" } as const;
const entityTabIcons = { dailyplans: ClipboardList, foods: Carrot, meals: Utensils } as const;

export default function SavedComparisonDetailScreen() {
  const router = useRouter();
  const { id, kind: routeKind } = useLocalSearchParams<{ id: string; kind?: string }>();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [comparison, setComparison] = useState<SavedComparisonDetail | null>(null);
  const [entityItems, setEntityItems] = useState<LibraryItem[]>([]);
  const [entityLoading, setEntityLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<DetailTab>("cards");
  const [actionsVisible, setActionsVisible] = useState(false);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const saved = await apiRequest<SavedComparisonDetail>(`/api/v1/comparisons/saved/${id}`);
      setComparison(saved);
      setEntityLoading(true);
      const segment = saved.kind === "dailyplans" ? "daily-plans" : saved.kind;
      setEntityItems(await Promise.all(saved.items.map((item) => apiRequest<LibraryItem>(`/api/v1/library/${segment}/${item.id}`))));
    }
    catch (nextError) { setError(userFacingError(nextError)); }
    finally { setEntityLoading(false); setLoading(false); }
  }, [apiRequest, id]);
  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  const kind = comparison?.kind ?? (routeKind === "meals" || routeKind === "dailyplans" ? routeKind : "foods");
  const entity = kind === "dailyplans" ? "dailyPlan" : kind === "meals" ? "meal" : "food";
  const EntityTabIcon = entityTabIcons[kind];
  const comparisonId = comparison?.saved_comparison_id ?? null;
  const comparisonTitle = comparison?.saved_comparison_name ?? "Comparación guardada";
  const comparatorHref = useMemo(() => ({ pathname: "/comparator", params: { kind } } as Href), [kind]);
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ action: comparisonId != null ? { icon: "more", label: "Acciones de comparación", onPress: () => setActionsVisible(true) } : undefined, fallback: comparatorHref, identityVisible: compactHeaderVisible, mode: "back", title: comparisonTitle });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, comparisonId, comparisonTitle, comparatorHref, setHeaderPresentation]));
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !comparison) return <LoadingState label="Abriendo la comparación…" />;
  return (
    <Screen
      headerMode="preserve"
      onHeaderVisibilityChange={setCompactHeaderVisible}
      scrollHeader={<AppHeader eyebrow={comparison ? `Comparación ${entityTabLabels[comparison.kind]}` : "Comparación guardada"} eyebrowIcon={<EntityIcon entity={entity} size="compact" />} title={comparison?.saved_comparison_name ?? "Comparación"} />}
      stickyHeader={<View style={styles.tabsBleed}>
        <DistributedTabBar<DetailTab>
          accessibilityLabel="Vista de la comparación"
          activeTab={activeTab}
          onChange={setActiveTab}
          tabs={[
            { icon: (selected) => <LayoutGrid color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />, key: "cards", label: "Cards" },
            { icon: (selected) => <EntityTabIcon color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />, key: "entities", label: entityTabLabels[kind] },
          ]}
        />
      </View>}
      stickyHeaderStyle={styles.stickyTabs}>
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {comparison && activeTab === "cards" ? <ComparisonResultCards result={comparison} /> : null}
      {activeTab === "entities" && entityLoading ? <ActivityIndicator color={tokens.color.textMuted} /> : null}
      {activeTab === "entities" ? entityItems.map((item, index) => <LibraryCard apiRequest={apiRequest} interactive={false} item={item} key={`${item.entity}-${item.id}-${index}`} navigable onChanged={() => void load()} />) : null}
      {comparison ? <SavedComparisonActions
        name={comparison.saved_comparison_name}
        onClose={() => setActionsVisible(false)}
        onEdit={() => router.push({ pathname: "/comparator", params: { kind, savedId: String(comparison.saved_comparison_id) } } as Href)}
        onRename={async (name) => {
          const renamed = await apiRequest<SavedComparisonDetail>(`/api/v1/comparisons/saved/${comparison.saved_comparison_id}/name`, {
            body: JSON.stringify({ name }),
            headers: { "Content-Type": "application/json" },
            method: "PATCH",
          });
          setComparison(renamed);
        }}
        visible={actionsVisible}
      /> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  stickyTabs: { paddingTop: tokens.spacing.sm },
  tabsBleed: { alignSelf: "stretch", marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
});
