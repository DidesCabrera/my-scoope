import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Pill, PillBottle } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Alert, type NativeScrollEvent, type NativeSyntheticEvent, ScrollView, StyleSheet, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { EntitlementsData, Supplement, SupplementIntakePreset } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { isHeaderIdentityVisible } from "@/components/navigation/header-scroll";
import { SupplementProSheet } from "@/components/supplements/supplement-pro-sheet";
import { SupplementActionsSheet } from "@/components/supplements/supplement-actions-sheet";
import { SupplementIntakePresetCard } from "@/components/supplements/supplement-intake-preset-card";
import {
  Button,
  Card,
  CollectionEmptyState,
  CollectionPageHeader,
  DistributedTabBar,
  InlineNotice,
  LoadingState,
  SearchField,
  SupplementCard,
} from "@/components/ui";
import { tokens } from "@/design/tokens";

function SupplementLibraryCard({ item, onMore, onOpen }: { item: Supplement; onMore(): void; onOpen(): void }) {
  return <SupplementCard brand={item.brand} componentCount={item.components.length} name={item.name} onMore={onMore} onOpen={onOpen} quantity={item.default_quantity} unit={item.default_unit} />;
}

type LibraryTab = "supplements" | "intakes";

export default function SupplementsLibraryScreen() {
  const { tab } = useLocalSearchParams<{ tab?: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [items, setItems] = useState<Supplement[]>([]);
  const [presets, setPresets] = useState<SupplementIntakePreset[]>([]);
  const [activeTab, setActiveTab] = useState<LibraryTab>(tab === "intakes" ? "intakes" : "supplements");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [pro, setPro] = useState(false);
  const [available, setAvailable] = useState(false);
  const [upsell, setUpsell] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSupplement, setSelectedSupplement] = useState<Supplement | null>(null);
  const [supplementActionsVisible, setSupplementActionsVisible] = useState(false);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);

  const openCreateSupplement = useCallback(() => router.push("/libraries/supplements/new" as Href), [router]);
  const openCreatePreset = useCallback(() => router.push("/libraries/supplements/intakes/new" as Href), [router]);
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const entitlements = await apiRequest<EntitlementsData>("/api/v1/entitlements", { cache: "no-store" });
      const allowed = Boolean(entitlements.workspace_features?.can_use_supplements);
      setAvailable(Boolean(entitlements.workspace_features?.supplements_available));
      setPro(allowed);
      if (allowed) {
        const [supplementsPage, presetsPage] = await Promise.all([
          apiRequest<{ items: Supplement[] }>("/api/v1/library/supplements"),
          apiRequest<{ items: SupplementIntakePreset[] }>("/api/v1/library/supplement-intake-presets"),
        ]);
        setItems(supplementsPage.items);
        setPresets(presetsPage.items);
      } else {
        setItems([]);
        setPresets([]);
      }
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));
  useFocusEffect(useCallback(() => { if (tab === "intakes") setActiveTab("intakes"); }, [tab]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      secondaryAction: available && pro && activeTab === "supplements" ? { icon: "search", label: "Explorar suplementos", onPress: () => router.push("/explore/supplements" as Href) } : undefined,
      createAction: available && pro ? {
        label: activeTab === "supplements" ? "Crear suplemento" : "Crear ingesta",
        onPress: activeTab === "supplements" ? openCreateSupplement : openCreatePreset,
      } : undefined,
      identityVisible: compactHeaderVisible,
      mode: "default",
      title: "Mis Suplementos",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [activeTab, available, compactHeaderVisible, openCreatePreset, openCreateSupplement, pro, router, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !items.length) return <LoadingState label="Cargando tu librería…" />;

  const normalizedQuery = query.trim().toLocaleLowerCase("es");
  const visible = items.filter((item) => `${item.name} ${item.brand}`.toLocaleLowerCase("es").includes(normalizedQuery));
  const visiblePresets = presets.filter((item) => `${item.name} ${item.items.map((row) => row.supplement.name ?? "").join(" ")}`.toLocaleLowerCase("es").includes(normalizedQuery));
  const handleScroll = ({ nativeEvent }: NativeSyntheticEvent<NativeScrollEvent>) => setCompactHeaderVisible(isHeaderIdentityVisible(nativeEvent.contentOffset.y));
  const removeSupplement = () => {
    if (!selectedSupplement) return;
    const selectedId = selectedSupplement.id;
    setSupplementActionsVisible(false);
    Alert.alert("Eliminar suplemento", "Se quitará de tu biblioteca. Las ingestas guardadas conservarán su descripción.", [
      { text: "Cancelar", style: "cancel" },
      { text: "Eliminar", style: "destructive", onPress: () => { void apiRequest(`/api/v1/library/supplements/${selectedId}`, { method: "DELETE" }).then(() => { setItems((current) => current.filter((item) => item.id !== selectedId)); setSelectedSupplement(null); }).catch((nextError) => setError(userFacingError(nextError))); } },
    ]);
  };

  return <>
    <ScrollView
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      onScroll={handleScroll}
      scrollEventThrottle={16}
      showsVerticalScrollIndicator={false}
      stickyHeaderIndices={available && pro ? [1] : undefined}
      style={styles.screen}>
      <CollectionPageHeader
        count={available && pro ? activeTab === "supplements" ? items.length : presets.length : undefined}
        countLabels={activeTab === "supplements"
          ? { plural: "Suplementos", singular: "Suplemento" }
          : { plural: "Ingestas", singular: "Ingesta" }}
        entity="supplement"
        title="Mis Suplementos"
      />
      {available && pro ? <View style={styles.stickySearch}>
        <DistributedTabBar<LibraryTab>
          accessibilityLabel="Contenido de Mis Suplementos"
          activeTab={activeTab}
          onChange={(tab) => { setActiveTab(tab); setQuery(""); }}
          tabs={[
            { count: items.length, icon: (selected) => <Pill color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={16} />, key: "supplements", label: "Suplementos" },
            { count: presets.length, icon: (selected) => <PillBottle color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={16} />, key: "intakes", label: "Ingestas" },
          ]}
        />
        <View style={styles.searchSpacer} />
        <SearchField
          accessibilityLabel={activeTab === "supplements" ? "Buscar suplementos" : "Buscar ingestas"}
          autoCapitalize="none"
          autoCorrect={false}
          onChangeText={setQuery}
          onClear={() => setQuery("")}
          placeholder={activeTab === "supplements" ? "Buscar por nombre o marca" : "Buscar ingesta"}
          returnKeyType="search"
          value={query}
        />
      </View> : null}
      {error ? <Card><InlineNotice tone="error">{error}</InlineNotice><Button label="Reintentar" onPress={() => void load()} variant="secondary" /></Card> : null}
      {!available ? <Card><InlineNotice tone="info">La biblioteca de suplementos aún no está disponible.</InlineNotice></Card> : null}
      {available && !pro ? <Card><InlineNotice tone="info">Suplementos está disponible con el plan Pro.</InlineNotice><Button label="Conocer Suplementos Pro" onPress={() => setUpsell(true)} variant="primary" /></Card> : null}
      {available && pro && activeTab === "supplements" && !visible.length ? <CollectionEmptyState description={normalizedQuery ? "Prueba con otra búsqueda." : "Los suplementos que uses habitualmente aparecerán aquí."} title={normalizedQuery ? "Sin resultados" : "Aún no tienes suplementos"} /> : null}
      {available && pro && activeTab === "intakes" && !visiblePresets.length ? <CollectionEmptyState description={normalizedQuery ? "Prueba con otra búsqueda." : "Crea una ingesta para reutilizar la misma combinación en distintas minutas."} title={normalizedQuery ? "Sin resultados" : "Aún no tienes ingestas"} /> : null}
      {available && pro && activeTab === "supplements" ? visible.map((item) => <SupplementLibraryCard item={item} key={item.id} onMore={() => { setSelectedSupplement(item); setSupplementActionsVisible(true); }} onOpen={() => router.push(`/libraries/supplements/${item.id}` as Href)} />) : null}
      {available && pro && activeTab === "intakes" ? visiblePresets.map((item) => <SupplementIntakePresetCard item={item} key={item.id} onOpen={() => router.push(`/libraries/supplements/intakes/${item.id}` as Href)} />) : null}
    </ScrollView>
    {selectedSupplement ? <SupplementActionsSheet name={selectedSupplement.name} onClose={() => setSupplementActionsVisible(false)} onDelete={removeSupplement} onEdit={() => {
      setSupplementActionsVisible(false);
      router.push(`/libraries/supplements/${selectedSupplement.id}/edit` as Href);
    }} visible={supplementActionsVisible} /> : null}
    <SupplementProSheet onClose={() => setUpsell(false)} visible={upsell} />
  </>;
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, gap: tokens.spacing.lg, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  searchSpacer: { height: 12 },
  stickySearch: { backgroundColor: tokens.color.surfaceApp, marginHorizontal: -tokens.spacing.screen, marginTop: -8, paddingBottom: tokens.spacing.sm, paddingHorizontal: tokens.layout.reducedInset, paddingTop: tokens.spacing.xs, zIndex: 3 },
});
