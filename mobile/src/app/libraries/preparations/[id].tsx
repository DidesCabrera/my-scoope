import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Carrot } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Alert, StyleSheet, Text, View } from "react-native";
import { NestableScrollContainer } from "react-native-draggable-flatlist";

import { userFacingError } from "@/api/errors";
import type { PreparationDetail } from "@/api/preparations";
import { useSession } from "@/auth/session-context";
import { EntityDetailPage, EntityDetailSection, FoodDetailCardList } from "@/components/details";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { FoodPanels, type FoodPanelItem } from "@/components/panels";
import { preparationStateLabel, formatPreparationAllergens, formatPreparationNumber } from "@/components/preparations/preparation-ingredients-card";
import { ingredientPanelItem } from "@/components/preparations/preparation-panel-items";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";
import { Button, LoadingState } from "@/components/ui";
import { InlineNotice } from "@/components/ui/primitives";
import { Card } from "@/components/ui/surfaces";
import { tokens } from "@/design/tokens";

function percentage(value: number, total: number): number {
  return total > 0 ? (value / total) * 100 : 0;
}

export default function PreparationDetailScreen() {
  const { id, mealId, relationId, units, grams } = useLocalSearchParams<{
    id: string; mealId?: string; relationId?: string; units?: string; grams?: string;
  }>();
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [detail, setDetail] = useState<PreparationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const validId = Number.isInteger(Number(id)) && Number(id) > 0;
  const meal = Number(mealId);
  const relation = Number(relationId);
  const inMeal = Number.isInteger(meal) && meal > 0 && Number.isInteger(relation) && relation > 0;

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ mode: "back", fallback: inMeal ? `/libraries/meals/${meal}` as Href : detail?.is_personal ? "/libraries/preparations" : "/libraries/meals", title: detail?.name ?? "Preparación" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [detail?.is_personal, detail?.name, inMeal, meal, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated" || !validId) return undefined;
    let active = true;
    setLoading(true);
    setError(null);
    const portion = units && Number(units) > 0 ? `?units=${encodeURIComponent(units)}` : grams && Number(grams) > 0 ? `?grams=${encodeURIComponent(grams)}` : "";
    void apiRequest<PreparationDetail>(`/api/v1/preparations/${id}${portion}`)
      .then((result) => { if (active) setDetail(result); })
      .catch((failure) => { if (active) setError(userFacingError(failure)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, grams, id, status, units, validId]));

  if (!validId) return <Redirect href="/libraries/meals" />;
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Cargando preparación" />;
  if (!detail) return <View style={styles.feedback}><InlineNotice tone="error">{error ?? "No encontramos esta preparación."}</InlineNotice></View>;

  const ingredients = detail.ingredients.map((ingredient, index) => ingredientPanelItem(ingredient, index, detail));
  const portion = detail.selection_mode === "units"
    ? `${formatPreparationNumber(detail.selected_units ?? 1)} ${detail.household_label}`
    : `${formatPreparationNumber(detail.grams)} g`;
  const nutrition = {
    // Meal components are displayed at one decimal before the KPI rounds to kcal.
    calories: Math.round(detail.nutrition.calories * 10) / 10,
    protein: { grams: detail.nutrition.protein_g, allocation: percentage(detail.nutrition.protein_g * 4, detail.nutrition.calories) },
    carbs: { grams: detail.nutrition.carbs_g, allocation: percentage(detail.nutrition.carbs_g * 4, detail.nutrition.calories) },
    fat: { grams: detail.nutrition.fat_g, allocation: percentage(detail.nutrition.fat_g * 9, detail.nutrition.calories) },
  };
  const openIngredient = (ingredient: FoodPanelItem) => {
    if (ingredient.detailId != null) router.push((ingredient.kind === "preparation" ? `/libraries/preparations/${ingredient.detailId}` : `/libraries/foods/${ingredient.detailId}`) as Href);
  };
  const remove = () => Alert.alert("Quitar preparación", `¿Quitar ${detail.name} de esta comida?`, [
    { text: "Cancelar", style: "cancel" },
    { text: "Quitar", style: "destructive", onPress: () => {
      void apiRequest(`/api/v1/library/meals/${meal}/preparations/${relation}`, { method: "DELETE" })
        .then(() => router.dismissTo(`/libraries/meals/${meal}` as Href))
        .catch((failure) => Alert.alert("No pudimos quitarla", userFacingError(failure)));
    } },
  ]);
  const removePersonal = () => Alert.alert("Eliminar preparación", `¿Eliminar ${detail.name} de tu biblioteca? Las comidas existentes conservarán su composición.`, [
    { text: "Cancelar", style: "cancel" },
    { text: "Eliminar", style: "destructive", onPress: () => {
      void apiRequest(`/api/v1/library/preparations/${detail.id}`, { method: "DELETE" })
        .then(() => router.replace("/libraries/preparations" as Href))
        .catch((failure) => Alert.alert("No pudimos eliminarla", userFacingError(failure)));
    } },
  ]);

  return <NestableScrollContainer contentContainerStyle={styles.content} showsVerticalScrollIndicator={false} style={styles.screen}>
    <EntityDetailPage entity="preparation" nutrition={nutrition} subtitle={portion} title={detail.name}>
      <EntityDetailSection detail={`${ingredients.length} ${ingredients.length === 1 ? "ingrediente" : "ingredientes"}`} title="Composición de la preparación">
        <FoodPanels items={ingredients} nestedScroll onOpenItem={openIngredient} />
      </EntityDetailSection>
      {ingredients.length > 0 ? <>
        <ProgramSectionHeader icon={Carrot} subtitle="Compara el aporte de cada ingrediente y abre su ficha de alimento." title="Detalle de cada ingrediente" />
        <FoodDetailCardList items={ingredients} onOpenFood={openIngredient} />
      </> : null}
      <Card muted>
        <Text style={styles.infoTitle}>Información de la preparación</Text>
        <View style={styles.infoRow}><Text style={styles.infoLabel}>Porción</Text><Text style={styles.infoValue}>{portion} · {formatPreparationNumber(detail.grams)} g</Text></View>
        <View style={styles.infoRow}><Text style={styles.infoLabel}>Sodio</Text><Text style={styles.infoValue}>{detail.nutrition.sodium_mg == null ? "Sin dato" : `${formatPreparationNumber(detail.nutrition.sodium_mg, 0)} mg`}</Text></View>
        <View style={styles.infoRow}><Text style={styles.infoLabel}>Alérgenos</Text><Text style={styles.infoValue}>{detail.allergen_status === "unknown" ? "Sin evaluación" : formatPreparationAllergens(detail.allergens)}</Text></View>
        <View style={styles.infoRow}><Text style={styles.infoLabel}>Estados</Text><Text style={styles.infoValue}>{[...new Set(detail.ingredients.filter((ingredient) => "preparation_state" in ingredient).map((ingredient) => preparationStateLabel(ingredient.preparation_state)))].join(", ") || "Sin datos declarados"}</Text></View>
        <Text style={styles.source}>{detail.is_personal ? "Estimación personal" : "Estimación editorial"} · versión {detail.version}{detail.evidence.source_name ? ` · ${detail.evidence.source_name}` : ""}</Text>
      </Card>
      {detail.is_personal && detail.is_active ? <View style={styles.actions}>
        <Button label="Editar preparación" onPress={() => router.push(`/libraries/preparations/${detail.id}/edit` as Href)} variant="secondary" />
        <Button label="Eliminar preparación" onPress={removePersonal} variant="danger" />
      </View> : null}
      {inMeal ? <View style={styles.actions}>
        {detail.is_active ? <Button label="Editar porción en esta comida" onPress={() => router.push(`/pickers/preparation-to-meal?mealId=${meal}&relationId=${relation}&preparationId=${detail.id}` as Href)} variant="secondary" /> : null}
        <Button label="Quitar de esta comida" onPress={remove} variant="danger" />
      </View> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    </EntityDetailPage>
  </NestableScrollContainer>;
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  content: { paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg, paddingBottom: 48 },
  feedback: { padding: tokens.spacing.screen },
  infoTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.bold },
  infoRow: { flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  infoLabel: { color: tokens.color.textMuted, flex: 1, fontSize: tokens.type.caption },
  infoValue: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, textAlign: "right" },
  source: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 18 },
  actions: { gap: tokens.spacing.sm },
});
