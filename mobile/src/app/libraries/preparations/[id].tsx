import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Carrot } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Alert, StyleSheet, View } from "react-native";
import { NestableScrollContainer } from "react-native-draggable-flatlist";

import { userFacingError } from "@/api/errors";
import type { PersonalPreparation } from "@/api/preparations";
import { useSession } from "@/auth/session-context";
import { EntityDetailPage, EntityDetailSection, FoodDetailCardList } from "@/components/details";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { isHeaderIdentityVisible } from "@/components/navigation/header-scroll";
import { FoodPanels, type FoodPanelItem } from "@/components/panels";
import { formatPreparationNumber } from "@/components/preparations/preparation-ingredients-card";
import { PreparationDetailActions } from "@/components/preparations/preparation-detail-actions";
import { ingredientPanelItem } from "@/components/preparations/preparation-panel-items";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";
import { Button, LoadingState } from "@/components/ui";
import { InlineNotice } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";
import { pickerHref } from "@/components/pickers/picker-routes";

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
  const [detail, setDetail] = useState<PersonalPreparation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [actionsVisible, setActionsVisible] = useState(false);
  const validId = Number.isInteger(Number(id)) && Number(id) > 0;
  const meal = Number(mealId);
  const relation = Number(relationId);
  const inMeal = Number.isInteger(meal) && meal > 0 && Number.isInteger(relation) && relation > 0;

  const openActions = useCallback(() => setActionsVisible(true), []);
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      mode: "library-detail",
      action: detail ? { label: `Más acciones para ${detail.name}`, onPress: openActions } : undefined,
      entity: "preparation",
      fallback: inMeal ? `/libraries/meals/${meal}` as Href : "/libraries/preparations",
      identityVisible: compactHeaderVisible,
      title: detail?.name ?? "Preparación",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, detail, inMeal, meal, openActions, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated" || !validId) return undefined;
    let active = true;
    setLoading(true);
    setError(null);
    const portion = units && Number(units) > 0 ? `?units=${encodeURIComponent(units)}` : grams && Number(grams) > 0 ? `?grams=${encodeURIComponent(grams)}` : "";
    void apiRequest<PersonalPreparation>(`/api/v1/preparations/${id}${portion}`)
      .then((result) => { if (active) setDetail(result); })
      .catch((failure) => { if (active) setError(userFacingError(failure)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, grams, id, status, units, validId]));

  if (!validId) return <Redirect href="/libraries/meals" />;
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Cargando preparación" />;
  if (!detail) return <View style={styles.feedback}><InlineNotice tone="error">{error ?? "No encontramos esta preparación."}</InlineNotice></View>;
  const addFood = () => router.push(pickerHref("food-to-preparation", { preparationId: detail.id, returnTo: `/libraries/preparations/${detail.id}` }));
  const openInformation = () => router.push({ pathname: "/libraries/preparations/[id]/information", params: {
    id: String(detail.id), ...(units ? { units } : {}), ...(grams ? { grams } : {}),
  } } as Href);
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
  const actions = <PreparationDetailActions
    inMeal={inMeal}
    isActive={detail.is_active}
    isPersonal={detail.is_personal}
    name={detail.name}
    onClose={() => setActionsVisible(false)}
    onEdit={() => router.push(`/libraries/preparations/${detail.id}/edit` as Href)}
    onEditMealPortion={() => router.push(`/pickers/preparation-to-meal?mealId=${meal}&relationId=${relation}&preparationId=${detail.id}` as Href)}
    onOpenInformation={openInformation}
    onRemoveFromMeal={remove}
    onRemovePersonal={removePersonal}
    visible={actionsVisible}
  />;

  if (detail.is_draft) return <>
    <NestableScrollContainer contentContainerStyle={styles.content} onScroll={({ nativeEvent }) => setCompactHeaderVisible(isHeaderIdentityVisible(nativeEvent.contentOffset.y))} scrollEventThrottle={16} showsVerticalScrollIndicator={false} style={styles.screen}>
      <EntityDetailPage entity="preparation" showNutrition={false} title={detail.name}>
        <InlineNotice tone="info">Agrega los alimentos de la receta para calcular su información nutricional.</InlineNotice>
        <Button label="+ Agregar alimento" onPress={addFood} variant="chipPrimary" />
      </EntityDetailPage>
    </NestableScrollContainer>
    {actions}
  </>;

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

  return <><NestableScrollContainer contentContainerStyle={styles.content} onScroll={({ nativeEvent }) => setCompactHeaderVisible(isHeaderIdentityVisible(nativeEvent.contentOffset.y))} scrollEventThrottle={16} showsVerticalScrollIndicator={false} style={styles.screen}>
    <EntityDetailPage entity="preparation" indicators={[{ icon: "food", label: ingredients.length === 1 ? "ingrediente" : "ingredientes", value: ingredients.length }]} nutrition={nutrition} subtitle={portion} title={detail.name}>
      <EntityDetailSection title="Composición de la preparación">
        <FoodPanels items={ingredients} nestedScroll onOpenItem={openIngredient} />
      </EntityDetailSection>
      {detail.is_personal && detail.is_active ? <Button label="+ Agregar alimento" onPress={addFood} variant="chipPrimary" /> : null}
      {ingredients.length > 0 ? <>
        <ProgramSectionHeader icon={Carrot} subtitle="Compara el aporte de cada ingrediente y abre su ficha de alimento." title="Detalle de cada ingrediente" />
        <FoodDetailCardList items={ingredients} onOpenFood={openIngredient} />
      </> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    </EntityDetailPage>
  </NestableScrollContainer>{actions}</>;
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  content: { flexGrow: 1, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg, paddingBottom: 42 },
  feedback: { padding: tokens.spacing.screen },
});
