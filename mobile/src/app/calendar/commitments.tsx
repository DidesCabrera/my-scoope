import { type Href, Redirect, useFocusEffect, useLocalSearchParams, usePathname, useRouter } from "expo-router";
import { ChevronLeft, ChevronRight, Paperclip } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BackHandler, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarCommitment, CalendarCommitmentKind, CalendarOverviewData, CalendarPeriodFoodsData } from "@/api/calendar-types";
import { useSession } from "@/auth/session-context";
import { commitmentDayTitle, commitmentFoodPanelItem, commitmentPresentation, commitmentRegistrationTitle, commitmentSupportsFoods } from "@/components/calendarization/calendar-commitments";
import { commitmentDotKinds } from "@/components/calendarization/calendar-commitment-dots";
import { CalendarMonthPlaceholder } from "@/components/calendarization/calendar-month-calendar";
import { calendarFoodDayRole, calendarFoodPeriodDayCount, selectCalendarFoodDate, validCalendarFoodPeriod } from "@/components/calendarization/calendar-food-period";
import { monthKeyFromDate, monthLabel, monthWindow, shiftMonth } from "@/components/calendarization/calendar-month";
import { createCalendarMonthCache } from "@/components/calendarization/calendar-month-cache";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { GroupedFoodsCard } from "@/components/panels";
import { PickerCardAction } from "@/components/pickers/picker-card-action";
import { Button, Card, InlineNotice, LoadingState, Screen, SectionPageHeader } from "@/components/ui";
import { Chip } from "@/components/ui/chip";
import { tokens } from "@/design/tokens";
import { loadCommitmentReminderSettings, syncCommitmentReminders } from "@/notifications/commitment-reminders";

function isCommitmentKind(value: string | undefined): value is CalendarCommitmentKind {
  return value === "shopping" || value === "cooking" || value === "training" || value === "nutritionist";
}

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" })
    .format(new Date(`${value}T12:00:00`));
}

function CommitmentDots({ commitments, draftKind }: { commitments?: CalendarCommitment[]; draftKind?: CalendarCommitmentKind }) {
  const kinds = commitmentDotKinds(commitments, draftKind);
  if (!kinds.length) return null;
  return <View style={styles.commitmentDots}>{kinds.map((commitmentKind) => <View key={commitmentKind} style={[styles.commitmentDot, { backgroundColor: commitmentPresentation[commitmentKind].color }]} />)}</View>;
}

type FoodAttachment = { start: string; end: string };

export default function RegisterCommitmentsScreen() {
  const router = useRouter();
  const pathname = usePathname();
  const { date: requestedDate, kind: requestedKind } = useLocalSearchParams<{ date?: string; kind?: string }>();
  const kind = isCommitmentKind(requestedKind) ? requestedKind : null;
  const initialDate = requestedDate && /^\d{4}-\d{2}-\d{2}$/.test(requestedDate) ? requestedDate : null;
  const setHeaderPresentation = useHeaderPresentation();
  const { apiRequest, status } = useSession();
  const monthCache = useMemo(() => createCalendarMonthCache(apiRequest), [apiRequest]);
  const [localToday, setLocalToday] = useState<string | null>(null);
  const [visibleMonth, setVisibleMonth] = useState<string | null>(null);
  const [monthOverview, setMonthOverview] = useState<CalendarOverviewData | null>(null);
  const [foodMonthOverview, setFoodMonthOverview] = useState<{ key: string; days: CalendarOverviewData["days"] } | null>(null);
  const [selectedDates, setSelectedDates] = useState<string[]>([]);
  const [foodAttachments, setFoodAttachments] = useState<Record<string, FoodAttachment>>({});
  const [editingFoodDate, setEditingFoodDate] = useState<string | null>(null);
  const [notesByDate, setNotesByDate] = useState<Record<string, string>>({});
  const [foodStartDate, setFoodStartDate] = useState("");
  const [foodEndDate, setFoodEndDate] = useState("");
  const [foodMonth, setFoodMonth] = useState<string | null>(null);
  const [foodPreview, setFoodPreview] = useState<CalendarPeriodFoodsData | null>(null);
  const [calculatedFoodsByDate, setCalculatedFoodsByDate] = useState<Record<string, CalendarPeriodFoodsData>>({});
  const [serverSupportsPerDateLists, setServerSupportsPerDateLists] = useState<boolean | null>(null);
  const [foodLoading, setFoodLoading] = useState(false);
  const [foodError, setFoodError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const foodRequestSequence = useRef(0);

  const closeFoodEditor = useCallback(() => {
    foodRequestSequence.current += 1;
    setFoodLoading(false);
    setEditingFoodDate(null);
  }, []);

  useEffect(() => {
    if (status !== "authenticated" || !kind) return;
    let active = true;
    void apiRequest<CalendarOverviewData>("/api/v1/calendar?days=1")
      .then((result) => {
        if (!active) return;
        setLocalToday(result.local_date);
        setVisibleMonth(monthKeyFromDate(initialDate ?? result.local_date));
        setFoodMonth(monthKeyFromDate(result.local_date));
        if (initialDate) setSelectedDates((current) => current.length ? current : [initialDate]);
      })
      .catch((nextError) => { if (active) { setError(userFacingError(nextError)); setLoading(false); } });
    return () => { active = false; };
  }, [apiRequest, initialDate, kind, status]);

  useEffect(() => {
    if (status !== "authenticated" || !visibleMonth) return;
    let active = true;
    void monthCache.load(visibleMonth)
      .then((result) => { if (active) { setMonthOverview(result); monthCache.prefetchAdjacent(visibleMonth); } })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [monthCache, status, visibleMonth]);

  useEffect(() => {
    if (status !== "authenticated" || !editingFoodDate || !foodMonth || foodMonth === visibleMonth && monthOverview?.start_date === monthWindow(foodMonth).startDate) return;
    let active = true;
    const window = monthWindow(foodMonth);
    void apiRequest<CalendarOverviewData>(`/api/v1/calendar?start_date=${window.startDate}&days=${window.days}`)
      .then((result) => { if (active) setFoodMonthOverview({ key: foodMonth, days: result.days }); })
      .catch((nextError) => { if (active) setFoodError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [apiRequest, editingFoodDate, foodMonth, monthOverview, status, visibleMonth]);

  useEffect(() => {
    if (!editingFoodDate) return;
    const subscription = BackHandler.addEventListener("hardwareBackPress", () => {
      closeFoodEditor();
      return true;
    });
    return () => subscription.remove();
  }, [closeFoodEditor, editingFoodDate]);

  const presentHeader = useCallback(() => {
    setHeaderPresentation({
      fallback: "/calendar",
      leadingAction: editingFoodDate ? { icon: "back", label: "Volver a las fechas", onPress: closeFoodEditor } : undefined,
      mode: "back",
      title: editingFoodDate && kind ? commitmentDayTitle[kind] : "Registrar compromisos",
    });
  }, [closeFoodEditor, editingFoodDate, kind, setHeaderPresentation]);

  useEffect(() => {
    if (!pathname.startsWith("/calendar/commitments")) return;
    presentHeader();
  }, [pathname, presentHeader]);
  useFocusEffect(useCallback(() => {
    presentHeader();
    return () => setHeaderPresentation({ mode: "default" });
  }, [presentHeader, setHeaderPresentation]));

  const selected = useMemo(() => [...selectedDates].sort(), [selectedDates]);
  const foodMonthDates = useMemo(() => {
    if (!foodMonth) return [];
    const window = monthWindow(foodMonth);
    const first = new Date(`${window.startDate}T12:00:00Z`);
    return Array.from({ length: window.days }, (_, index) =>
      new Date(first.getTime() + index * 86_400_000).toISOString().slice(0, 10));
  }, [foodMonth]);
  const foodMonthDays = foodMonth === visibleMonth && monthOverview?.start_date === (foodMonth ? monthWindow(foodMonth).startDate : "")
    ? monthOverview.days
    : foodMonthOverview?.key === foodMonth ? foodMonthOverview.days : [];
  const foodDaysByDate = new Map(foodMonthDays.map((day) => [day.calendar_date, day]));
  const foodRangeLocked = foodLoading || Boolean(foodPreview);
  const hasFoodAttachments = selected.some((day) => Boolean(foodAttachments[day]));
  if (status === "anonymous") return <Redirect href="/login" />;
  if (!kind) return <Redirect href={"/calendar" as Href} />;
  const presentation = commitmentPresentation[kind];
  const CommitmentIcon = presentation.icon;
  const pageIcon = <CommitmentIcon color={presentation.color} size={28} strokeWidth={1.8} />;

  function changeFoodPeriod(start: string, end: string) {
    setFoodStartDate(start);
    setFoodEndDate(end);
    setFoodPreview(null);
    setFoodError(null);
    setFoodLoading(false);
  }

  function chooseFoodDate(day: string) {
    const next = selectCalendarFoodDate(foodStartDate, foodEndDate, day);
    if (next.tooLong) {
      setFoodError("Elige un periodo de hasta 366 días.");
      return;
    }
    changeFoodPeriod(next.start, next.end);
    if (foodMonth && monthKeyFromDate(day) !== foodMonth) setFoodMonth(monthKeyFromDate(day));
  }

  function openFoodEditor(day: string) {
    foodRequestSequence.current += 1;
    const attachment = foodAttachments[day];
    setEditingFoodDate(day);
    setFoodStartDate(attachment?.start ?? "");
    setFoodEndDate(attachment?.end ?? "");
    setFoodPreview(calculatedFoodsByDate[day] ?? null);
    setFoodError(null);
    setFoodLoading(false);
    setFoodMonth(monthKeyFromDate(attachment?.start ?? day));
  }

  async function calculateFoodList() {
    if (!editingFoodDate || !validCalendarFoodPeriod(foodStartDate, foodEndDate) || foodLoading) return;
    const day = editingFoodDate;
    const start = foodStartDate;
    const end = foodEndDate;
    const requestSequence = ++foodRequestSequence.current;
    setFoodLoading(true);
    setFoodError(null);
    try {
      const result = await apiRequest<CalendarPeriodFoodsData>(`/api/v1/calendar/foods?start_date=${start}&end_date=${end}`);
      if (foodRequestSequence.current !== requestSequence) return;
      if (typeof result.meals_count !== "number") {
        setServerSupportsPerDateLists(false);
        setFoodError("El servidor seleccionado aún no permite guardar una lista distinta para cada fecha.");
        return;
      }
      setServerSupportsPerDateLists(true);
      setFoodPreview(result);
      setCalculatedFoodsByDate((current) => ({ ...current, [day]: result }));
      setFoodAttachments((current) => ({ ...current, [day]: { start, end } }));
    } catch (nextError) {
      if (foodRequestSequence.current === requestSequence) setFoodError(userFacingError(nextError));
    } finally {
      if (foodRequestSequence.current === requestSequence) setFoodLoading(false);
    }
  }

  function clearFoodSelection() {
    if (!editingFoodDate || foodLoading) return;
    foodRequestSequence.current += 1;
    const day = editingFoodDate;
    setFoodAttachments((current) => {
      const next = { ...current };
      delete next[day];
      return next;
    });
    setCalculatedFoodsByDate((current) => {
      const next = { ...current };
      delete next[day];
      return next;
    });
    changeFoodPeriod("", "");
  }

  function toggleDate(date: string) {
    if (!localToday || date < localToday) return;
    if (selectedDates.includes(date)) {
      setSelectedDates((current) => current.filter((item) => item !== date));
      setFoodAttachments((current) => {
        const next = { ...current };
        delete next[date];
        return next;
      });
      setCalculatedFoodsByDate((current) => {
        const next = { ...current };
        delete next[date];
        return next;
      });
      setNotesByDate((current) => {
        const next = { ...current };
        delete next[date];
        return next;
      });
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
    const nextMonth = shiftMonth(visibleMonth, delta);
    const cached = monthCache.get(nextMonth);
    setLoading(!cached);
    setError(null);
    if (cached) setMonthOverview(cached);
    setVisibleMonth(nextMonth);
  }

  async function register() {
    if (!selected.length || hasFoodAttachments && serverSupportsPerDateLists !== true) return;
    setSaving(true);
    setError(null);
    try {
      await apiRequest<{ items: CalendarCommitment[] }>("/api/v1/calendar/commitments", {
        method: "POST",
        body: JSON.stringify({
          kind, dates: selected,
          notes_by_date: selected.map((day) => ({ calendar_date: day, note: (notesByDate[day] ?? "").trim() })),
          food_attachments: selected.flatMap((day) => foodAttachments[day]
            ? [{ calendar_date: day, food_period_start: foodAttachments[day].start, food_period_end: foodAttachments[day].end }]
            : []),
        }),
      });
      monthCache.invalidate(new Set(selected.map(monthKeyFromDate)));
      void loadCommitmentReminderSettings().then((reminderSettings) => syncCommitmentReminders(reminderSettings, apiRequest)).catch(() => undefined);
      router.replace("/calendar/registry" as Href);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  }

  if (editingFoodDate) return <Screen contentStyle={styles.content} headerMode="preserve" key={`commitment-detail-${editingFoodDate}`}>
    <SectionPageHeader icon={pageIcon} indicator={<Chip backgroundColor={tokens.color.surfaceMuted} borderColor={tokens.color.borderDefault} label={shortDate(editingFoodDate)} textColor={tokens.color.textMain} />} section="calendarization" title={commitmentDayTitle[kind]} />
    {commitmentSupportsFoods(kind) ? <View style={styles.foodPeriodControls}>
          <Text style={styles.foodInstruction}>Selecciona una fecha de inicio y de término.</Text>
          <View style={styles.monthNavigation}>
            <Pressable accessibilityLabel="Mes anterior del periodo" accessibilityRole="button" accessibilityState={{ disabled: foodRangeLocked }} disabled={foodRangeLocked} onPress={() => { if (foodMonth) setFoodMonth(shiftMonth(foodMonth, -1)); }} style={styles.monthArrow}>
              <ChevronLeft color={tokens.color.textMain} size={20} />
            </Pressable>
            <Text accessibilityRole="header" style={styles.monthTitle}>{foodMonth ? monthLabel(foodMonth) : ""}</Text>
            <Pressable accessibilityLabel="Mes siguiente del periodo" accessibilityRole="button" accessibilityState={{ disabled: foodRangeLocked }} disabled={foodRangeLocked} onPress={() => { if (foodMonth) setFoodMonth(shiftMonth(foodMonth, 1)); }} style={styles.monthArrow}>
              <ChevronRight color={tokens.color.textMain} size={20} />
            </Pressable>
          </View>
          <View style={styles.grid}>
            {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`food-weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
            {foodMonthDates.map((day) => {
              const role = calendarFoodDayRole(day, foodStartDate, foodEndDate);
              const endpoint = role === "start" || role === "end" || role === "single";
              const shoppingDate = kind === "shopping" && day === editingFoodDate;
              const dayData = foodDaysByDate.get(day);
              const dayCommitments = dayData?.commitments;
              const accent = tokens.color.food;
              return <Pressable
                accessibilityLabel={`${shortDate(day)}: ${shoppingDate ? "día para hacer compras, " : ""}${role === "single" ? "inicio y término" : role === "start" ? "inicio" : role === "end" ? "término" : role === "between" ? "dentro del periodo" : "fuera del periodo"}${dayCommitments?.length ? `; ${dayCommitments.map((item) => commitmentPresentation[item.kind].label).join(", ")}` : ""}`}
                accessibilityRole="button"
                accessibilityState={{ disabled: foodRangeLocked }}
                disabled={foodRangeLocked}
                key={`food-${day}`}
                onPress={() => chooseFoodDate(day)}
                style={[styles.gridDate, dayData?.has_plan && styles.gridDateFilled, endpoint && { backgroundColor: `${accent}26`, borderColor: accent }, role === "between" && { backgroundColor: `${accent}33` }, monthKeyFromDate(day) !== foodMonth && styles.gridDateAdjacent]}>
                <Text style={[styles.gridNumber, dayData?.has_plan && styles.gridNumberWithPlan, endpoint && { color: accent, fontWeight: "700" }, role === "between" && { color: accent }]}>{day.slice(8, 10)}</Text>
                <CommitmentDots commitments={dayCommitments} draftKind={shoppingDate ? "shopping" : undefined} />
              </Pressable>;
            })}
          </View>
          <View style={styles.foodPeriodAction}>
            {foodPreview ? <Button label="Limpiar selección" onPress={clearFoodSelection} variant="secondary" />
              : <Button disabled={!validCalendarFoodPeriod(foodStartDate, foodEndDate) || foodLoading} label="Calcular lista de alimentos" loading={foodLoading} onPress={() => void calculateFoodList()} />}
          </View>
      </View> : null}
    {commitmentSupportsFoods(kind) && foodError ? <InlineNotice tone="error">{foodError}</InlineNotice> : null}
    {commitmentSupportsFoods(kind) && foodLoading ? <LoadingState label="Calculando alimentos…" /> : null}
    {commitmentSupportsFoods(kind) && foodPreview ? <GroupedFoodsCard
      intro={<Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={`${shortDate(foodStartDate)} – ${shortDate(foodEndDate)}`} textColor={tokens.color.textMain} />}
      items={foodPreview?.foods.map(commitmentFoodPanelItem) ?? []}
      key={`${editingFoodDate}:${foodStartDate}:${foodEndDate}`}
      onOpenItem={(food) => { if (food.detailId != null) router.push(`/libraries/foods/${food.detailId}` as Href); }}
      preparationFirst={kind === "shopping"}
      showContents={Boolean(foodPreview)}
      summaryChips={foodPreview && typeof foodPreview.meals_count === "number" ? <>
        <Chip backgroundColor={`${tokens.color.dailyPlan}1A`} borderColor={tokens.color.dailyPlan} label={`${foodPreview.plans_count} ${foodPreview.plans_count === 1 ? "plan" : "planes"}`} textColor={tokens.color.textMain} />
        <Chip backgroundColor={`${tokens.color.meal}1A`} borderColor={tokens.color.meal} label={`${foodPreview.meals_count} ${foodPreview.meals_count === 1 ? "comida" : "comidas"}`} textColor={tokens.color.textMain} />
      </> : null}
      title={kind === "cooking" ? "Alimentos para cocinar" : "Alimentos para comprar"}
    /> : null}
    <Card>
      <Text style={styles.sectionTitle}>Nota (opcional)</Text>
      <TextInput accessibilityLabel={`Nota de ${kind === "nutritionist" ? "la cita nutricionista" : `el ${commitmentDayTitle[kind].toLowerCase()}`} del ${shortDate(editingFoodDate)}`} maxLength={500} multiline onChangeText={(value) => setNotesByDate((current) => ({ ...current, [editingFoodDate]: value }))} placeholder="Agrega una nota para recordar los detalles…" placeholderTextColor={tokens.color.textMuted} style={styles.noteInput} textAlignVertical="top" value={notesByDate[editingFoodDate] ?? ""} />
      <Text style={styles.noteCount}>{(notesByDate[editingFoodDate] ?? "").length}/500</Text>
    </Card>
  </Screen>;

  return <Screen contentStyle={styles.content} headerMode="preserve" key="commitment-registration">
    <SectionPageHeader countLabel="fechas" icon={pageIcon} section="calendarization" subtitle="Marca varios días; puedes cambiar de mes sin perder tu selección." title={commitmentRegistrationTitle[kind]} />
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    <View style={styles.calendarSection}>
      <View style={styles.monthNavigation}>
        <Pressable accessibilityLabel="Mes anterior" accessibilityRole="button" accessibilityState={{ disabled: !visibleMonth || !localToday || visibleMonth <= monthKeyFromDate(localToday) }} disabled={!visibleMonth || !localToday || visibleMonth <= monthKeyFromDate(localToday)} onPress={() => changeMonth(-1)} style={styles.monthArrow}>
          <ChevronLeft color={tokens.color.textMain} size={20} />
        </Pressable>
        <Text accessibilityRole="header" style={styles.monthTitle}>{visibleMonth ? monthLabel(visibleMonth) : ""}</Text>
        <Pressable accessibilityLabel="Mes siguiente" accessibilityRole="button" onPress={() => changeMonth(1)} style={styles.monthArrow}>
          <ChevronRight color={tokens.color.textMain} size={20} />
        </Pressable>
      </View>
      {loading ? <CalendarMonthPlaceholder /> : <View style={styles.grid}>
        {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
        {monthOverview?.days.map((day) => {
          const exists = day.commitments?.some((item) => item.kind === kind) ?? false;
          const isPast = Boolean(localToday && day.calendar_date < localToday);
          const isSelected = selectedDates.includes(day.calendar_date);
          return <Pressable
            accessibilityLabel={`${shortDate(day.calendar_date)}: ${exists ? "ya registrado" : isSelected ? "seleccionado" : isPast ? "fecha anterior" : "sin seleccionar"}${day.commitments?.length ? `; ${day.commitments.map((item) => commitmentPresentation[item.kind].label).join(", ")}` : ""}`}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: isSelected || exists, disabled: isPast || exists }}
            disabled={isPast || exists}
            key={day.calendar_date}
            onPress={() => toggleDate(day.calendar_date)}
            style={[styles.gridDate, day.has_plan && styles.gridDateFilled, isSelected && { backgroundColor: `${presentation.color}33`, borderColor: presentation.color }, exists && styles.gridDateExisting, monthKeyFromDate(day.calendar_date) !== visibleMonth && styles.gridDateAdjacent, isPast && styles.gridDatePast]}>
            <Text style={[styles.gridNumber, day.has_plan && styles.gridNumberWithPlan, (isSelected || exists) && { color: presentation.color }]}>{day.calendar_date.slice(8, 10)}</Text>
            <CommitmentDots commitments={day.commitments} />
          </Pressable>;
        })}
      </View>}
      <Text style={styles.legend}>Los días con un punto ya tienen este compromiso registrado.</Text>
    </View>
    <View style={styles.selectedDatesSection}>
      <Text style={styles.sectionTitle}>Días comprometidos · {selected.length}</Text>
      {selected.length ? selected.map((date) => <View key={date} style={[styles.selectedDateCard, { borderTopColor: presentation.color }]}>
        <Pressable accessibilityLabel={`Ver detalle: ${commitmentDayTitle[kind]} del ${shortDate(date)}`} accessibilityRole="button" onPress={() => openFoodEditor(date)} style={styles.selectedDateContent}>
        <View style={styles.selectedDateEyebrow}>
          {foodAttachments[date] ? <Paperclip accessibilityLabel="Lista de alimentos adjunta" color={tokens.color.textSoft} size={16} strokeWidth={2} /> : null}
          <View style={[styles.selectedDateIcon, { backgroundColor: presentation.color }]}><CommitmentIcon color={tokens.color.entityIconForeground} size={13} strokeWidth={2.3} /></View>
          <Text style={styles.selectedDateEyebrowText}>{commitmentDayTitle[kind].toUpperCase()}</Text>
        </View>
        <Text style={styles.selectedDateTitle}>{shortDate(date)}</Text>
        {commitmentSupportsFoods(kind) ? <Text style={styles.helper}>{foodAttachments[date]
          ? `Lista: ${shortDate(foodAttachments[date].start)} – ${shortDate(foodAttachments[date].end)}`
          : "Sin lista de alimentos adjunta"}</Text> : null}
        {foodAttachments[date] && calculatedFoodsByDate[date] ? <View style={styles.selectedDateChips}>
          <Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={`${calculatedFoodsByDate[date].foods.length} ${calculatedFoodsByDate[date].foods.length === 1 ? "alimento" : "alimentos"}`} textColor={tokens.color.textMain} />
          <Chip backgroundColor={`${tokens.color.dailyPlan}1A`} borderColor={tokens.color.dailyPlan} label={`${calculatedFoodsByDate[date].plans_count} ${calculatedFoodsByDate[date].plans_count === 1 ? "plan" : "planes"}`} textColor={tokens.color.textMain} />
          <Chip backgroundColor={`${tokens.color.program}1A`} borderColor={tokens.color.program} label={`${calendarFoodPeriodDayCount(foodAttachments[date].start, foodAttachments[date].end)} ${calendarFoodPeriodDayCount(foodAttachments[date].start, foodAttachments[date].end) === 1 ? "día" : "días"}`} textColor={tokens.color.textMain} />
        </View> : null}
        {notesByDate[date]?.trim() ? <Text numberOfLines={1} style={styles.helper}>{notesByDate[date].trim()}</Text> : null}
        </Pressable>
        <View style={styles.selectedDateFooter}>
          {commitmentSupportsFoods(kind) && !foodAttachments[date]
            ? <PickerCardAction label={kind === "shopping" ? "Crear lista de compras" : "Crear lista para cocinar"} onPress={() => openFoodEditor(date)} subject={shortDate(date)} />
            : <Pressable accessibilityLabel={`Ver detalle: ${shortDate(date)}`} accessibilityRole="button" onPress={() => openFoodEditor(date)}><ChevronRight color={tokens.color.textMuted} size={22} /></Pressable>}
        </View>
      </View>) : <Text style={styles.helper}>Toca las fechas del calendario para seleccionarlas.</Text>}
    </View>
    {hasFoodAttachments && serverSupportsPerDateLists === false ? <InlineNotice tone="error">El servidor seleccionado aún no permite guardar una lista distinta para cada fecha. Espera la actualización antes de registrar estos compromisos.</InlineNotice> : null}
    <View style={styles.registerAction}>
      <Button disabled={!selected.length || saving || hasFoodAttachments && serverSupportsPerDateLists !== true} label="Registrar en el calendario" loading={saving} onPress={() => void register()} />
    </View>
  </Screen>;
}

const styles = StyleSheet.create({
  calendarSection: { paddingVertical: tokens.spacing.sm },
  content: { gap: tokens.spacing.lg },
  selectedDateIcon: { alignItems: "center", borderRadius: 6, height: 23, justifyContent: "center", width: 23 },
  commitmentDots: { bottom: 3, flexDirection: "row", gap: 2, position: "absolute" },
  commitmentDot: { borderRadius: 3, height: 5, width: 5 },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: tokens.spacing.sm },
  gridDate: { alignItems: "center", borderColor: "transparent", borderRadius: 10, borderWidth: 2, justifyContent: "center", minHeight: 40, width: "13.5%" },
  gridDateAdjacent: { opacity: 0.5 },
  gridDateExisting: { backgroundColor: tokens.color.surfaceMuted },
  gridDateFilled: { backgroundColor: `${tokens.color.dailyPlan}33` },
  gridDatePast: { opacity: 0.35 },
  gridHeader: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center", width: "13.5%" },
  gridNumber: { color: tokens.color.textMain, fontSize: 14, fontWeight: "500" },
  gridNumberWithPlan: { color: tokens.color.textMain, fontWeight: "700" },
  helper: { color: tokens.color.textMuted, fontSize: 13, lineHeight: 19 },
  foodInstruction: { color: tokens.color.textMain, fontSize: 16, fontWeight: "700", lineHeight: 23 },
  foodPeriodAction: { marginTop: 30 - tokens.spacing.md },
  foodPeriodControls: { gap: tokens.spacing.md, marginBottom: 42 - tokens.spacing.lg },
  legend: { color: tokens.color.textMuted, fontSize: 12, marginTop: tokens.spacing.sm },
  monthArrow: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 10, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  monthNavigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: tokens.spacing.md },
  monthTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "600" },
  noteCount: { color: tokens.color.textMuted, fontSize: 12, textAlign: "right" },
  noteInput: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, color: tokens.color.textMain, minHeight: 96, padding: tokens.spacing.md },
  registerAction: { marginTop: 64 - tokens.spacing.lg },
  sectionTitle: { color: tokens.color.textMain, fontSize: 16, fontWeight: "600" },
  selectedDateCard: { backgroundColor: tokens.color.surfaceCard, borderColor: "transparent", borderRadius: tokens.radius.card, borderWidth: 1, borderTopWidth: 3, gap: tokens.spacing.xs, marginHorizontal: -tokens.spacing.screen, minHeight: 130, overflow: "hidden", padding: tokens.card.outerPadding },
  selectedDateChips: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.xs, marginTop: tokens.spacing.sm },
  selectedDateContent: { gap: tokens.spacing.xs },
  selectedDateEyebrow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  selectedDateEyebrowText: { color: tokens.color.textMuted, fontSize: 12, fontWeight: "600" },
  selectedDateFooter: { alignItems: "center", flexDirection: "row", justifyContent: "flex-end", marginTop: tokens.spacing.sm },
  selectedDateTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: "700" },
  selectedDatesSection: { gap: tokens.spacing.md, marginTop: 34 },
});
