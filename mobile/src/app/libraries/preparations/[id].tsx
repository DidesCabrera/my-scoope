import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Carrot } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
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
  const [portionDetail, setPortionDetail] = useState<PersonalPreparation | null>(null);
  const [kpiView, setKpiView] = useState<"recipe" | "portion">("recipe");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [actionsVisible, setActionsVisible] = useState(false);
  const validId = Number.isInteger(Number(id)) && Number(id) > 0;
  const meal = Number(mealId);
  const relation = Number(relationId);
  const inMeal = Number.isInteger(meal) && meal > 0 && Number.isInteger(relation) && relation > 0;

  const openActions = useCallback(() => setActionsVisible(true), []);
  const loadDetails = useCallback(async () => {
    const [recipe, portion] = await Promise.all([
      apiRequest<PersonalPreparation>(`/api/v1/preparations/${id}?full_recipe=true`, { cache: "no-store" }),
      apiRequest<PersonalPreparation>(`/api/v1/preparations/${id}`, { cache: "no-store" }),
    ]);
    setDetail(recipe);
    setPortionDetail(portion);
  }, [apiRequest, id]);
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
    void Promise.all([
      apiRequest<PersonalPreparation>(`/api/v1/preparations/${id}?full_recipe=true`, { cache: "no-store" }),
      apiRequest<PersonalPreparation>(`/api/v1/preparations/${id}`, { cache: "no-store" }),
    ])
      .then(([recipe, portion]) => { if (active) { setDetail(recipe); setPortionDetail(portion); } })
      .catch((failure) => { if (active) setError(userFacingError(failure)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, id, status, validId]));

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
  const saveMetadata = async (name: string, options?: { manualYield: boolean; yieldG: number; portionG: number }) => {
    if (detail.is_draft) {
      const updated = await apiRequest<PersonalPreparation>(`/api/v1/library/preparations/${detail.id}/draft`, {
        method: "PATCH", body: JSON.stringify({ name }),
      });
      setDetail(updated);
      setPortionDetail(updated);
      return;
    }
    await apiRequest<PersonalPreparation>(`/api/v1/library/preparations/${detail.id}`, {
      method: "PUT",
      body: JSON.stringify({
        name,
        ...((options?.manualYield ?? detail.yield_is_manual) ? { yield_g: options?.yieldG ?? detail.yield_g } : {}),
        default_portion_g: options?.portionG ?? detail.default_portion_g,
        ingredients: detail.recipe_ingredients.map(({ food_id, quantity_g }) => ({ food_id, quantity_g })),
      }),
    });
    await loadDetails();
  };
  const actions = <PreparationDetailActions
    advanced={!detail.is_draft ? {
      estimatedYieldG: detail.recipe_ingredients.reduce((sum, row) => sum + row.quantity_g, 0),
      manualYield: Boolean(detail.yield_is_manual),
      yieldG: detail.yield_g,
      portionG: detail.default_portion_g,
    } : undefined}
    inMeal={inMeal}
    isActive={detail.is_active}
    isPersonal={detail.is_personal}
    name={detail.name}
    onClose={() => setActionsVisible(false)}
    onEditMealPortion={() => router.push(`/pickers/preparation-to-meal?mealId=${meal}&relationId=${relation}&preparationId=${detail.id}` as Href)}
    onOpenInformation={openInformation}
    onRemoveFromMeal={remove}
    onRemovePersonal={removePersonal}
    onRename={(name) => saveMetadata(name)}
    onSaveAdvanced={(options) => saveMetadata(detail.name, options)}
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
  const portionCount = detail.yield_g / detail.default_portion_g;
  const subtitle = `Rinde ${formatPreparationNumber(detail.yield_g, 2)} g · ${formatPreparationNumber(portionCount, 2)} ${portionCount === 1 ? "porción" : "porciones"} de ${formatPreparationNumber(detail.default_portion_g, 2)} g`;
  const displayedDetail = kpiView === "portion" && portionDetail && !portionDetail.is_draft ? portionDetail : detail;
  const displayedNutrition = displayedDetail.nutrition;
  const nutrition = {
    // Meal components are displayed at one decimal before the KPI rounds to kcal.
    calories: Math.round(displayedNutrition.calories * 10) / 10,
    protein: { grams: displayedNutrition.protein_g, allocation: percentage(displayedNutrition.protein_g * 4, displayedNutrition.calories), perKilogram: displayedNutrition.protein_per_kilogram },
    carbs: { grams: displayedNutrition.carbs_g, allocation: percentage(displayedNutrition.carbs_g * 4, displayedNutrition.calories) },
    fat: { grams: displayedNutrition.fat_g, allocation: percentage(displayedNutrition.fat_g * 9, displayedNutrition.calories) },
  };
  const openIngredient = (ingredient: FoodPanelItem) => {
    if (ingredient.detailId != null) router.push((ingredient.kind === "preparation" ? `/libraries/preparations/${ingredient.detailId}` : `/libraries/foods/${ingredient.detailId}`) as Href);
  };
  const editable = detail.is_personal && detail.is_active;
  const saveIngredients = async (next: { food_id: number; quantity_g: number }[]) => {
    try {
      if (!next.length) {
        const draft = await apiRequest<PersonalPreparation>(`/api/v1/library/preparations/${detail.id}/foods`, { method: "DELETE" });
        setDetail(draft);
        setPortionDetail(draft);
        setError(null);
        return;
      }
      await apiRequest<PersonalPreparation>(`/api/v1/library/preparations/${detail.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: detail.name,
          ...(detail.yield_is_manual ? { yield_g: detail.yield_g } : {}),
          default_portion_g: detail.default_portion_g,
          ingredients: next,
        }),
      });
      await loadDetails();
      setError(null);
    } catch (failure) {
      setError(userFacingError(failure));
      throw failure;
    }
  };
  const editing = editable ? {
    onDelete: async (food: FoodPanelItem) => {
      await saveIngredients(detail.recipe_ingredients.filter((row) => row.food_id !== food.detailId));
    },
    onEditPortion: (food: FoodPanelItem) => {
      if (food.detailId == null) return;
      Alert.prompt("Editar cantidad", `Cantidad de ${food.name} en la receta (g)`, [
        { text: "Cancelar", style: "cancel" },
        { text: "Guardar", onPress: (value?: string) => {
          const quantity = Number(String(value ?? "").trim().replace(",", "."));
          if (!Number.isFinite(quantity) || quantity <= 0) { Alert.alert("Cantidad inválida", "Ingresa una cantidad mayor que cero."); return; }
          void saveIngredients(detail.recipe_ingredients.map((row) => row.food_id === food.detailId ? { food_id: row.food_id, quantity_g: quantity } : row)).catch(() => undefined);
        } },
      ], "plain-text", String(food.quantity), "decimal-pad");
    },
    onReorder: async (foods: FoodPanelItem[]) => {
      await saveIngredients(foods.map((food) => ({ food_id: Number(food.detailId), quantity_g: food.quantity })));
    },
    onReplace: (food: FoodPanelItem) => {
      if (food.detailId != null) router.push(pickerHref("food-to-preparation", { preparationId: detail.id, replaceFoodId: food.detailId, returnTo: `/libraries/preparations/${detail.id}` }));
    },
  } : undefined;

  return <><NestableScrollContainer contentContainerStyle={styles.content} onScroll={({ nativeEvent }) => setCompactHeaderVisible(isHeaderIdentityVisible(nativeEvent.contentOffset.y))} scrollEventThrottle={16} showsVerticalScrollIndicator={false} style={styles.screen}>
    <EntityDetailPage beforeNutrition={<View style={styles.kpiViewSelector}>
      <Text style={styles.kpiViewTitle}>Información nutricional</Text>
      <Pressable accessibilityRole="button" hitSlop={8} onPress={() => setKpiView((current) => current === "recipe" ? "portion" : "recipe")} style={({ pressed }) => [styles.kpiViewAction, pressed && styles.kpiViewActionPressed]}>
        <Text style={styles.kpiViewActionText}>{kpiView === "recipe" ? "Ver por porción" : "Ver por receta"}</Text>
      </Pressable>
    </View>} entity="preparation" indicators={[{ icon: "food", label: ingredients.length === 1 ? "ingrediente" : "ingredientes", value: ingredients.length }]} nutrition={nutrition} subtitle={subtitle} title={detail.name}>
      <EntityDetailSection title="Composición de la preparación">
        <FoodPanels editing={editing} items={ingredients} nestedScroll onOpenItem={openIngredient} ownerLabel="esta preparación" />
      </EntityDetailSection>
      {detail.is_personal && detail.is_active ? <Button label="+ Agregar alimento" onPress={addFood} variant="chipPrimary" /> : null}
      {ingredients.length > 0 ? <>
        <ProgramSectionHeader icon={Carrot} subtitle="Compara el aporte de cada ingrediente y abre su ficha de alimento." title="Detalle de cada ingrediente" />
        <FoodDetailCardList editing={() => editing} items={ingredients} onOpenFood={openIngredient} ownerLabel="esta preparación" />
      </> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    </EntityDetailPage>
  </NestableScrollContainer>{actions}</>;
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  content: { flexGrow: 1, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg, paddingBottom: 42 },
  feedback: { padding: tokens.spacing.screen },
  kpiViewSelector: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginTop: tokens.spacing.sm },
  kpiViewTitle: { color: tokens.color.textMuted, flexShrink: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  kpiViewAction: { alignItems: "center", justifyContent: "center", minHeight: 38, paddingLeft: tokens.spacing.sm },
  kpiViewActionPressed: { opacity: 0.65 },
  kpiViewActionText: { color: tokens.color.interactivePrimary, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
});
