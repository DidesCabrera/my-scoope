import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronLeft, ChevronRight } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarCommitment, CalendarDayDetailData, CalendarOverviewData } from "@/api/calendar-types";
import { useSession } from "@/auth/session-context";
import { commitmentDayTitle, commitmentFoodPanelItem, commitmentPresentation, commitmentSupportsFoods } from "@/components/calendarization/calendar-commitments";
import { commitmentDotKinds } from "@/components/calendarization/calendar-commitment-dots";
import { calendarFoodDayRole, selectCalendarFoodDate, validCalendarFoodPeriod } from "@/components/calendarization/calendar-food-period";
import { monthKeyFromDate, monthLabel, monthWindow, shiftMonth } from "@/components/calendarization/calendar-month";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { GroupedFoodsCard } from "@/components/panels";
import { Button, Card, Chip, InlineNotice, LoadingState, Screen, SectionPageHeader } from "@/components/ui";
import { tokens } from "@/design/tokens";

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

export default function CalendarCommitmentDetailScreen() {
  const { id, date } = useLocalSearchParams<{ id: string; date: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [commitment, setCommitment] = useState<CalendarCommitment | null>(null);
  const [month, setMonth] = useState<string | null>(null);
  const [monthOverview, setMonthOverview] = useState<CalendarOverviewData | null>(null);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingPeriod, setSavingPeriod] = useState(false);
  const [editingPeriod, setEditingPeriod] = useState(false);
  const [savingNote, setSavingNote] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated" || !date || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !id) return;
    let active = true;
    setLoading(true);
    void apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${date}`)
      .then((day) => {
        if (!active) return;
        const found = day.commitments?.find((item) => item.id === Number(id)) ?? null;
        setCommitment(found);
        if (!found) { setError("Este compromiso ya no está registrado en esta fecha."); return; }
        setStart(found.food_period_start ?? "");
        setEnd(found.food_period_end ?? "");
        setNote(found.note);
        setMonth(monthKeyFromDate(found.food_period_start ?? date));
        setEditingPeriod(false);
        setError(null);
      })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, date, id, status]));

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: date ? `/calendar/days/${date}` as Href : "/calendar", mode: "back", title: commitment ? commitmentDayTitle[commitment.kind] : "Detalle de compromiso" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [commitment, date, setHeaderPresentation]));

  useEffect(() => {
    if (status !== "authenticated" || !month) return;
    let active = true;
    const window = monthWindow(month);
    void apiRequest<CalendarOverviewData>(`/api/v1/calendar?start_date=${window.startDate}&days=${window.days}`)
      .then((result) => { if (active) setMonthOverview(result); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [apiRequest, month, status]);

  const monthDates = useMemo(() => {
    if (!month) return [];
    const window = monthWindow(month);
    const first = new Date(`${window.startDate}T12:00:00Z`);
    return Array.from({ length: window.days }, (_, index) => new Date(first.getTime() + index * 86_400_000).toISOString().slice(0, 10));
  }, [month]);
  const monthDaysByDate = new Map(monthOverview?.start_date === (month ? monthWindow(month).startDate : "")
    ? monthOverview.days.map((day) => [day.calendar_date, day] as const) : []);
  const periodSaved = Boolean(commitment?.food_period_start && commitment?.food_period_end);

  async function savePeriod(nextStart: string, nextEnd: string) {
    if (!commitment || savingPeriod) return;
    setSavingPeriod(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await apiRequest<CalendarCommitment>(`/api/v1/calendar/commitments/${commitment.id}`, {
        method: "PATCH", body: JSON.stringify({ update_food_period: true, food_period_start: nextStart || null, food_period_end: nextEnd || null }),
      });
      setCommitment(updated);
      setStart(updated.food_period_start ?? "");
      setEnd(updated.food_period_end ?? "");
      setEditingPeriod(false);
      setNotice(nextStart ? "Lista guardada en este compromiso." : "Lista quitada de este compromiso.");
    } catch (nextError) { setError(userFacingError(nextError)); }
    finally { setSavingPeriod(false); }
  }

  async function saveNote() {
    if (!commitment || savingNote) return;
    setSavingNote(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await apiRequest<CalendarCommitment>(`/api/v1/calendar/commitments/${commitment.id}`, {
        method: "PATCH", body: JSON.stringify({ note }),
      });
      setCommitment(updated);
      setNote(updated.note);
      setNotice("Nota guardada.");
    } catch (nextError) { setError(userFacingError(nextError)); }
    finally { setSavingNote(false); }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !id) return <Redirect href="/calendar" />;
  if (loading) return <LoadingState label="Abriendo compromiso…" />;
  if (!commitment) return <Screen headerMode="preserve"><InlineNotice tone="error">{error ?? "No encontramos este compromiso."}</InlineNotice></Screen>;

  const presentation = commitmentPresentation[commitment.kind];
  const CommitmentIcon = presentation.icon;
  const savedStart = commitment.food_period_start;
  const savedEnd = commitment.food_period_end;
  const controlsLocked = savingPeriod || periodSaved && !editingPeriod;
  return <Screen contentStyle={styles.content} headerMode="preserve">
    <SectionPageHeader icon={<CommitmentIcon color={presentation.color} size={28} strokeWidth={1.8} />} indicator={<Chip backgroundColor={tokens.color.surfaceMuted} borderColor={tokens.color.borderDefault} label={shortDate(date)} textColor={tokens.color.textMain} />} section="calendarization" title={commitmentDayTitle[commitment.kind]} />
    {commitmentSupportsFoods(commitment.kind) ? <View style={styles.foodPeriodControls}>
      <Text style={styles.foodInstruction}>Selecciona una fecha de inicio y de término.</Text>
      <View style={styles.monthNavigation}>
        <Pressable accessibilityLabel="Mes anterior del periodo" accessibilityRole="button" accessibilityState={{ disabled: controlsLocked }} disabled={controlsLocked} onPress={() => { if (month) setMonth(shiftMonth(month, -1)); }} style={styles.monthArrow}><ChevronLeft color={tokens.color.textMain} size={20} /></Pressable>
        <Text accessibilityRole="header" style={styles.monthTitle}>{month ? monthLabel(month) : ""}</Text>
        <Pressable accessibilityLabel="Mes siguiente del periodo" accessibilityRole="button" accessibilityState={{ disabled: controlsLocked }} disabled={controlsLocked} onPress={() => { if (month) setMonth(shiftMonth(month, 1)); }} style={styles.monthArrow}><ChevronRight color={tokens.color.textMain} size={20} /></Pressable>
      </View>
      <View style={styles.grid}>
        {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
        {monthDates.map((day) => {
          const role = calendarFoodDayRole(day, start, end);
          const endpoint = role === "start" || role === "end" || role === "single";
          const dayData = monthDaysByDate.get(day);
          const shoppingDate = commitment.kind === "shopping" && day === date;
          const dots = commitmentDotKinds(dayData?.commitments, shoppingDate ? "shopping" : undefined);
          const accent = tokens.color.food;
          return <Pressable
            accessibilityLabel={`${shortDate(day)}: ${shoppingDate ? "día para hacer compras, " : ""}${role === "single" ? "inicio y término" : role === "start" ? "inicio" : role === "end" ? "término" : role === "between" ? "dentro del periodo" : "fuera del periodo"}${dayData?.commitments?.length ? `; ${dayData.commitments.map((item) => commitmentPresentation[item.kind].label).join(", ")}` : ""}`}
            accessibilityRole="button" accessibilityState={{ disabled: controlsLocked }} disabled={controlsLocked} key={day}
            onPress={() => {
              const next = selectCalendarFoodDate(start, end, day);
              if (next.tooLong) { setError("Elige un periodo de hasta 366 días."); return; }
              setStart(next.start); setEnd(next.end); setError(null);
            }}
            style={[styles.gridDate, endpoint && { backgroundColor: `${accent}26`, borderColor: accent }, role === "between" && { backgroundColor: `${accent}33` }, monthKeyFromDate(day) !== month && styles.gridDateAdjacent]}>
            <Text style={[styles.gridNumber, dayData?.has_plan && styles.gridNumberWithPlan, endpoint && { color: accent, fontWeight: "700" }, role === "between" && { color: accent }]}>{day.slice(8, 10)}</Text>
            {dots.length ? <View style={styles.commitmentDots}>{dots.map((kind) => <View key={kind} style={[styles.commitmentDot, { backgroundColor: commitmentPresentation[kind].color }]} />)}</View> : null}
          </Pressable>;
        })}
      </View>
      <View style={styles.foodPeriodAction}>
        {periodSaved && !editingPeriod ? <>
          <Button label="Editar periodo" onPress={() => setEditingPeriod(true)} variant="secondary" />
          <Button label="Limpiar selección" loading={savingPeriod} onPress={() => void savePeriod("", "")} variant="secondary" />
        </> : <Button disabled={!validCalendarFoodPeriod(start, end) || savingPeriod} label="Calcular lista de alimentos" loading={savingPeriod} onPress={() => void savePeriod(start, end)} />}
      </View>
    </View> : null}
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    {notice ? <InlineNotice tone="info">{notice}</InlineNotice> : null}
    {savedStart && savedEnd ? <GroupedFoodsCard
      intro={<Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={`${shortDate(savedStart)} – ${shortDate(savedEnd)}`} textColor={tokens.color.textMain} />}
      items={commitment.foods.map(commitmentFoodPanelItem)}
      onOpenItem={(food) => { if (food.detailId != null) router.push(`/libraries/foods/${food.detailId}` as Href); }}
      preparationFirst={commitment.kind === "shopping"}
      showContents
      summaryChips={<Chip backgroundColor={`${tokens.color.dailyPlan}1A`} borderColor={tokens.color.dailyPlan} label={`${commitment.food_plans_count} ${commitment.food_plans_count === 1 ? "plan" : "planes"}`} textColor={tokens.color.textMain} />}
      title={commitment.kind === "cooking" ? "Alimentos para cocinar" : "Alimentos para comprar"}
    /> : null}
    <Card>
      <Text style={styles.noteTitle}>Nota (opcional)</Text>
      <TextInput accessibilityLabel="Nota del compromiso" maxLength={500} multiline onChangeText={setNote} placeholder="Agrega una nota para recordar los detalles…" placeholderTextColor={tokens.color.textMuted} style={styles.noteInput} textAlignVertical="top" value={note} />
      <Text style={styles.noteCount}>{note.length}/500</Text>
      {note !== commitment.note ? <Button label="Guardar nota" loading={savingNote} onPress={() => void saveNote()} /> : null}
    </Card>
  </Screen>;
}

const styles = StyleSheet.create({
  content: { gap: tokens.spacing.lg },
  commitmentDots: { bottom: 3, flexDirection: "row", gap: 2, position: "absolute" },
  commitmentDot: { borderRadius: 3, height: 5, width: 5 },
  foodInstruction: { color: tokens.color.textMain, fontSize: 16, fontWeight: "700", lineHeight: 23 },
  foodPeriodAction: { gap: tokens.spacing.sm, marginTop: 30 - tokens.spacing.md },
  foodPeriodControls: { gap: tokens.spacing.md, marginBottom: 42 - tokens.spacing.lg },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: tokens.spacing.sm },
  gridDate: { alignItems: "center", borderColor: "transparent", borderRadius: 10, borderWidth: 2, justifyContent: "center", minHeight: 40, width: "13.5%" },
  gridDateAdjacent: { opacity: 0.5 },
  gridHeader: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center", width: "13.5%" },
  gridNumber: { color: tokens.color.textMain, fontSize: 14, fontWeight: "500" },
  gridNumberWithPlan: { color: tokens.color.dailyPlan, fontWeight: "700" },
  monthArrow: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 10, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  monthNavigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: tokens.spacing.md },
  monthTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "600" },
  noteCount: { color: tokens.color.textMuted, fontSize: 12, textAlign: "right" },
  noteInput: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, color: tokens.color.textMain, minHeight: 96, padding: tokens.spacing.md },
  noteTitle: { color: tokens.color.textMain, fontSize: 16, fontWeight: "600" },
});
