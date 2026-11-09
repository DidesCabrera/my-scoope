import { ChevronRight } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/ui/surfaces";
import { tokens } from "@/design/tokens";

export type PreparationIngredient = {
  food_id: number;
  name: string;
  quantity_g: number;
  preparation_state: string;
  is_condiment: boolean;
};

const preparationStates: Record<string, string> = {
  baked: "Horneado",
  cooked: "Cocido",
  fried: "Frito",
  grilled: "A la plancha",
  raw: "Crudo",
  ready_to_eat: "Listo para comer",
  steamed: "Al vapor",
};

export function preparationStateLabel(state: string): string {
  return preparationStates[state] ?? state.replaceAll("_", " ");
}

const allergenNames: Record<string, string> = {
  egg: "Huevo", fish: "Pescado", gluten: "Gluten", milk: "Leche", peanut: "Maní", sesame: "Sésamo",
  shellfish: "Mariscos", soy: "Soya", tree_nut: "Frutos secos", wheat: "Trigo",
};

export function formatPreparationNumber(value: number, maximumFractionDigits = 1) {
  return new Intl.NumberFormat("es-CL", { maximumFractionDigits }).format(value);
}

export function formatPreparationAllergens(allergens: string[]) {
  return allergens.length ? allergens.map((allergen) => allergenNames[allergen] ?? allergen.replaceAll("_", " ")).join(", ") : "Sin datos declarados";
}

export function PreparationIngredientsCard({ ingredients, onOpenFood }: { ingredients: PreparationIngredient[]; onOpenFood(foodId: number): void }) {
  return (
    <Card style={styles.card}>
      <View style={styles.heading}>
        <Text style={styles.headingTitle}>Ingredientes</Text>
        <Text style={styles.headingDetail}>{ingredients.length} {ingredients.length === 1 ? "alimento" : "alimentos"}</Text>
      </View>
      <View>
        {ingredients.map((ingredient, index) => (
          <Pressable
            accessibilityLabel={`Ver ${ingredient.name}, ${formatPreparationNumber(ingredient.quantity_g)} gramos`}
            accessibilityRole="button"
            key={`${ingredient.food_id}:${index}`}
            onPress={() => onOpenFood(ingredient.food_id)}
            style={({ pressed }) => [styles.row, index === ingredients.length - 1 && styles.lastRow, pressed && styles.pressed]}>
            <View style={styles.copy}>
              <Text style={styles.name}>{ingredient.name}</Text>
              <Text style={styles.meta}>{preparationStateLabel(ingredient.preparation_state)}{ingredient.is_condiment ? " · Condimento" : ""}</Text>
            </View>
            <Text style={styles.amount}>{formatPreparationNumber(ingredient.quantity_g)} g</Text>
            <ChevronRight color={tokens.color.textSoft} size={18} />
          </Pressable>
        ))}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { gap: tokens.spacing.sm },
  heading: { alignItems: "baseline", flexDirection: "row", justifyContent: "space-between", marginBottom: tokens.spacing.xs },
  headingTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.bold },
  headingDetail: { color: tokens.color.textSoft, fontSize: tokens.type.caption },
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 58, paddingVertical: tokens.spacing.sm },
  lastRow: { borderBottomWidth: 0 },
  pressed: { opacity: 0.65 },
  copy: { flex: 1, gap: 3, minWidth: 0 },
  name: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  meta: { color: tokens.color.textSoft, fontSize: tokens.type.caption },
  amount: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold },
});
