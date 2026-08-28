import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Search } from "lucide-react-native";
import { useCallback, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { ComparisonKind, ComparisonOption, ComparisonOptionsData, LibraryEntity } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useComparatorSelectionTransfer } from "@/components/comparisons/comparator-selection-context";
import { FoodPanels, MealPanels } from "@/components/libraries/entity-panels";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { PickerCardAction } from "@/components/pickers/picker-card-action";
import { PickerEntryTabs } from "@/components/pickers/picker-entry-tabs";
import { NutritionEntityCard } from "@/components/nutrition";
import { LoadingState, textStyles } from "@/components/ui";
import { RecoverableErrorState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";

type SelectorConfig = {
  createEntity: LibraryEntity;
  createLabel: string;
  searchLabel: string;
  searchPlaceholder: string;
  title: string;
};

const selectorConfigs: Record<ComparisonKind, SelectorConfig> = {
  foods: { createEntity: "food", createLabel: "Crear alimento", searchLabel: "Buscar alimento", searchPlaceholder: "Escribe el nombre de un alimento", title: "Seleccionar alimento" },
  meals: { createEntity: "meal", createLabel: "Crear comida", searchLabel: "Buscar comida", searchPlaceholder: "Escribe el nombre de una comida", title: "Seleccionar comida" },
  dailyplans: { createEntity: "dailyPlan", createLabel: "Crear plan diario", searchLabel: "Buscar plan diario", searchPlaceholder: "Escribe el nombre de un plan diario", title: "Seleccionar plan" },
};

function builderHref(kind: ComparisonKind, savedId: number | null): Href {
  return savedId
    ? { pathname: "/comparator", params: { kind, savedId: String(savedId) } } as Href
    : { pathname: "/comparator", params: { create: "1", kind } } as Href;
}

export default function ComparatorSelectScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ kind?: string; savedId?: string; slotKey?: string }>();
  const kind: ComparisonKind = params.kind === "meals" || params.kind === "dailyplans" ? params.kind : "foods";
  const slotKey = Number(params.slotKey);
  const savedId = Number(params.savedId || 0) || null;
  const config = selectorConfigs[kind];
  const returnHref = builderHref(kind, savedId);
  const { status, apiRequest } = useSession();
  const { publishSelection } = useComparatorSelectionTransfer();
  const setHeaderPresentation = useHeaderPresentation();
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<ComparisonOption[]>([]);
  const [searching, setSearching] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: returnHref, mode: "back", title: config.title });
    return () => setHeaderPresentation({ mode: "default" });
  }, [config.title, returnHref, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated" || !Number.isInteger(slotKey) || slotKey <= 0) return;
    void retryNonce;
    let active = true;
    const timer = setTimeout(() => {
      setSearching(true);
      setError(null);
      const search = query.trim() ? `&search=${encodeURIComponent(query.trim())}` : "";
      void apiRequest<ComparisonOptionsData>(`/api/v1/comparisons/options/${kind}?limit=100${search}`)
        .then((page) => active && setOptions(page.items))
        .catch((nextError) => active && setError(userFacingError(nextError)))
        .finally(() => active && setSearching(false));
    }, 220);
    return () => { active = false; clearTimeout(timer); };
  }, [apiRequest, kind, query, retryNonce, slotKey, status]));

  function select(option: ComparisonOption) {
    publishSelection({ kind, option, slotKey });
    if (router.canGoBack()) router.back();
    else router.replace(returnHref);
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (!Number.isInteger(slotKey) || slotKey <= 0) return <Redirect href={returnHref} />;
  if (searching && !options.length && !query) return <LoadingState label="Preparando el selector…" />;

  return (
    <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardDismissMode="on-drag"
        keyboardShouldPersistTaps="handled"
        stickyHeaderIndices={[0]}>
        <View style={styles.stickyHeader}>
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
            <NutritionEntityCard
              actions={<PickerCardAction label="Seleccionar" onPress={() => select(option)} subject={option.name} />}
              entity={option.entity}
              indicators={option.indicators}
              key={option.id}
              nutrition={libraryNutrition(option.nutrition)}
              subtitle={option.subtitle || undefined}
              title={option.name}>
              {option.panel.kind === "foods" ? <FoodPanels items={option.panel.foods} /> : null}
              {option.panel.kind === "meals" ? <MealPanels items={option.panel.meals} /> : null}
            </NutritionEntityCard>
          ))}
          {!searching && !options.length && !error ? <Text style={textStyles.muted}>No encontramos resultados.</Text> : null}
          {error ? <RecoverableErrorState message={error} onRetry={() => setRetryNonce((value) => value + 1)} /> : null}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  options: { gap: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen },
  safeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  scrollContent: { flexGrow: 1, paddingBottom: 42 },
  searchField: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, marginHorizontal: tokens.spacing.screen, minHeight: 38, paddingHorizontal: tokens.spacing.md },
  searchInput: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, minHeight: 36, paddingVertical: 0 },
  stickyHeader: { backgroundColor: tokens.color.surfaceApp, gap: tokens.spacing.xs, paddingBottom: tokens.spacing.lg, zIndex: 2 },
});
