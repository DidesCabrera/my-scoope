export function numeric(value) {
  return Number(value) || 0;
}

function safePercentage(part, total) {
  const normalizedTotal = numeric(total);
  return normalizedTotal > 0 ? (numeric(part) / normalizedTotal) * 100 : 0;
}

export function projectProgramWeekRows(existingRows, selectedPlan, selectedDayNumbers) {
  if (!selectedPlan) return [];

  const selectedDays = new Set((selectedDayNumbers || []).map(Number));
  const rows = (existingRows || []).map((row) => {
    if (!selectedDays.has(Number(row.day_number))) {
      return { ...row, is_projected: false };
    }

    return {
      ...row,
      dailyplan_id: selectedPlan.id,
      dailyplan_name: selectedPlan.name || "Plan diario",
      has_plan: true,
      is_empty: false,
      is_projected: true,
      projected_label: row.has_plan ? "Reemplazo" : "Por agregar",
      total_kcal: numeric(selectedPlan.total_kcal),
      protein: numeric(selectedPlan.protein),
      carbs: numeric(selectedPlan.carbs),
      fat: numeric(selectedPlan.fat),
      kcal_protein: numeric(selectedPlan.kcal_protein),
      kcal_carbs: numeric(selectedPlan.kcal_carbs),
      kcal_fat: numeric(selectedPlan.kcal_fat),
      ppk: numeric(selectedPlan.ppk),
      kcal_distribution: selectedPlan.alloc || {},
    };
  });

  const totals = rows.reduce((result, row) => {
    result.total_kcal += numeric(row.total_kcal);
    result.kcal_protein += numeric(row.kcal_protein);
    result.kcal_carbs += numeric(row.kcal_carbs);
    result.kcal_fat += numeric(row.kcal_fat);
    return result;
  }, { total_kcal: 0, kcal_protein: 0, kcal_carbs: 0, kcal_fat: 0 });

  return rows.map((row) => ({
    ...row,
    kcal_share: safePercentage(row.total_kcal, totals.total_kcal),
    alloc: {
      protein: safePercentage(row.kcal_protein, totals.kcal_protein),
      carbs: safePercentage(row.kcal_carbs, totals.kcal_carbs),
      fat: safePercentage(row.kcal_fat, totals.kcal_fat),
    },
  }));
}
