import { type Href, Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronLeft, ChevronRight } from "lucide-react-native";
import { useEffect, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarCommitment, CalendarCommitmentKind, CalendarOverviewData, CalendarPeriodFoodsData } from "@/api/calendar-types";
import { useSession } from "@/auth/session-context";
import { commitmentFoodPanelItem, commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { validCalendarFoodPeriod } from "@/components/calendarization/calendar-food-period";
import { monthKeyFromDate, monthLabel, monthWindow, shiftMonth } from "@/components/calendarization/calendar-month";
import { GroupedFoodsCard } from "@/components/panels";
import { Button, Card, InlineNotice, LoadingState, NativeDateTimeField, Screen, SectionPageHeader } from "@/components/ui";
import { tokens } from "@/design/tokens";

function isCommitmentKind(value: string | undefined): value is CalendarCommitmentKind {
  return value === "shopping" || value === "cooking" || value === "training";
}

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" })
    .format(new Date(`${value}T12:00:00`));
}

export default function RegisterCommitmentsScreen() {
  const router = useRouter();
  const { kind: requestedKind } = useLocalSearchParams<{ kind?: string }>();
  const kind = isCommitmentKind(requestedKind) ? requestedKind : null;
  const { apiRequest, status } = useSession();
  const [localToday, setLocalToday] = useState<string | null>(null);
  const [visibleMonth, setVisibleMonth] = useState<string | null>(null);
  const [monthOverview, setMonthOverview] = useState<CalendarOverviewData | null>(null);
  const [selectedDates, setSelectedDates] = useState<string[]>([]);
  const [note, setNote] = useState("");
  const [foodStartDate, setFoodStartDate] = useState("");
  const [foodEndDate, setFoodEndDate] = useState("");
  const [foodPreview, setFoodPreview] = useState<CalendarPeriodFoodsData | null>(null);
  const [foodLoading, setFoodLoading] = useState(false);
  const [foodError, setFoodError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "authenticated" || !kind) return;
    let active = true;
    void apiRequest<CalendarOverviewData>("/api/v1/calendar?days=1")
      .then((result) => {
        if (!active) return;
        setLocalToday(result.local_date);
        setVisibleMonth(monthKeyFromDate(result.local_date));
      })
      .catch((nextError) => { if (active) { setError(userFacingError(nextError)); setLoading(false); } });
    return () => { active = false; };
  }, [apiRequest, kind, status]);

  useEffect(() => {
    if (status !== "authenticated" || !visibleMonth) return;
    let active = true;
    const window = monthWindow(visibleMonth);
    void apiRequest<CalendarOverviewData>(`/api/v1/calendar?start_date=${window.startDate}&days=${window.days}`)
      .then((result) => { if (active) setMonthOverview(result); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, status, visibleMonth]);

  useEffect(() => {
    if (status !== "authenticated" || kind !== "shopping" || !validCalendarFoodPeriod(foodStartDate, foodEndDate)) return;
    let active = true;
    void apiRequest<CalendarPeriodFoodsData>(`/api/v1/calendar/foods?start_date=${foodStartDate}&end_date=${foodEndDate}`)
      .then((result) => { if (active) setFoodPreview(result); })
      .catch((nextError) => { if (active) setFoodError(userFacingError(nextError)); })
      .finally(() => { if (active) setFoodLoading(false); });
    return () => { active = false; };
  }, [apiRequest, foodEndDate, foodStartDate, kind, status]);

  const selected = useMemo(() => [...selectedDates].sort(), [selectedDates]);
  if (status === "anonymous") return <Redirect href="/login" />;
  if (!kind) return <Redirect href="/calendar" />;
  const presentation = commitmentPresentation[kind];

  function changeFoodPeriod(start: string, end: string) {
    setFoodStartDate(start);
    setFoodEndDate(end);
    setFoodPreview(null);
    setFoodError(null);
    setFoodLoading(validCalendarFoodPeriod(start, end));
  }

  function toggleDate(date: string) {
    if (!localToday || date < localToday) return;
    if (selectedDates.includes(date)) {
      setSelectedDates((current) => current.filter((item) => item !== date));
      return;
    }
    if (selectedDates.length >= 62) {
      setError("Puedes elegir hasta 62 fechas por registro.");
      return;
    }
    setError(null);
    setSelectedDates((current) => [...current, date]);
  }

  function changeMonth(delta: number) {
    if (!visibleMonth) return;
    setLoading(true);
    setError(null);
    setMonthOverview(null);
    setVisibleMonth(shiftMonth(visibleMonth, delta));
  }

  async function register() {
    if (!selected.length) return;
    setSaving(true);
    setError(null);
    try {
      await apiRequest<{ items: CalendarCommitment[] }>("/api/v1/calendar/commitments", {
        method: "POST",
        body: JSON.stringify({
          kind, dates: selected, note: note.trim(),
          ...(kind === "shopping" && foodStartDate && foodEndDate
            ? { food_period_start: foodStartDate, food_period_end: foodEndDate } : {}),
        }),
      });
      router.replace("/calendar" as Href);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  }

  return <Screen contentStyle={styles.content}>
    <SectionPageHeader countLabel="fechas" section="calendarization" subtitle="Marca varios días; puedes cambiar de mes sin perder tu selección." title={presentation.label} />
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    <Card>
      <View style={styles.monthNavigation}>
        <Pressable accessibilityLabel="Mes anterior" accessibilityRole="button" accessibilityState={{ disabled: !visibleMonth || !localToday || visibleMonth <= monthKeyFromDate(localToday) }} disabled={!visibleMonth || !localToday || visibleMonth <= monthKeyFromDate(localToday)} onPress={() => changeMonth(-1)} style={styles.monthArrow}>
          <ChevronLeft color={tokens.color.textMain} size={20} />
        </Pressable>
        <Text accessibilityRole="header" style={styles.monthTitle}>{visibleMonth ? monthLabel(visibleMonth) : ""}</Text>
        <Pressable accessibilityLabel="Mes siguiente" accessibilityRole="button" onPress={() => changeMonth(1)} style={styles.monthArrow}>
          <ChevronRight color={tokens.color.textMain} size={20} />
        </Pressable>
      </View>
      {loading ? <LoadingState label="Cargando fechas…" /> : null}
      <View style={styles.grid}>
        {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
        {monthOverview?.days.map((day) => {
          const exists = day.commitments?.some((item) => item.kind === kind) ?? false;
          const isPast = Boolean(localToday && day.calendar_date < localToday);
          const isSelected = selectedDates.includes(day.calendar_date);
          return <Pressable
            accessibilityLabel={`${shortDate(day.calendar_date)}: ${exists ? "ya registrado" : isSelected ? "seleccionado" : isPast ? "fecha anterior" : "sin seleccionar"}`}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: isSelected || exists, disabled: isPast || exists }}
            disabled={isPast || exists}
            key={day.calendar_date}
            onPress={() => toggleDate(day.calendar_date)}
            style={[styles.gridDate, isSelected && { backgroundColor: `${presentation.color}33`, borderColor: presentation.color }, exists && styles.gridDateExisting, monthKeyFromDate(day.calendar_date) !== visibleMonth && styles.gridDateAdjacent, isPast && styles.gridDatePast]}>
            <Text style={[styles.gridNumber, (isSelected || exists) && { color: presentation.color }]}>{day.calendar_date.slice(8, 10)}</Text>
            {exists ? <View style={[styles.existingDot, { backgroundColor: presentation.color }]} /> : null}
          </Pressable>;
        })}
      </View>
      <Text style={styles.legend}>Los días con un punto ya tienen este compromiso registrado.</Text>
    </Card>
    <Card>
      <Text style={styles.sectionTitle}>Fechas elegidas · {selected.length}</Text>
      {selected.length ? <View style={styles.selectedDates}>
        {selected.slice(0, 8).map((date) => <Text key={date} style={styles.selectedDate}>{shortDate(date)}</Text>)}
        {selected.length > 8 ? <Text style={styles.moreDates}>y {selected.length - 8} más</Text> : null}
      </View> : <Text style={styles.helper}>Toca las fechas del calendario para seleccionarlas.</Text>}
    </Card>
    {kind === "shopping" ? <>
      <Card>
        <Text style={styles.sectionTitle}>Periodo para la lista de alimentos</Text>
        <Text style={styles.helper}>Elige un periodo para guardar una copia de esta lista con cada compromiso. Puedes dejarlo vacío si no necesitas una lista.</Text>
        <NativeDateTimeField label="Fecha de inicio" mode="date" onChange={(value) => changeFoodPeriod(value, foodEndDate)} value={foodStartDate} />
        <NativeDateTimeField label="Fecha de término" mode="date" onChange={(value) => changeFoodPeriod(foodStartDate, value)} value={foodEndDate} />
        {foodStartDate || foodEndDate ? <Button label="Quitar periodo y lista" onPress={() => changeFoodPeriod("", "")} variant="secondary" /> : null}
        {(foodStartDate && !foodEndDate) || (!foodStartDate && foodEndDate) ? <InlineNotice>Elige ambas fechas para guardar la lista.</InlineNotice> : null}
        {foodStartDate && foodEndDate && !validCalendarFoodPeriod(foodStartDate, foodEndDate) ? <InlineNotice tone="error">Elige un periodo válido de hasta 366 días.</InlineNotice> : null}
        {foodError ? <InlineNotice tone="error">{foodError}</InlineNotice> : null}
        {foodLoading ? <LoadingState label="Calculando alimentos…" /> : null}
      </Card>
      {foodPreview ? <>
        <Text style={styles.helper}>{foodPreview.plans_count} {foodPreview.plans_count === 1 ? "plan programado" : "planes programados"} en este periodo.</Text>
        <GroupedFoodsCard
          items={foodPreview.foods.map(commitmentFoodPanelItem)}
          key={`${foodPreview.start_date}:${foodPreview.end_date}`}
          onOpenItem={(food) => { if (food.detailId != null) router.push(`/libraries/foods/${food.detailId}` as Href); }}
          title="Alimentos para comprar"
        />
      </> : null}
    </> : null}
    <Card>
      <Text style={styles.sectionTitle}>Nota (opcional)</Text>
      <Text style={styles.helper}>Se registrará en todas las fechas elegidas.</Text>
      <TextInput accessibilityLabel="Nota del compromiso" maxLength={500} multiline onChangeText={setNote} placeholder="Agrega una nota para recordar los detalles…" placeholderTextColor={tokens.color.textMuted} style={styles.noteInput} textAlignVertical="top" value={note} />
      <Text style={styles.noteCount}>{note.length}/500</Text>
    </Card>
    <Button disabled={!selected.length || saving || Boolean(foodStartDate || foodEndDate) && (!foodPreview || foodLoading)} label="Registrar en el calendario" loading={saving} onPress={() => void register()} />
    <Button label="Volver al calendario" onPress={() => router.back()} variant="secondary" />
  </Screen>;
}

const styles = StyleSheet.create({
  content: { gap: tokens.spacing.lg },
  existingDot: { borderRadius: 3, bottom: 3, height: 5, position: "absolute", width: 5 },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: tokens.spacing.sm },
  gridDate: { alignItems: "center", borderColor: "transparent", borderRadius: 10, borderWidth: 2, justifyContent: "center", minHeight: 40, width: "13.5%" },
  gridDateAdjacent: { opacity: 0.5 },
  gridDateExisting: { backgroundColor: tokens.color.surfaceMuted },
  gridDatePast: { opacity: 0.35 },
  gridHeader: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center", width: "13.5%" },
  gridNumber: { color: tokens.color.textMain, fontSize: 14, fontWeight: "500" },
  helper: { color: tokens.color.textMuted, fontSize: 13, lineHeight: 19 },
  legend: { color: tokens.color.textMuted, fontSize: 12, marginTop: tokens.spacing.sm },
  monthArrow: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 10, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  monthNavigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: tokens.spacing.md },
  monthTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "600" },
  moreDates: { color: tokens.color.textMuted, fontSize: 13 },
  noteCount: { color: tokens.color.textMuted, fontSize: 12, textAlign: "right" },
  noteInput: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, color: tokens.color.textMain, minHeight: 96, padding: tokens.spacing.md },
  sectionTitle: { color: tokens.color.textMain, fontSize: 16, fontWeight: "600" },
  selectedDate: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, color: tokens.color.textMain, fontSize: 12, overflow: "hidden", paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  selectedDates: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
});
