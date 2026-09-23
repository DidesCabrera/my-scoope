import type {
  LibraryFoodPanelItem,
  LibraryItem,
  LibraryMealPanelItem,
  LibraryNutrition,
  LibraryWeekPanelItem,
  ProposalDailyPlan,
  ProposalFood,
  ProposalKpis,
  ProposalMeal,
  ProposalProgram,
} from "@/api/types";

const dayLabels = ["L", "M", "X", "J", "V", "S", "D"];

type NutritionTotals = {
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  ppk: number | null;
  allocation: { protein: number; carbs: number; fat: number };
};

function number(value: number | null | undefined): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function percentage(value: number, total: number): number {
  return total > 0 ? (value * 100) / total : 0;
}

function macroCalories(protein: number, carbs: number, fat: number): number {
  return protein * 4 + carbs * 4 + fat * 9;
}

function macroDistribution(protein: number, carbs: number, fat: number) {
  const calories = macroCalories(protein, carbs, fat);
  return {
    protein: percentage(protein * 4, calories),
    carbs: percentage(carbs * 4, calories),
    fat: percentage(fat * 9, calories),
  };
}

function kpiValue(value: number | null | undefined, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function nutritionTotals(kpis: ProposalKpis | null, fallback: Omit<NutritionTotals, "allocation" | "ppk">, referenceWeight?: number | null): NutritionTotals {
  const protein = kpiValue(kpis?.protein, fallback.protein);
  const carbs = kpiValue(kpis?.carbs, fallback.carbs);
  const fat = kpiValue(kpis?.fat, fallback.fat);
  const distribution = macroDistribution(protein, carbs, fat);
  return {
    calories: kpiValue(kpis?.total_kcal, fallback.calories || macroCalories(protein, carbs, fat)),
    protein,
    carbs,
    fat,
    ppk: typeof kpis?.ppk === "number" && Number.isFinite(kpis.ppk)
      ? kpis.ppk
      : referenceWeight && referenceWeight > 0
        ? protein / referenceWeight
        : null,
    allocation: {
      protein: kpiValue(kpis?.alloc_protein, distribution.protein),
      carbs: kpiValue(kpis?.alloc_carbs, distribution.carbs),
      fat: kpiValue(kpis?.alloc_fat, distribution.fat),
    },
  };
}

function foodTotals(food: ProposalFood) {
  const protein = number(food.protein);
  const carbs = number(food.carbs);
  const fat = number(food.fat);
  return {
    calories: number(food.total_kcal) || macroCalories(protein, carbs, fat),
    protein,
    carbs,
    fat,
  };
}

function mealTotals(meal: ProposalMeal, referenceWeight?: number | null): NutritionTotals {
  const fallback = meal.foods.reduce((total, food) => {
    const next = foodTotals(food);
    return {
      calories: total.calories + next.calories,
      protein: total.protein + next.protein,
      carbs: total.carbs + next.carbs,
      fat: total.fat + next.fat,
    };
  }, { calories: 0, protein: 0, carbs: 0, fat: 0 });
  return nutritionTotals(meal.kpis, fallback, referenceWeight);
}

function dailyPlanTotals(dailyplan: ProposalDailyPlan, referenceWeight?: number | null): NutritionTotals {
  const fallback = dailyplan.meals.reduce((total, item) => {
    const next = mealTotals(item.meal, referenceWeight);
    return {
      calories: total.calories + next.calories,
      protein: total.protein + next.protein,
      carbs: total.carbs + next.carbs,
      fat: total.fat + next.fat,
    };
  }, { calories: 0, protein: 0, carbs: 0, fat: 0 });
  return nutritionTotals(dailyplan.kpis, fallback, referenceWeight);
}

function libraryNutrition(totals: NutritionTotals): LibraryNutrition {
  return {
    calories: totals.calories,
    protein: { grams: totals.protein, allocation: totals.allocation.protein, per_kilogram: totals.ppk },
    carbs: { grams: totals.carbs, allocation: totals.allocation.carbs },
    fat: { grams: totals.fat, allocation: totals.allocation.fat },
  };
}

function foodPanelItem(food: ProposalFood, index: number, mealCalories: number, referenceWeight: number | null, idPrefix: string): LibraryFoodPanelItem {
  const totals = foodTotals(food);
  const distribution = macroDistribution(totals.protein, totals.carbs, totals.fat);
  return {
    id: `${idPrefix}:food:${food.food_id ?? index}`,
    relation_id: null,
    detail_id: food.food_id,
    name: food.food_name || "Alimento",
    quantity: number(food.quantity),
    quantity_unit: food.unit || "g",
    calories: totals.calories,
    calorie_share: percentage(totals.calories, mealCalories),
    calorie_distribution: distribution,
    protein_grams: totals.protein,
    protein_per_kilogram: referenceWeight != null && referenceWeight > 0 ? totals.protein / referenceWeight : null,
    carbs_grams: totals.carbs,
    fat_grams: totals.fat,
    protein_allocation: distribution.protein,
    carbs_allocation: distribution.carbs,
    fat_allocation: distribution.fat,
  };
}

function mealPanelItem(item: ProposalDailyPlan["meals"][number], index: number, planCalories: number, referenceWeight: number | null, idPrefix: string): LibraryMealPanelItem {
  const totals = mealTotals(item.meal, referenceWeight);
  return {
    id: `${idPrefix}:meal:${index}`,
    relation_id: null,
    detail_id: null,
    name: item.meal.name || `Comida ${index + 1}`,
    time: item.hour,
    note: item.note,
    foods: item.meal.foods.map((food, foodIndex) => foodPanelItem(food, foodIndex, totals.calories, referenceWeight, `${idPrefix}:meal:${index}`)),
    calories: totals.calories,
    calorie_share: percentage(totals.calories, planCalories),
    calorie_distribution: macroDistribution(totals.protein, totals.carbs, totals.fat),
    protein_grams: totals.protein,
    protein_per_kilogram: totals.ppk,
    carbs_grams: totals.carbs,
    fat_grams: totals.fat,
    protein_allocation: totals.allocation.protein,
    carbs_allocation: totals.allocation.carbs,
    fat_allocation: totals.allocation.fat,
  };
}

type AggregatedFood = {
  detailId: number | null;
  name: string;
  quantity: number;
  unit: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
};

function aggregateWeekFoods(days: ProposalProgram["days"], weekTotals: NutritionTotals, referenceWeight: number | null, week: number): LibraryFoodPanelItem[] {
  const foods = new Map<string, AggregatedFood>();
  for (const day of days) {
    for (const meal of day.dailyplan.meals) {
      for (const food of meal.meal.foods) {
        const key = food.food_id != null
          ? `id:${food.food_id}`
          : `name:${food.food_name.trim().toLocaleLowerCase("es-CL")}:${food.unit}`;
        const totals = foodTotals(food);
        const current = foods.get(key);
        foods.set(key, {
          detailId: food.food_id,
          name: food.food_name || "Alimento",
          quantity: (current?.quantity ?? 0) + number(food.quantity),
          unit: food.unit || "g",
          calories: (current?.calories ?? 0) + totals.calories,
          protein: (current?.protein ?? 0) + totals.protein,
          carbs: (current?.carbs ?? 0) + totals.carbs,
          fat: (current?.fat ?? 0) + totals.fat,
        });
      }
    }
  }
  return [...foods.entries()].map(([key, food]) => ({
    id: `proposed-program:week:${week}:food:${key}`,
    relation_id: null,
    detail_id: food.detailId,
    name: food.name,
    quantity: food.quantity,
    quantity_unit: food.unit,
    calories: food.calories,
    calorie_share: percentage(food.calories, weekTotals.calories),
    calorie_distribution: macroDistribution(food.protein, food.carbs, food.fat),
    protein_grams: food.protein,
    protein_per_kilogram: referenceWeight != null && referenceWeight > 0 ? food.protein / referenceWeight : null,
    carbs_grams: food.carbs,
    fat_grams: food.fat,
    protein_allocation: percentage(food.protein, weekTotals.protein),
    carbs_allocation: percentage(food.carbs, weekTotals.carbs),
    fat_allocation: percentage(food.fat, weekTotals.fat),
  }));
}

type WeekDraft = Omit<LibraryWeekPanelItem, "calorie_share" | "protein_allocation" | "carbs_allocation" | "fat_allocation"> & {
  totals: NutritionTotals;
};

function weekDraft(program: ProposalProgram, week: number): WeekDraft {
  const proposalDays = program.days.filter((day) => day.week_number === week);
  const referenceWeight = number(program.nutrition_specification?.weeks.find((item) => item.week === week)?.reference_weight_kg);
  const days = dayLabels.map((dayLabel, index) => {
    const dayNumber = index + 1;
    const proposedDay = proposalDays.find((day) => day.day_number === dayNumber);
    if (!proposedDay) {
      return {
        id: `proposed-program:week:${week}:day:${dayNumber}`,
        day_number: dayNumber,
        day_label: dayLabel,
        dailyplan_id: null,
        plan_name: null,
        nutrition: null,
        meals: [],
      };
    }
    const totals = dailyPlanTotals(proposedDay.dailyplan, referenceWeight);
    return {
      id: `proposed-program:week:${week}:day:${dayNumber}`,
      day_number: dayNumber,
      day_label: dayLabel,
      dailyplan_id: null,
      plan_name: proposedDay.dailyplan.name || `Plan diario ${dayNumber}`,
      nutrition: libraryNutrition(totals),
      meals: proposedDay.dailyplan.meals.map((meal, mealIndex) => mealPanelItem(meal, mealIndex, totals.calories, referenceWeight, `proposed-program:week:${week}:day:${dayNumber}`)),
    };
  });
  const totals = days.reduce<NutritionTotals>((sum, day) => ({
    calories: sum.calories + (day.nutrition?.calories ?? 0),
    protein: sum.protein + (day.nutrition?.protein.grams ?? 0),
    carbs: sum.carbs + (day.nutrition?.carbs.grams ?? 0),
    fat: sum.fat + (day.nutrition?.fat.grams ?? 0),
    ppk: null,
    allocation: { protein: 0, carbs: 0, fat: 0 },
  }), { calories: 0, protein: 0, carbs: 0, fat: 0, ppk: null, allocation: { protein: 0, carbs: 0, fat: 0 } });
  const foods = aggregateWeekFoods(proposalDays, totals, referenceWeight, week);
  const filledDaysCount = proposalDays.length;
  return {
    id: `proposed-program:week:${week}`,
    week_number: week,
    days,
    filled_days_count: filledDaysCount,
    meals_count: proposalDays.reduce((total, day) => total + day.dailyplan.meals.length, 0),
    foods_count: foods.length,
    average_calories: filledDaysCount ? totals.calories / filledDaysCount : 0,
    foods,
    calories: totals.calories,
    calorie_distribution: macroDistribution(totals.protein, totals.carbs, totals.fat),
    protein_grams: totals.protein,
    carbs_grams: totals.carbs,
    fat_grams: totals.fat,
    totals,
  };
}

export function proposalProgramLibraryItem(program: ProposalProgram): LibraryItem {
  const drafts = Array.from({ length: program.duration_weeks }, (_, index) => weekDraft(program, index + 1));
  const programTotals = drafts.reduce((total, week) => ({
    calories: total.calories + week.calories,
    protein: total.protein + week.protein_grams,
    carbs: total.carbs + week.carbs_grams,
    fat: total.fat + week.fat_grams,
  }), { calories: 0, protein: 0, carbs: 0, fat: 0 });
  const weeks: LibraryWeekPanelItem[] = drafts.map(({ totals: _totals, ...week }) => ({
    ...week,
    calorie_share: percentage(week.calories, programTotals.calories),
    protein_allocation: percentage(week.protein_grams, programTotals.protein),
    carbs_allocation: percentage(week.carbs_grams, programTotals.carbs),
    fat_allocation: percentage(week.fat_grams, programTotals.fat),
  }));
  const uniqueFoods = new Set(weeks.flatMap((week) => (week.foods ?? []).map((food) => food.detail_id != null ? `id:${food.detail_id}` : `${food.name}:${food.quantity_unit}`)));
  const programNutrition = nutritionTotals(null, programTotals);
  return {
    id: 0,
    entity: "program",
    name: program.name || "Programa propuesto",
    subtitle: "Propuesta del Asistente AI",
    nutrition: libraryNutrition(programNutrition),
    indicators: [
      { icon: "week", label: "semanas", value: program.duration_weeks },
      { icon: "dailyPlan", label: "planes asignados", value: program.days.length },
      { icon: "food", label: "alimentos", value: uniqueFoods.size },
    ],
    panel: { kind: "weeks", foods: [], meals: [], weeks },
    creator: "Asistente AI",
    created_at: "",
    is_draft: true,
    can_calendarize: false,
    actions: [],
  };
}
