import { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import type { LibraryItem, LibraryNutrition } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { libraryFoodNutritionFacts } from "@/components/libraries/presentation-adapters";
import { FoodNutritionPanel } from "@/components/panels";
import { InlineNotice } from "@/components/ui";
import { tokens } from "@/design/tokens";

export function PickerFoodNutritionPanel({ foodId, nutrition, portion }: {
  foodId: number;
  nutrition?: LibraryNutrition;
  portion: { quantity: number | null; unit: "g" | "ml" };
}) {
  const { apiRequest } = useSession();
  const [detail, setDetail] = useState<LibraryItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    void apiRequest<LibraryItem>(`/api/v1/library/foods/${foodId}`)
      .then((item) => { if (active) setDetail(item); })
      .catch(() => { if (active) setFailed(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, foodId]);

  const baseNutrition = nutrition ?? detail?.nutrition;
  return <View style={styles.content}>
    {baseNutrition ? <FoodNutritionPanel facts={libraryFoodNutritionFacts(baseNutrition, detail?.food_nutrition)} portion={portion} /> : null}
    {loading ? <ActivityIndicator accessibilityLabel="Cargando información nutricional" color={tokens.color.food} size="small" /> : null}
    {failed ? <InlineNotice tone="warning">{nutrition ? "No pudimos cargar los nutrientes adicionales. Los macros disponibles siguen visibles." : "No pudimos cargar la información nutricional de este alimento."}</InlineNotice> : null}
  </View>;
}

const styles = StyleSheet.create({ content: { gap: tokens.spacing.sm } });
