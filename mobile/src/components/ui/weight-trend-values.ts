export type WeightTrendPoint = {
  id: number;
  measured_on: string;
  weight_kg: number;
};

function dateValue(value: string): number {
  return new Date(`${value}T12:00:00`).getTime();
}

export function sortedWeightTrend(items: WeightTrendPoint[]): WeightTrendPoint[] {
  return [...items]
    .filter((item) => Number.isFinite(item.weight_kg) && Number.isFinite(dateValue(item.measured_on)))
    .sort((left, right) => dateValue(left.measured_on) - dateValue(right.measured_on) || left.id - right.id);
}
