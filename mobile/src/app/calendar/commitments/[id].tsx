import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { CalendarDays, ChevronLeft, ChevronRight, MoreHorizontal, Trash2 } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarCommitment, CalendarDayDetailData, CalendarOverviewData } from "@/api/calendar-types";
import { useSession } from "@/auth/session-context";
import { commitmentActionLabel, commitmentDayTitle, commitmentFoodPanelItem, commitmentPresentation, commitmentSupportsFoods } from "@/components/calendarization/calendar-commitments";
import { commitmentDotKinds } from "@/components/calendarization/calendar-commitment-dots";
import { CalendarTodayOutline } from "@/components/calendarization/calendar-today-outline";
import { isCurrentMonthFromToday, monthKeyFromDate, monthLabel, monthWindow, shiftMonth } from "@/components/calendarization/calendar-month";
import { createCalendarMonthCache } from "@/components/calendarization/calendar-month-cache";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { GroupedFoodsCard } from "@/components/panels";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, Card, Chip, InlineNotice, LoadingState, Screen, SectionPageHeader } from "@/components/ui";
import { ConfirmationState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";
import { loadCommitmentReminderSettings, syncCommitmentReminders } from "@/notifications/commitment-reminders";

type CommitmentActionMode = "menu" | "reschedule" | "delete" | null;

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

function headerDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

export default function CalendarCommitmentDetailScreen() {
  const { id, date } = useLocalSearchParams<{ id: string; date: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const monthCache = useMemo(() => createCalendarMonthCache(apiRequest), [apiRequest]);
  const setHeaderPresentation = useHeaderPresentation();
  const [commitment, setCommitment] = useState<CalendarCommitment | null>(null);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingNote, setSavingNote] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionMode, setActionMode] = useState<CommitmentActionMode>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [rescheduleDate, setRescheduleDate] = useState("");
  const [rescheduleMonth, setRescheduleMonth] = useState<string | null>(null);
  const [rescheduleOverview, setRescheduleOverview] = useState<CalendarOverviewData | null>(null);
  const [rescheduleTodaySize, setRescheduleTodaySize] = useState({ width: 0, height: 0 });
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);

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
        setNote(found.note);
        setNotice(null);
        setError(null);
      })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, date, id, status]));

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      action: { icon: "more", label: "Opciones del compromiso", onPress: () => setActionMode("menu") },
      fallback: date ? `/calendar/days/${date}` as Href : "/calendar",
      identityVisible: compactHeaderVisible,
      mode: "back",
      title: commitment ? commitmentActionLabel[commitment.kind] : "Detalle de compromiso",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [commitment, compactHeaderVisible, date, setHeaderPresentation]));

  useEffect(() => {
    if (status !== "authenticated" || actionMode !== "reschedule" || !rescheduleMonth) return;
    let active = true;
    void monthCache.load(rescheduleMonth)
      .then((result) => { if (active) setRescheduleOverview(result); })
      .catch((nextError) => { if (active) setActionError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [actionMode, monthCache, rescheduleMonth, status]);

  const periodSaved = Boolean(commitment?.food_period_start && commitment?.food_period_end);
  const rescheduleMonthDates = useMemo(() => {
    if (!rescheduleMonth) return [];
    const window = monthWindow(rescheduleMonth);
    const first = new Date(`${window.startDate}T12:00:00Z`);
    return Array.from({ length: window.days }, (_, index) => new Date(first.getTime() + index * 86_400_000).toISOString().slice(0, 10));
  }, [rescheduleMonth]);
  const rescheduleDaysByDate = new Map(rescheduleOverview?.start_date === (rescheduleMonth ? monthWindow(rescheduleMonth).startDate : "")
    ? rescheduleOverview.days.map((day) => [day.calendar_date, day] as const) : []);

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

  function openFoodListGenerator() {
    if (!commitment) return;
    router.push(`/calendar/commitments/${commitment.id}/foods?date=${commitment.calendar_date}` as Href);
  }
  function openReschedule() {
    if (!commitment) return;
    setActionError(null);
    setRescheduleDate(commitment.calendar_date);
    setRescheduleMonth(monthKeyFromDate(commitment.calendar_date));
    setActionMode("reschedule");
  }

  function changeRescheduleMonth(delta: number) {
    if (!rescheduleMonth) return;
    const nextMonth = shiftMonth(rescheduleMonth, delta);
    const cached = monthCache.get(nextMonth);
    if (cached) setRescheduleOverview(cached);
    setActionError(null);
    setRescheduleMonth(nextMonth);
  }

  async function refreshCommitmentReminders() {
    try {
      const reminderSettings = await loadCommitmentReminderSettings();
      await syncCommitmentReminders(reminderSettings, apiRequest);
    } catch {
      // A calendar change must remain successful if local notification refresh fails.
    }
  }

  async function rescheduleCommitment() {
    if (!commitment || !rescheduleDate || rescheduleDate === commitment.calendar_date || actionBusy) return;
    setActionBusy(true);
    setActionError(null);
    try {
      const previousDate = commitment.calendar_date;
      const updated = await apiRequest<CalendarCommitment>(`/api/v1/calendar/commitments/${commitment.id}`, {
        method: "PATCH", body: JSON.stringify({ calendar_date: rescheduleDate }),
      });
      monthCache.invalidate([monthKeyFromDate(previousDate), monthKeyFromDate(updated.calendar_date)]);
      setCommitment(updated);
      setActionMode(null);
      void refreshCommitmentReminders();
      router.replace(`/calendar/commitments/${updated.id}?date=${updated.calendar_date}` as Href);
    } catch (nextError) { setActionError(userFacingError(nextError)); }
    finally { setActionBusy(false); }
  }

  async function deleteCommitment() {
    if (!commitment || actionBusy) return;
    setActionBusy(true);
    setActionError(null);
    try {
      await apiRequest<{ deleted_id: number }>(`/api/v1/calendar/commitments/${commitment.id}`, { method: "DELETE" });
      monthCache.invalidate([monthKeyFromDate(commitment.calendar_date)]);
      setActionMode(null);
      void refreshCommitmentReminders();
      router.back();
    } catch (nextError) { setActionError(userFacingError(nextError)); }
    finally { setActionBusy(false); }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !id) return <Redirect href="/calendar" />;
  if (loading) return <LoadingState label="Abriendo compromiso…" />;
  if (!commitment) return <Screen headerMode="preserve"><InlineNotice tone="error">{error ?? "No encontramos este compromiso."}</InlineNotice></Screen>;

  const presentation = commitmentPresentation[commitment.kind];
  const CommitmentIcon = presentation.icon;
  const savedStart = commitment.food_period_start;
  const savedEnd = commitment.food_period_end;
  return <>
  <Screen contentStyle={styles.content} headerMode="preserve" onHeaderVisibilityChange={setCompactHeaderVisible}>
    <SectionPageHeader icon={<CommitmentIcon color={presentation.color} size={28} strokeWidth={1.8} />} section="calendarization" subtitle={headerDate(date)} subtitleStyle={styles.dateSubtitle} title={commitmentActionLabel[commitment.kind]} />
    {commitmentSupportsFoods(commitment.kind) && !periodSaved ? <View style={styles.emptyFoodSection}>
      <InlineNotice tone="info">Aún no tiene una lista de alimentos asociada</InlineNotice>
      <Button label="Generar lista de alimentos" onPress={openFoodListGenerator} />
    </View> : null}
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    {notice === "Nota guardada." ? <InlineNotice tone="info">{notice}</InlineNotice> : null}
    {savedStart && savedEnd ? <View style={styles.associatedFoodSection}>
      <Text accessibilityRole="header" style={styles.foodSectionTitle}>Lista de alimentos asociada</Text>
      <GroupedFoodsCard
        chipsAction={<Button bleed={false} label="Editar periodo" onPress={openFoodListGenerator} variant="secondary" />}
        intro={<Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={`${shortDate(savedStart)} – ${shortDate(savedEnd)}`} textColor={tokens.color.textMain} />}
        items={commitment.foods.map(commitmentFoodPanelItem)}
        onOpenItem={(food) => { if (food.detailId != null) router.push(`/libraries/foods/${food.detailId}` as Href); }}
        preparationFirst={commitment.kind === "shopping"}
        showContents
        summaryChips={<Chip backgroundColor={`${tokens.color.dailyPlan}1A`} borderColor={tokens.color.dailyPlan} label={`${commitment.food_plans_count} ${commitment.food_plans_count === 1 ? "plan" : "planes"}`} textColor={tokens.color.textMain} />}
        title={commitment.kind === "cooking" ? "Alimentos para cocinar" : "Alimentos para comprar"}
      />
    </View> : null}
    <Card>
      <Text style={styles.noteTitle}>Nota (opcional)</Text>
      <TextInput accessibilityLabel="Nota del compromiso" maxLength={500} multiline onChangeText={setNote} placeholder="Agrega una nota para recordar los detalles…" placeholderTextColor={tokens.color.textMuted} style={styles.noteInput} textAlignVertical="top" value={note} />
      <Text style={styles.noteCount}>{note.length}/500</Text>
      {note !== commitment.note ? <Button label="Guardar nota" loading={savingNote} onPress={() => void saveNote()} /> : null}
    </Card>
  </Screen>
  <ActionSheetModal onRequestClose={() => { if (!actionBusy) setActionMode(null); }} visible={actionMode != null}>
    <SafeAreaView edges={["left", "right"]} style={styles.sheet}>
      {actionMode === "menu" ? <>
        <ActionSheetHeader icon={MoreHorizontal} onClose={() => setActionMode(null)} title="Opciones del compromiso" />
        <View style={styles.sheetContent}>
          <ActionSheetActions>
            <ActionSheetAction icon={CalendarDays} label="Recalendarizar compromiso" onPress={openReschedule} />
            <ActionSheetAction destructive icon={Trash2} label="Eliminar compromiso" onPress={() => { setActionError(null); setActionMode("delete"); }} />
          </ActionSheetActions>
        </View>
      </> : null}
      {actionMode === "reschedule" ? <>
        <ActionSheetHeader icon={CalendarDays} onClose={() => setActionMode(null)} title="Recalendarizar compromiso" />
        <View style={styles.sheetContent}>
          <Text style={styles.rescheduleInstruction}>Selecciona la nueva fecha del compromiso.</Text>
          <View style={styles.monthNavigation}>
            <Pressable accessibilityLabel="Mes anterior" accessibilityRole="button" disabled={actionBusy} onPress={() => changeRescheduleMonth(-1)} style={styles.monthArrow}><ChevronLeft color={tokens.color.textMain} size={20} /></Pressable>
            <Text accessibilityRole="header" style={styles.monthTitle}>{rescheduleMonth ? monthLabel(rescheduleMonth) : ""}</Text>
            <Pressable accessibilityLabel="Mes siguiente" accessibilityRole="button" disabled={actionBusy} onPress={() => changeRescheduleMonth(1)} style={styles.monthArrow}><ChevronRight color={tokens.color.textMain} size={20} /></Pressable>
          </View>
          <View style={styles.grid}>
            {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`reschedule-weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
            {rescheduleMonthDates.map((day) => {
              const dayData = rescheduleDaysByDate.get(day);
              const past = Boolean(rescheduleOverview?.local_date && day < rescheduleOverview.local_date);
              const occupied = Boolean(dayData?.commitments?.some((item) => item.kind === commitment.kind && item.id !== commitment.id));
              const disabled = past || occupied || actionBusy;
              const selected = day === rescheduleDate;
              const dots = commitmentDotKinds(dayData?.commitments?.filter((item) => item.id !== commitment.id));
              return <Pressable
                accessibilityLabel={`${shortDate(day)}${day === rescheduleOverview?.local_date ? ", hoy" : ""}${occupied ? "; ya tiene este compromiso" : ""}`}
                accessibilityRole="button"
                accessibilityState={{ disabled, selected }}
                disabled={disabled}
                key={day}
                onLayout={day === rescheduleOverview?.local_date ? ({ nativeEvent: { layout } }) => {
                  setRescheduleTodaySize((current) => current.width === layout.width && current.height === layout.height ? current : { width: layout.width, height: layout.height });
                } : undefined}
                onPress={() => setRescheduleDate(day)}
                style={[styles.gridDate, dayData?.has_plan && styles.gridDateFilled, dayData?.has_plan && isCurrentMonthFromToday(day, rescheduleOverview?.local_date) && styles.gridDateUpcomingFilled, selected && styles.rescheduleDateSelected, disabled && styles.gridDateDisabled, monthKeyFromDate(day) !== rescheduleMonth && styles.gridDateAdjacent, day === rescheduleOverview?.local_date && styles.gridDateToday]}>
                <Text style={[styles.gridNumber, dayData?.has_plan && styles.gridNumberWithPlan, past && styles.gridNumberPast, selected && styles.rescheduleNumberSelected]}>{day.slice(8, 10)}</Text>
                {dots.length ? <View style={[styles.commitmentDots, Boolean(rescheduleOverview?.local_date && day < rescheduleOverview.local_date) && styles.commitmentDotsPast, day === rescheduleOverview?.local_date && styles.commitmentDotsToday]}>{dots.map((kind) => <View key={kind} style={[styles.commitmentDot, { backgroundColor: commitmentPresentation[kind].color }]} />)}</View> : null}
                {day === rescheduleOverview?.local_date ? <CalendarTodayOutline {...rescheduleTodaySize} /> : null}
              </Pressable>;
            })}
          </View>
          {actionError ? <InlineNotice tone="error">{actionError}</InlineNotice> : null}
          <Button disabled={!rescheduleDate || rescheduleDate === commitment.calendar_date || actionBusy} label="Recalendarizar compromiso" loading={actionBusy} onPress={() => void rescheduleCommitment()} />
        </View>
      </> : null}
      {actionMode === "delete" ? <>
        <ActionSheetHeader icon={Trash2} iconColor={tokens.color.danger} onClose={() => setActionMode(null)} title="Eliminar compromiso" />
        <View style={styles.sheetContent}>
          {actionError ? <InlineNotice tone="error">{actionError}</InlineNotice> : null}
          <ConfirmationState
            busy={actionBusy}
            confirmLabel="Eliminar compromiso"
            danger
            message={`Se eliminará ${commitmentDayTitle[commitment.kind].toLowerCase()} del ${shortDate(commitment.calendar_date)}.`}
            onCancel={() => setActionMode("menu")}
            onConfirm={() => void deleteCommitment()}
            title="¿Eliminar este compromiso?"
          />
        </View>
      </> : null}
    </SafeAreaView>
  </ActionSheetModal>
  </>;
}

const styles = StyleSheet.create({
  associatedFoodSection: { gap: tokens.spacing.md },
  content: { gap: tokens.spacing.lg },
  dateSubtitle: { fontSize: 17, fontWeight: "600", lineHeight: 23, marginTop: -4 },
  commitmentDots: { bottom: 4, flexDirection: "row", gap: 2, position: "absolute" },
  commitmentDotsPast: { opacity: 0.5 },
  commitmentDotsToday: { bottom: 6 },
  commitmentDot: { borderRadius: 3, height: 5, width: 5 },
  emptyFoodSection: { gap: tokens.spacing.md },
  foodSectionTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: tokens.weight.extraBold },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: tokens.spacing.sm },
  gridDate: { alignItems: "center", borderColor: "transparent", borderRadius: 10, borderWidth: 2, justifyContent: "center", minHeight: 40, width: "13.5%" },
  gridDateToday: { borderWidth: 0 },
  gridDateAdjacent: { opacity: 0.5 },
  gridDateDisabled: { opacity: 0.32 },
  gridDateFilled: { backgroundColor: `${tokens.color.dailyPlan}2E` },
  gridDateUpcomingFilled: { backgroundColor: `${tokens.color.dailyPlan}59` },
  gridHeader: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center", width: "13.5%" },
  gridNumber: { color: tokens.color.textMain, fontSize: 14, fontWeight: "500" },
  gridNumberPast: { opacity: 0.8 },
  gridNumberWithPlan: { color: tokens.color.textMain, fontWeight: "700" },
  monthArrow: { alignItems: "center", height: 36, justifyContent: "center", width: 36 },
  monthNavigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: tokens.spacing.md },
  monthTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "600" },
  noteCount: { color: tokens.color.textMuted, fontSize: 12, textAlign: "right" },
  noteInput: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, color: tokens.color.textMain, minHeight: 96, padding: tokens.spacing.md },
  noteTitle: { color: tokens.color.textMain, fontSize: 16, fontWeight: "600" },
  rescheduleDateSelected: { backgroundColor: `${tokens.color.interactivePrimary}26`, borderColor: tokens.color.interactivePrimary },
  rescheduleInstruction: { color: tokens.color.textMain, fontSize: 15, fontWeight: "600" },
  rescheduleNumberSelected: { color: tokens.color.interactivePrimary, fontWeight: "700" },
  sheet: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  sheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
});
