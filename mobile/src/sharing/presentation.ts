import type { ComparisonMetric, ComparisonResult, LibraryFoodPanelItem, LibraryItem, LibraryMealPanelItem, LibraryNutrition, LibraryWeekPanelItem, ShareResource, ShareSnapshot } from "@/api/types";
import type { FoodPanelItem, MealPanelItem } from "@/components/panels";

export type ShareNutrition = NonNullable<ShareResource["snapshot"]>["nutrition"];
export type ShareMeal = NonNullable<NonNullable<ShareResource["snapshot"]>["meals"]>[number];

export function sharedDate(value?: string): string | undefined {
  if (!value) return undefined;
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("es-CL", { day: "numeric", month: "short", year: "numeric" });
}

export function sharedNutrition(values: ShareNutrition) {
  const calories = values.calories || values.protein_grams * 4 + values.carbs_grams * 4 + values.fat_grams * 9;
  return {
    calories,
    protein: { grams: values.protein_grams, allocation: calories > 0 ? values.protein_grams * 4 * 100 / calories : 0 },
    carbs: { grams: values.carbs_grams, allocation: calories > 0 ? values.carbs_grams * 4 * 100 / calories : 0 },
    fat: { grams: values.fat_grams, allocation: calories > 0 ? values.fat_grams * 9 * 100 / calories : 0 },
  };
}

function libraryNutrition(values: ShareNutrition): LibraryNutrition {
  const nutrition = sharedNutrition(values);
  return { ...nutrition, protein: { ...nutrition.protein, per_kilogram: null } };
}

function calorieDistribution(nutrition: LibraryNutrition) {
  return { protein: nutrition.protein.allocation, carbs: nutrition.carbs.allocation, fat: nutrition.fat.allocation };
}

function libraryFood(food: ShareMeal["foods"][number], id: string, planCalories: number): LibraryFoodPanelItem {
  const nutrition = libraryNutrition(food.nutrition);
  return {
    id,
    relation_id: null,
    detail_id: null,
    name: food.name,
    quantity: food.quantity_grams,
    quantity_unit: food.quantity_unit ?? "g",
    calories: nutrition.calories,
    calorie_share: planCalories > 0 ? nutrition.calories * 100 / planCalories : 0,
    calorie_distribution: calorieDistribution(nutrition),
    protein_grams: nutrition.protein.grams,
    protein_per_kilogram: null,
    carbs_grams: nutrition.carbs.grams,
    fat_grams: nutrition.fat.grams,
    protein_allocation: nutrition.protein.allocation,
    carbs_allocation: nutrition.carbs.allocation,
    fat_allocation: nutrition.fat.allocation,
  };
}

function libraryMeal(meal: ShareMeal, id: string, planCalories: number): LibraryMealPanelItem {
  const nutrition = libraryNutrition(meal.nutrition);
  return {
    id,
    relation_id: null,
    detail_id: null,
    name: meal.name,
    time: meal.time?.slice(0, 5) ?? null,
    note: "",
    foods: meal.foods.map((food, index) => libraryFood(food, `${id}:food:${index}`, nutrition.calories)),
    calories: nutrition.calories,
    calorie_share: planCalories > 0 ? nutrition.calories * 100 / planCalories : 0,
    calorie_distribution: calorieDistribution(nutrition),
    protein_grams: nutrition.protein.grams,
    protein_per_kilogram: null,
    carbs_grams: nutrition.carbs.grams,
    fat_grams: nutrition.fat.grams,
    protein_allocation: nutrition.protein.allocation,
    carbs_allocation: nutrition.carbs.allocation,
    fat_allocation: nutrition.fat.allocation,
  };
}

const dayLabels = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

function sumNutrition(values: ShareNutrition[]): ShareNutrition {
  return values.reduce((total, value) => ({
    calories: total.calories + value.calories,
    protein_grams: total.protein_grams + value.protein_grams,
    carbs_grams: total.carbs_grams + value.carbs_grams,
    fat_grams: total.fat_grams + value.fat_grams,
  }), { calories: 0, protein_grams: 0, carbs_grams: 0, fat_grams: 0 });
}

export function sharedProgramLibraryItem(snapshot: ShareSnapshot, title: string): LibraryItem {
  const duration = Math.max(snapshot.summary.duration_weeks ?? 1, 1);
  const weeks: LibraryWeekPanelItem[] = Array.from({ length: duration }, (_, weekIndex) => {
    const weekNumber = weekIndex + 1;
    const sourceDays = (snapshot.days ?? []).filter((day) => day.week_number === weekNumber);
    const weekNutrition = libraryNutrition(sumNutrition(sourceDays.map((day) => day.plan.nutrition)));
    const foods = sourceDays.flatMap((day) => (day.plan.meals ?? []).flatMap((meal, mealIndex) => meal.foods.map((food, foodIndex) => libraryFood(food, `shared:${weekNumber}:${day.day_number}:${mealIndex}:${foodIndex}`, weekNutrition.calories))));
    return {
      id: `shared-week-${weekNumber}`,
      week_number: weekNumber,
      days: dayLabels.map((dayLabel, dayIndex) => {
        const source = sourceDays.find((day) => day.day_number === dayIndex + 1);
        if (!source) return { day_number: dayIndex + 1, day_label: dayLabel, plan_name: null };
        const nutrition = libraryNutrition(source.plan.nutrition);
        return {
          id: `shared-day-${weekNumber}-${dayIndex + 1}`,
          day_number: dayIndex + 1,
          day_label: dayLabel,
          plan_name: source.plan.subject.title,
          nutrition,
          meals: (source.plan.meals ?? []).map((meal, mealIndex) => libraryMeal(meal, `shared-meal-${weekNumber}-${dayIndex + 1}-${mealIndex}`, nutrition.calories)),
        };
      }),
      filled_days_count: sourceDays.length,
      meals_count: sourceDays.reduce((total, day) => total + (day.plan.meals?.length ?? 0), 0),
      foods_count: foods.length,
      average_calories: sourceDays.length ? weekNutrition.calories / sourceDays.length : 0,
      foods,
      calories: weekNutrition.calories,
      calorie_share: snapshot.nutrition.calories > 0 ? weekNutrition.calories * 100 / snapshot.nutrition.calories : 0,
      calorie_distribution: calorieDistribution(weekNutrition),
      protein_grams: weekNutrition.protein.grams,
      carbs_grams: weekNutrition.carbs.grams,
      fat_grams: weekNutrition.fat.grams,
      protein_allocation: weekNutrition.protein.allocation,
      carbs_allocation: weekNutrition.carbs.allocation,
      fat_allocation: weekNutrition.fat.allocation,
    };
  });
  return {
    id: 0,
    entity: "program",
    name: title,
    subtitle: "Programa semanal compartido",
    nutrition: libraryNutrition(snapshot.nutrition),
    indicators: [
      { icon: "week", label: "semanas", value: duration },
      { icon: "dailyPlan", label: "planes diarios", value: snapshot.summary.filled_days ?? 0 },
    ],
    panel: { kind: "weeks", foods: [], meals: [], weeks },
    creator: "Elemento compartido",
    created_at: "",
    is_draft: false,
    can_calendarize: false,
    actions: [],
  };
}

const comparisonMetricSpecs = [
  ["total_kcal", "Calorías", "kcal"], ["ppk", "P/kg", "g/kg"], ["protein", "Proteína", "g"],
  ["carbs", "Carbohidratos", "g"], ["fat", "Grasas", "g"], ["alloc_protein", "P%", "%"],
  ["alloc_carbs", "C%", "%"], ["alloc_fat", "F%", "%"],
] as const;

export function sharedComparisonResult(snapshot: ShareSnapshot): ComparisonResult | null {
  const comparison = snapshot.comparison;
  if (!comparison || comparison.snapshot_payload.length < 2) return null;
  const rows = comparison.snapshot_payload;
  const metrics: ComparisonMetric[] = comparisonMetricSpecs.map(([key, label, unit]) => {
    const maximum = Math.max(...rows.map((row) => Number(row.values[key] ?? 0)), 0);
    return {
      key,
      label,
      unit,
      bars: rows.map((row, index) => {
        const value = Number(row.values[key] ?? 0);
        const formatted = value.toLocaleString("es-CL", { maximumFractionDigits: key === "ppk" ? 2 : 1 });
        return {
          position: index + 1,
          id: row.id,
          label: row.name,
          quantity: row.quantity ?? null,
          quantity_unit: row.quantity_unit ?? null,
          value,
          formatted_value: `${formatted}${unit === "%" ? "%" : ` ${unit}`}`,
          relative_percentage: maximum > 0 ? value * 100 / maximum : 0,
        };
      }),
    };
  });
  return {
    kind: comparison.kind,
    kind_label: comparison.kind === "foods" ? "Alimentos" : comparison.kind === "meals" ? "Comidas" : "Planes diarios",
    historical_snapshot: true,
    saved_comparison_id: null,
    saved_comparison_name: snapshot.subject.title,
    metrics,
    items: rows.map((row, index) => ({
      position: index + 1,
      id: row.id,
      name: row.name,
      quantity: row.quantity ?? null,
      quantity_unit: row.quantity_unit ?? null,
      values: {
        calories: Number(row.values.total_kcal ?? 0),
        protein_g: Number(row.values.protein ?? 0),
        carbs_g: Number(row.values.carbs ?? 0),
        fat_g: Number(row.values.fat ?? 0),
        protein_per_kilogram: row.values.ppk == null ? null : Number(row.values.ppk),
      },
    })),
  };
}

export function sharedFoodPanelItems(meal: ShareMeal): FoodPanelItem[] {
  return meal.foods.map((food, index) => {
    const item = sharedNutrition(food.nutrition);
    return {
      detailId: index,
      id: `shared-food-${index}`,
      name: food.name,
      quantity: food.quantity_grams,
      quantityUnit: food.quantity_unit ?? "g",
      calories: item.calories,
      calorieShare: meal.nutrition.calories > 0 ? item.calories * 100 / meal.nutrition.calories : 0,
      proteinGrams: item.protein.grams,
      carbsGrams: item.carbs.grams,
      fatGrams: item.fat.grams,
      proteinAllocation: item.protein.allocation,
      carbsAllocation: item.carbs.allocation,
      fatAllocation: item.fat.allocation,
    };
  });
}

export function sharedMealPanelItems(meals: ShareMeal[], planCalories: number): MealPanelItem[] {
  return meals.map((meal, index) => {
    const item = sharedNutrition(meal.nutrition);
    return {
      canOpen: true,
      id: String(index),
      name: meal.name,
      time: meal.time?.slice(0, 5) ?? undefined,
      foods: meal.foods.map((food) => ({ name: food.name, quantity: food.quantity_grams, quantityUnit: food.quantity_unit ?? "g" })),
      calories: item.calories,
      calorieShare: planCalories > 0 ? item.calories * 100 / planCalories : 0,
      proteinGrams: item.protein.grams,
      carbsGrams: item.carbs.grams,
      fatGrams: item.fat.grams,
      proteinAllocation: item.protein.allocation,
      carbsAllocation: item.carbs.allocation,
      fatAllocation: item.fat.allocation,
    };
  });
}
