export type WeightTrendPoint = {
  id: number;
  measured_on: string;
  weight_kg: number;
};

export type DailyWeightTrendPoint = WeightTrendPoint & {
  estimated: boolean;
};

const DAY_MS = 24 * 60 * 60 * 1000;

function dateValue(value: string): number {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return Number.NaN;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const timestamp = Date.UTC(year, month - 1, day);
  const parsed = new Date(timestamp);
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day
    ? timestamp
    : Number.NaN;
}

function dateFromValue(value: number): string {
  return new Date(value).toISOString().slice(0, 10);
}

export function sortedWeightTrend(items: WeightTrendPoint[]): WeightTrendPoint[] {
  return [...items]
    .filter((item) => Number.isFinite(item.weight_kg) && Number.isFinite(dateValue(item.measured_on)))
    .sort((left, right) => dateValue(left.measured_on) - dateValue(right.measured_on) || left.id - right.id);
}

export function dailyWeightTrend(items: WeightTrendPoint[], throughDate: string): DailyWeightTrendPoint[] {
  const measurementsByDate = new Map<string, WeightTrendPoint>();
  for (const item of sortedWeightTrend(items)) measurementsByDate.set(item.measured_on, item);
  const measurements = [...measurementsByDate.values()];
  if (!measurements.length) return [];

  const indexedByTimestamp = new Map(measurements.map((item, index) => [dateValue(item.measured_on), { index, item }]));
  const firstTimestamp = dateValue(measurements[0].measured_on);
  const lastTimestamp = dateValue(measurements.at(-1)?.measured_on ?? measurements[0].measured_on);
  const requestedEnd = dateValue(throughDate);
  const endTimestamp = Number.isFinite(requestedEnd) ? Math.max(lastTimestamp, requestedEnd) : lastTimestamp;
  const trend: DailyWeightTrendPoint[] = [];
  let previousIndex = 0;
  let nextIndex = 1;

  for (let timestamp = firstTimestamp; timestamp <= endTimestamp; timestamp += DAY_MS) {
    const measurement = indexedByTimestamp.get(timestamp);
    if (measurement) {
      previousIndex = measurement.index;
      nextIndex = measurement.index + 1;
      trend.push({ ...measurement.item, estimated: false });
      continue;
    }

    const previous = measurements[previousIndex];
    const next = measurements[nextIndex];
    const previousTimestamp = dateValue(previous.measured_on);
    const nextTimestamp = next ? dateValue(next.measured_on) : null;
    const weight = next && nextTimestamp != null
      ? previous.weight_kg + ((next.weight_kg - previous.weight_kg) * (timestamp - previousTimestamp)) / (nextTimestamp - previousTimestamp)
      : previous.weight_kg;
    trend.push({ estimated: true, id: -trend.length - 1, measured_on: dateFromValue(timestamp), weight_kg: weight });
  }

  return trend;
}
