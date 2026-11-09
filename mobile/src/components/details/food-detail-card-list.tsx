import { useEffect, useState } from "react";
import { ChevronRight, Pencil, RefreshCw, Trash2 } from "lucide-react-native";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import type { PreparationDetail } from "@/api/preparations";
import { useSession } from "@/auth/session-context";
import { NutritionEntityCard } from "@/components/nutrition";
import { ContextCardActions, type ContextCardAction } from "@/components/libraries/context-card-actions";
import { FoodPanels } from "@/components/panels";
import { PickerFoodNutritionPanel } from "@/components/pickers/picker-food-nutrition-panel";
import { ingredientPanelItem } from "@/components/preparations/preparation-panel-items";
import { EntityCardAction, InlineNotice } from "@/components/ui";
import { tokens } from "@/design/tokens";
import type { FoodPanelEditing, FoodPanelItem } from "@/components/panels";

function macroShare(grams: number, factor: number, calories: number): number {
  return calories > 0 ? (grams * factor * 100) / calories : 0;
}

function PreparationComponentPanel({ item, onOpenFood }: { item: FoodPanelItem; onOpenFood?: (item: FoodPanelItem) => void }) {
  const { apiRequest } = useSession();
  const [detail, setDetail] = useState<PreparationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const preparationId = item.detailId;
  const portion = item.quantityUnit === "g" ? `grams=${item.quantity}` : `units=${item.quantity}`;

  useEffect(() => {
    if (preparationId == null) return;
    let active = true;
    void apiRequest<PreparationDetail>(`/api/v1/preparations/${preparationId}?${portion}`)
      .then((result) => { if (active) setDetail(result); })
      .catch(() => { if (active) setFailed(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, portion, preparationId]);

  return <View style={styles.panelContent}>
    {loading ? <ActivityIndicator accessibilityLabel="Cargando ingredientes" color={tokens.color.preparation} size="small" /> : null}
    {failed ? <InlineNotice tone="warning">No pudimos cargar los ingredientes de esta preparación.</InlineNotice> : null}
    {detail ? <FoodPanels items={detail.ingredients.map((ingredient, index) => ingredientPanelItem(ingredient, index, detail))} onOpenItem={onOpenFood} showEditTab={false} /> : null}
  </View>;
}

export function FoodDetailCardList({ editing, items, onOpenFood }: { editing?(item: FoodPanelItem): Pick<FoodPanelEditing, "onDelete" | "onEditPortion" | "onReplace"> | null | undefined; items: FoodPanelItem[]; onOpenFood?(item: FoodPanelItem): void }) {
  return (
    <View style={styles.list}>
      {items.map((item) => {
        const calculatedCalories = item.proteinGrams * 4 + item.carbsGrams * 4 + item.fatGrams * 9;
        const calories = item.calories || calculatedCalories;
        const openDetail = onOpenFood && item.detailId != null ? () => onOpenFood(item) : undefined;
        const isPreparation = item.kind === "preparation";
        const componentEditing = editing?.(item);
        const componentLabel = isPreparation ? "preparación" : "alimento";
        const componentActions: ContextCardAction[] = componentEditing ? [
          { icon: Pencil, key: "portion", label: "Editar porción", onPress: () => componentEditing.onEditPortion(item) },
          { icon: RefreshCw, key: "replace", label: `Reemplazar ${componentLabel}`, onPress: () => componentEditing.onReplace(item) },
          { confirmation: { confirmLabel: `Quitar ${componentLabel}`, message: `Se quitará ${item.name} de esta comida. Permanecerá en tu biblioteca.`, title: `¿Quitar ${componentLabel}?` }, destructive: true, icon: Trash2, key: "remove", label: `Quitar ${componentLabel}`, onPress: () => componentEditing.onDelete(item) },
        ] : [];
        const nutritionQuantity = item.quantityUnit === "g" || item.quantityUnit === "ml"
          ? item.quantity
          : item.portionDisplayQuantity ?? item.quantity;
        return (
          <NutritionEntityCard
            actions={componentActions.length || openDetail ? <>
              {componentActions.length ? <ContextCardActions actions={componentActions} label={`Más acciones para ${item.name}`} title={item.name} /> : null}
              {openDetail ? <EntityCardAction label={`Ver detalle de ${item.name}`} onPress={openDetail} role="link">
                <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
              </EntityCardAction> : null}
            </> : undefined}
            collapsiblePanel={item.detailId != null}
            entity={isPreparation ? "preparation" : "food"}
            eyebrow={isPreparation ? "Preparación" : "Alimento"}
            foodEmoji={item.emoji}
            foodVisualKey={item.visualKey}
            headingLink={openDetail ? { label: `Ver detalle de ${item.name}`, onPress: openDetail } : undefined}
            key={item.id}
            nutrition={{
              calories,
              protein: { grams: item.proteinGrams, allocation: macroShare(item.proteinGrams, 4, calories) },
              carbs: { grams: item.carbsGrams, allocation: macroShare(item.carbsGrams, 4, calories) },
              fat: { grams: item.fatGrams, allocation: macroShare(item.fatGrams, 9, calories) },
            }}
            subtitle={`${item.quantity} ${item.quantityUnit}`}
            title={item.name}>
            {item.detailId != null && (isPreparation
              ? <PreparationComponentPanel item={item} key={`${item.detailId}:${item.quantity}:${item.quantityUnit}`} onOpenFood={onOpenFood} />
              : <PickerFoodNutritionPanel foodId={item.detailId} key={item.detailId} portion={{ quantity: nutritionQuantity, unit: item.quantityUnit === "ml" ? "ml" : "g" }} />)}
          </NutritionEntityCard>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({ list: { gap: tokens.spacing.lg, minWidth: 0 }, panelContent: { gap: tokens.spacing.sm } });
