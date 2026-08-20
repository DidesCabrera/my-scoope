import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { LibraryItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { EntityDetailMetadata, EntityDetailPage, EntityDetailSection } from "@/components/details";
import { Button, InlineNotice, textStyles } from "@/components/ui/primitives";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { tokens } from "@/design/tokens";

import { DailyPlanMealCards, FoodPanels, MealPanels, ProgramPanels } from "./entity-panels";
import { libraryDate, libraryNutrition } from "./presentation-adapters";
import { ProgramDetailPreview } from "./program-detail-preview";

const sectionTitles = { foods: "Alimentos de esta comida", meals: "Comidas en este plan", weeks: "Semanas del programa" } as const;

export function LibraryDetailScreen({ entitySlug }: { entitySlug: "foods" | "meals" | "daily-plans" | "programs" }) {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { status, apiRequest } = useSession();
  const [item, setItem] = useState<LibraryItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const setHeaderPresentation = useHeaderPresentation();
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const headerEntity = entitySlug === "daily-plans" ? "dailyPlan" : entitySlug === "programs" ? "program" : entitySlug === "meals" ? "meal" : "food";
  const fallbackTitle = entitySlug === "daily-plans" ? "Plan diario" : entitySlug === "programs" ? "Programa" : entitySlug === "meals" ? "Comida" : "Alimento";
  useFocusEffect(useCallback(() => { setHeaderPresentation({ mode: "library-detail", entity: headerEntity, identityVisible: compactHeaderVisible, title: item?.name ?? fallbackTitle }); return () => setHeaderPresentation({ mode: "default" }); }, [compactHeaderVisible, fallbackTitle, headerEntity, item?.name, setHeaderPresentation]));
  const load = useCallback(async () => { setLoading(true); setError(null); try { setItem(await apiRequest<LibraryItem>(`/api/v1/library/${entitySlug}/${id}`)); } catch (nextError) { setError(userFacingError(nextError)); } finally { setLoading(false); } }, [apiRequest, entitySlug, id]);
  useFocusEffect(useCallback(() => { if (status === "authenticated" && id) void load(); }, [id, load, status]));
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !item) return <View style={styles.loading}><ActivityIndicator color={tokens.color.interactivePrimary} size="large" /><Text style={textStyles.muted}>Cargando detalle…</Text></View>;
  if (!item) return <View style={styles.loading}>{error ? <InlineNotice tone="error">{error}</InlineNotice> : null}<Button label="Reintentar" onPress={() => void load()} variant="secondary" /></View>;
  if (item.entity === "program") {
    return <ProgramDetailPreview
      footer={<>{item.can_calendarize ? <Button label="Calendarizar este programa" onPress={() => router.push(`/program/activate?programId=${item.id}` as Href)} /> : null}<EntityDetailMetadata creator={item.creator} updatedAt={libraryDate(item.created_at)} /></>}
      item={item}
      onScroll={({ nativeEvent }) => { const visible = nativeEvent.contentOffset.y > 1; if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible); }}
      scrollable
    />;
  }
  const panelCount = item.panel.kind === "foods" ? item.panel.foods.length : item.panel.kind === "meals" ? item.panel.meals.length : item.panel.kind === "weeks" ? item.panel.weeks.length : 0;
  return <ScrollView contentContainerStyle={styles.content} onScroll={({ nativeEvent }) => { const visible = nativeEvent.contentOffset.y > 1; if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible); }} scrollEventThrottle={16} style={styles.screen}><EntityDetailPage entity={item.entity} indicators={item.indicators} nutrition={libraryNutrition(item.nutrition)} subtitle={item.subtitle || undefined} title={item.name}>
    {item.panel.kind !== "none" ? <EntityDetailSection detail={`${panelCount} elementos`} title={sectionTitles[item.panel.kind]}>{item.panel.kind === "foods" ? <FoodPanels items={item.panel.foods} /> : null}{item.panel.kind === "meals" ? <MealPanels items={item.panel.meals} /> : null}{item.panel.kind === "weeks" ? <ProgramPanels items={item.panel.weeks} /> : null}</EntityDetailSection> : null}
    {item.entity === "dailyPlan" && item.panel.kind === "meals" && item.panel.meals.length > 0 ? <EntityDetailSection detail={`${item.panel.meals.length} comidas`} title="Detalle de cada Comida"><DailyPlanMealCards items={item.panel.meals} /></EntityDetailSection> : null}
    <EntityDetailMetadata creator={item.creator} updatedAt={libraryDate(item.created_at)} />
  </EntityDetailPage></ScrollView>;
}
const styles = StyleSheet.create({ screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 }, content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg }, loading: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, flex: 1, gap: tokens.spacing.md, justifyContent: "center", padding: tokens.spacing.screen } });
