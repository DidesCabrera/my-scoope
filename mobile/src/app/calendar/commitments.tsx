import { type Href, Redirect, useFocusEffect, useLocalSearchParams, usePathname, useRouter } from "expo-router";
import { Check, ChevronLeft, ChevronRight, List, Paperclip, Pencil, Plus, Trash2 } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Alert, BackHandler, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarCommitment, CalendarCommitmentKind, CalendarOverviewData, CalendarPeriodFoodsData } from "@/api/calendar-types";
import { useSession } from "@/auth/session-context";
import { commitmentDayTitle, commitmentFoodPanelItem, commitmentPresentation, commitmentRegistrationTitle, commitmentSupportsFoods } from "@/components/calendarization/calendar-commitments";
import { commitmentDotKinds } from "@/components/calendarization/calendar-commitment-dots";
import { CalendarMonthPlaceholder } from "@/components/calendarization/calendar-month-calendar";
import { CalendarTodayOutline } from "@/components/calendarization/calendar-today-outline";
import { calendarFoodDayRole, calendarFoodPeriodDayCount, selectCalendarFoodDate, validCalendarFoodPeriod } from "@/components/calendarization/calendar-food-period";
import { isCurrentMonthFromToday, monthKeyFromDate, monthLabel, monthWindow, shiftMonth } from "@/components/calendarization/calendar-month";
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

function shiftCalendarDate(value: string, days: number): string {
  const current = new Date(`${value}T12:00:00Z`);
  current.setUTCDate(current.getUTCDate() + days);
  return current.toISOString().slice(0, 10);
}

const addCommitmentTitle: Record<CalendarCommitmentKind, string> = {
  shopping: "Agregar compras al calendario",
  cooking: "Agregar cocinar al calendario",
  training: "Agregar entrenamiento al calendario",
  nutritionist: "Agregar nutricionista al calendario",
};

const commitmentRegistrationSubject: Record<CalendarCommitmentKind, string> = {
  shopping: "de compras",
  cooking: "de cocinar",
  training: "de entrenamiento",
  nutritionist: "con nutricionista",
};

function CommitmentDots({ commitments, draftKind, muted = false }: { commitments?: CalendarCommitment[]; draftKind?: CalendarCommitmentKind; muted?: boolean }) {
  const kinds = commitmentDotKinds(commitments, draftKind);
  if (!kinds.length) return null;
  return <View style={[styles.commitmentDots, muted && styles.commitmentDotsPast]}>{kinds.map((commitmentKind) => <View key={commitmentKind} style={[styles.commitmentDot, { backgroundColor: commitmentPresentation[commitmentKind].color }]} />)}</View>;
}

type FoodAttachment = { start: string; end: string };

export default function RegisterCommitmentsScreen() {
  const router = useRouter();
  const pathname = usePathname();
  const { date: requestedDate, kind: requestedKind, origin } = useLocalSearchParams<{ date?: string; kind?: string; origin?: string }>();
  const kind = isCommitmentKind(requestedKind) ? requestedKind : null;
  const initialDate = requestedDate && /^\d{4}-\d{2}-\d{2}$/.test(requestedDate) ? requestedDate : null;
  const setHeaderPresentation = useHeaderPresentation();
  const { apiRequest, status } = useSession();
  const monthCache = useMemo(() => createCalendarMonthCache(apiRequest), [apiRequest]);
  const [localToday, setLocalToday] = useState<string | null>(null);
  const [todaySize, setTodaySize] = useState({ width: 0, height: 0 });
  const [visibleMonth, setVisibleMonth] = useState<string | null>(null);
  const [monthOverview, setMonthOverview] = useState<CalendarOverviewData | null>(null);
  const [foodMonthOverview, setFoodMonthOverview] = useState<{ key: string; days: CalendarOverviewData["days"] } | null>(null);
  const [selectedDates, setSelectedDates] = useState<string[]>([]);
  const [existingCommitments, setExistingCommitments] = useState<CalendarCommitment[]>([]);
  const [existingCommitmentsError, setExistingCommitmentsError] = useState<string | null>(null);
  const [existingCommitmentsLoading, setExistingCommitmentsLoading] = useState(false);
  const [deletingCommitmentId, setDeletingCommitmentId] = useState<number | null>(null);
  const [foodAttachments, setFoodAttachments] = useState<Record<string, FoodAttachment>>({});
  const [editingFoodDate, setEditingFoodDate] = useState<string | null>(null);
  const [foodViewMode, setFoodViewMode] = useState<"detail" | "generator">("generator");
  const [notesByDate, setNotesByDate] = useState<Record<string, string>>({});
  const [foodStartDate, setFoodStartDate] = useState("");
  const [foodEndDate, setFoodEndDate] = useState("");
  const [foodMonth, setFoodMonth] = useState<string | null>(null);
  const [foodPreview, setFoodPreview] = useState<CalendarPeriodFoodsData | null>(null);
  const [calculatedFoodsByDate, setCalculatedFoodsByDate] = useState<Record<string, CalendarPeriodFoodsData>>({});
  const [serverSupportsPerDateLists, setServerSupportsPerDateLists] = useState<boolean | null>(null);
  const [foodLoading, setFoodLoading] = useState(false);
  const [foodError, setFoodError] = useState<string | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const foodRequestSequence = useRef(0);

  const closeFoodEditor = useCallback(() => {
    foodRequestSequence.current += 1;
    setCompactHeaderVisible(false);
    setFoodLoading(false);
    setEditingFoodDate(null);
    setFoodViewMode("generator");
  }, []);

  const leaveFoodView = useCallback(() => {
    if (foodViewMode === "generator" && editingFoodDate && foodAttachments[editingFoodDate]) {
      const attachment = foodAttachments[editingFoodDate];
      setFoodStartDate(attachment.start);
      setFoodEndDate(attachment.end);
      setFoodPreview(calculatedFoodsByDate[editingFoodDate] ?? null);
      setFoodViewMode("detail");
      return;
    }
    closeFoodEditor();
  }, [calculatedFoodsByDate, closeFoodEditor, editingFoodDate, foodAttachments, foodViewMode]);

  const loadExistingCommitments = useCallback(async (today: string, expectedCount?: number, isActive: () => boolean = () => true) => {
    if (!kind) return;
    setExistingCommitmentsLoading(true);
    setExistingCommitmentsError(null);
    try {
      try {
        const result = await apiRequest<{ items: CalendarCommitment[] }>(
          `/api/v1/calendar/commitments?kind=${kind}&from_date=${today}`,
        );
        if (isActive()) setExistingCommitments(result.items);
        return;
      } catch {
        // Compatibility with staging versions that predate the dedicated list endpoint.
      }
      const byId = new Map<number, CalendarCommitment>();
      let windowStart = today;
      let windowCount = 0;
      do {
        const result = await apiRequest<CalendarOverviewData>(`/api/v1/calendar?start_date=${windowStart}&days=42`);
        if (!isActive()) return;
        result.days.forEach((day) => day.commitments?.forEach((commitment) => {
          if (commitment.kind === kind && commitment.calendar_date >= today) byId.set(commitment.id, commitment);
        }));
        windowStart = shiftCalendarDate(windowStart, 42);
        windowCount += 1;
      } while (expectedCount !== undefined && byId.size < expectedCount && windowCount < 260);
      if (isActive()) setExistingCommitments([...byId.values()].sort((left, right) => left.calendar_date.localeCompare(right.calendar_date)));
    } catch (nextError) {
      if (isActive()) setExistingCommitmentsError(userFacingError(nextError));
    } finally {
      if (isActive()) setExistingCommitmentsLoading(false);
    }
  }, [apiRequest, kind]);

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
        void loadExistingCommitments(result.local_date, result.future_commitments_count_by_kind?.[kind], () => active);
      })
      .catch((nextError) => { if (active) { setError(userFacingError(nextError)); setLoading(false); } });
    return () => { active = false; };
  }, [apiRequest, initialDate, kind, loadExistingCommitments, status]);

  useEffect(() => {
    if (status !== "authenticated" || !visibleMonth) return;
    let active = true;
    void monthCache.load(visibleMonth)
      .then((result) => { if (active) setMonthOverview(result); })
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
      leaveFoodView();
      return true;
    });
    return () => subscription.remove();
  }, [editingFoodDate, leaveFoodView]);

  const presentHeader = useCallback(() => {
    setHeaderPresentation({
      fallback: "/calendar",
      identityVisible: compactHeaderVisible,
      leadingAction: editingFoodDate ? { icon: "back", label: foodViewMode === "generator" && foodAttachments[editingFoodDate] ? "Volver al detalle" : "Volver a las fechas", onPress: leaveFoodView } : undefined,
      mode: "back",
      title: kind ? editingFoodDate ? foodViewMode === "generator" ? "Generar lista de alimentos" : commitmentDayTitle[kind] : commitmentRegistrationTitle[kind] : "Registrar compromisos",
    });
  }, [compactHeaderVisible, editingFoodDate, foodAttachments, foodViewMode, kind, leaveFoodView, setHeaderPresentation]);

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
  const registrationPageIcon = <View style={[styles.registrationPageIcon, { backgroundColor: `${presentation.color}33` }]}>{pageIcon}</View>;

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

  function openFoodGenerator(day: string) {
    foodRequestSequence.current += 1;
    const attachment = foodAttachments[day];
    setCompactHeaderVisible(false);
    setEditingFoodDate(day);
    setFoodViewMode("generator");
    setFoodStartDate(attachment?.start ?? "");
    setFoodEndDate(attachment?.end ?? "");
    setFoodPreview(null);
    setFoodError(null);
    setFoodLoading(false);
    setFoodMonth(monthKeyFromDate(attachment?.start ?? day));
  }

  function openFoodDetail(day: string) {
    const attachment = foodAttachments[day];
    if (!attachment || !calculatedFoodsByDate[day]) {
      openFoodGenerator(day);
      return;
    }
    setCompactHeaderVisible(false);
    setEditingFoodDate(day);
    setFoodViewMode("detail");
    setFoodStartDate(attachment.start);
    setFoodEndDate(attachment.end);
    setFoodPreview(calculatedFoodsByDate[day]);
    setFoodError(null);
    setFoodMonth(monthKeyFromDate(attachment.start));
  }

  async function calculateFoodList() {
    if (!editingFoodDate || !validCalendarFoodPeriod(foodStartDate, foodEndDate) || foodLoading) return;
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
    } catch (nextError) {
      if (foodRequestSequence.current === requestSequence) setFoodError(userFacingError(nextError));
    } finally {
      if (foodRequestSequence.current === requestSequence) setFoodLoading(false);
    }
  }

  function clearFoodSelection() {
    if (foodLoading) return;
    foodRequestSequence.current += 1;
    changeFoodPeriod("", "");
  }

  function associateFoodList() {
    if (!editingFoodDate || !foodPreview || foodLoading) return;
    const day = editingFoodDate;
    setCalculatedFoodsByDate((current) => ({ ...current, [day]: foodPreview }));
    setFoodAttachments((current) => ({ ...current, [day]: { start: foodStartDate, end: foodEndDate } }));
    Alert.alert("Lista asociada con éxito", undefined, [{ text: "Aceptar", onPress: closeFoodEditor }]);
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

  async function deleteExistingCommitment(commitment: CalendarCommitment) {
    if (deletingCommitmentId != null) return;
    setDeletingCommitmentId(commitment.id);
    setExistingCommitmentsError(null);
    try {
      await apiRequest<{ deleted_id: number }>(`/api/v1/calendar/commitments/${commitment.id}`, { method: "DELETE" });
      setExistingCommitments((current) => current.filter((item) => item.id !== commitment.id));
      const affectedMonth = monthKeyFromDate(commitment.calendar_date);
      monthCache.invalidate([affectedMonth]);
      if (visibleMonth === affectedMonth) {
        const refreshed = await monthCache.load(affectedMonth);
        setMonthOverview(refreshed);
      }
      void loadCommitmentReminderSettings().then((reminderSettings) => syncCommitmentReminders(reminderSettings, apiRequest)).catch(() => undefined);
    } catch (nextError) {
      setExistingCommitmentsError(userFacingError(nextError));
    } finally {
      setDeletingCommitmentId(null);
    }
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
      router.replace((origin === "home" ? "/today" : "/calendar/registry") as Href);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  }

  if (editingFoodDate && foodViewMode === "detail") {
    const attachment = foodAttachments[editingFoodDate];
    const attachedFoods = calculatedFoodsByDate[editingFoodDate];
    return <Screen contentStyle={styles.content} headerMode="preserve" key={`commitment-detail-${editingFoodDate}`} onHeaderVisibilityChange={setCompactHeaderVisible}>
      <SectionPageHeader icon={pageIcon} indicator={<Chip backgroundColor={tokens.color.surfaceMuted} borderColor={tokens.color.borderDefault} label={shortDate(editingFoodDate)} textColor={tokens.color.textMain} />} section="calendarization" title={commitmentDayTitle[kind]} />
      {attachment && attachedFoods ? <View style={styles.associatedFoodSection}>
        <Text accessibilityRole="header" style={styles.foodSectionTitle}>Lista de alimentos asociada</Text>
        <GroupedFoodsCard
          chipsAction={<Button bleed={false} label="Editar periodo" onPress={() => openFoodGenerator(editingFoodDate)} variant="secondary" />}
          intro={<Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={`${shortDate(attachment.start)} – ${shortDate(attachment.end)}`} textColor={tokens.color.textMain} />}
          items={attachedFoods.foods.map(commitmentFoodPanelItem)}
          preparationFirst={kind === "shopping"}
          showContents
          summaryChips={<>
            <Chip backgroundColor={`${tokens.color.dailyPlan}1A`} borderColor={tokens.color.dailyPlan} label={`${attachedFoods.plans_count} ${attachedFoods.plans_count === 1 ? "plan" : "planes"}`} textColor={tokens.color.textMain} />
            <Chip backgroundColor={`${tokens.color.meal}1A`} borderColor={tokens.color.meal} label={`${attachedFoods.meals_count} ${attachedFoods.meals_count === 1 ? "comida" : "comidas"}`} textColor={tokens.color.textMain} />
          </>}
          title={kind === "cooking" ? "Alimentos para cocinar" : "Alimentos para comprar"}
        />
      </View> : null}
      <Card>
        <Text style={styles.sectionTitle}>Nota (opcional)</Text>
        <TextInput accessibilityLabel={`Nota de ${kind === "nutritionist" ? "la cita nutricionista" : `el ${commitmentDayTitle[kind].toLowerCase()}`} del ${shortDate(editingFoodDate)}`} maxLength={500} multiline onChangeText={(value) => setNotesByDate((current) => ({ ...current, [editingFoodDate]: value }))} placeholder="Agrega una nota para recordar los detalles…" placeholderTextColor={tokens.color.textMuted} style={styles.noteInput} textAlignVertical="top" value={notesByDate[editingFoodDate] ?? ""} />
        <Text style={styles.noteCount}>{(notesByDate[editingFoodDate] ?? "").length}/500</Text>
      </Card>
    </Screen>;
  }

  if (editingFoodDate) return <Screen contentStyle={styles.content} headerMode="preserve" key={`commitment-generator-${editingFoodDate}`} onHeaderVisibilityChange={setCompactHeaderVisible}>
    <SectionPageHeader icon={<List color={tokens.color.textMain} size={28} strokeWidth={1.8} />} section="calendarization" subtitle="Selecciona la fecha de inicio y término del periodo" title="Generar lista de alimentos" />
    {commitmentSupportsFoods(kind) ? <View style={styles.foodPeriodControls}>
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
                style={[styles.gridDate, dayData?.has_plan && styles.gridDateFilled, dayData?.has_plan && isCurrentMonthFromToday(day, localToday) && styles.gridDateUpcomingFilled, endpoint && { backgroundColor: `${accent}26`, borderColor: accent }, role === "between" && { backgroundColor: `${accent}33` }, monthKeyFromDate(day) !== foodMonth && styles.gridDateAdjacent]}>
                <Text style={[styles.gridNumber, dayData?.has_plan && styles.gridNumberWithPlan, Boolean(localToday && day < localToday) && styles.gridNumberPast, endpoint && { color: accent, fontWeight: "700" }, role === "between" && { color: accent }]}>{day.slice(8, 10)}</Text>
                <CommitmentDots commitments={dayCommitments} draftKind={shoppingDate ? "shopping" : undefined} muted={Boolean(localToday && day < localToday)} />
              </Pressable>;
            })}
          </View>
          <View style={styles.foodPeriodAction}>
            {foodPreview ? <>
              <Button contentStyle={styles.foodActionButtonContent} icon={<Check color={tokens.color.surfaceApp} size={18} strokeWidth={2.6} />} label="Asociar lista de alimentos" onPress={associateFoodList} />
              <Button contentStyle={styles.foodActionButtonContent} icon={<Pencil color={tokens.color.textMain} size={18} strokeWidth={2.2} />} label="Editar periodo" onPress={() => setFoodPreview(null)} variant="secondary" />
            </> : <>
              <Button disabled={!validCalendarFoodPeriod(foodStartDate, foodEndDate) || foodLoading} label="Generar lista de alimentos" loading={foodLoading} onPress={() => void calculateFoodList()} />
              <Button disabled={!foodStartDate && !foodEndDate || foodLoading} label="Limpiar selección" onPress={clearFoodSelection} variant="secondary" />
            </>}
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
  </Screen>;

  return <Screen contentStyle={styles.content} headerMode="preserve" key="commitment-registration" onHeaderVisibilityChange={setCompactHeaderVisible}>
    <SectionPageHeader
      icon={registrationPageIcon}
      indicator={<Chip
        backgroundColor={`${presentation.color}33`}
        borderless
        label={`${existingCommitments.length} ${existingCommitments.length === 1 ? "día comprometido" : "días comprometidos"}`}
        textColor={tokens.color.textMain}
      />}
      section="calendarization"
      title={commitmentRegistrationTitle[kind]}
    />
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    <View style={styles.addCommitmentHeading}>
      <View style={styles.addCommitmentTitleRow}>
        <Plus color={tokens.color.textMain} size={22} strokeWidth={2.4} />
        <Text accessibilityRole="header" style={styles.addCommitmentTitle}>{addCommitmentTitle[kind]}</Text>
      </View>
      <Text style={styles.addCommitmentSubtitle}>Selecciona las fechas que desees</Text>
    </View>
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
            onLayout={day.calendar_date === localToday ? ({ nativeEvent: { layout } }) => {
              setTodaySize((current) => current.width === layout.width && current.height === layout.height ? current : { width: layout.width, height: layout.height });
            } : undefined}
            onPress={() => toggleDate(day.calendar_date)}
            style={[styles.gridDate, day.has_plan && styles.gridDateFilled, day.has_plan && isCurrentMonthFromToday(day.calendar_date, localToday) && styles.gridDateUpcomingFilled, isSelected && { backgroundColor: `${presentation.color}33`, borderColor: presentation.color }, exists && styles.gridDateExisting, monthKeyFromDate(day.calendar_date) !== visibleMonth && styles.gridDateAdjacent, isPast && styles.gridDatePast, day.calendar_date === localToday && styles.gridDateToday]}>
            <Text style={[styles.gridNumber, day.has_plan && styles.gridNumberWithPlan, isPast && styles.gridNumberPast, (isSelected || exists) && { color: presentation.color }]}>{day.calendar_date.slice(8, 10)}</Text>
            <CommitmentDots commitments={day.commitments} muted={isPast} />
            {day.calendar_date === localToday ? <CalendarTodayOutline {...todaySize} /> : null}
          </Pressable>;
        })}
      </View>}
    </View>
    <View style={[styles.selectedDatesSection, styles.currentSelectedDatesSection]}>
      <Text style={styles.sectionTitle}>Días seleccionados · {selected.length}</Text>
      {selected.length ? selected.map((date) => <View key={date} style={styles.selectedDateCard}>
        <Pressable accessibilityLabel={`Ver detalle: ${commitmentDayTitle[kind]} del ${shortDate(date)}`} accessibilityRole="button" onPress={() => openFoodDetail(date)} style={styles.selectedDateContent}>
          <View style={styles.selectedDateMainRow}>
            <View style={[styles.selectedDateIcon, { backgroundColor: `${presentation.color}33` }]}>
              <CommitmentIcon color={presentation.color} size={23} strokeWidth={2.1} />
            </View>
            <View style={styles.selectedDateCopy}>
              <Text style={styles.selectedDateTitle}>{commitmentDayTitle[kind]}</Text>
              <Text style={styles.selectedDateDate}>{shortDate(date)}</Text>
              {notesByDate[date]?.trim() ? <Text numberOfLines={1} style={styles.selectedDateNote}>{notesByDate[date].trim()}</Text> : null}
            </View>
            <Pressable
              accessibilityLabel={`Quitar ${commitmentDayTitle[kind].toLowerCase()} del ${shortDate(date)}`}
              accessibilityRole="button"
              hitSlop={8}
              onPress={(event) => { event.stopPropagation(); toggleDate(date); }}
              style={({ pressed }) => [styles.selectedDateRemove, pressed && styles.selectedDateRemovePressed]}>
              <Trash2 color={tokens.color.danger} size={16} strokeWidth={2.2} />
            </Pressable>
          </View>
          {foodAttachments[date] && calculatedFoodsByDate[date] ? <View style={styles.selectedDateListRow}>
            <View style={styles.selectedDateAttachmentIcon}>
              <Paperclip accessibilityLabel="Lista de alimentos adjunta" color={tokens.color.textSoft} size={18} strokeWidth={2} />
            </View>
            <View style={styles.selectedDateChips}>
            <Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={`${calculatedFoodsByDate[date].foods.length} ${calculatedFoodsByDate[date].foods.length === 1 ? "alimento" : "alimentos"}`} textColor={tokens.color.textMain} />
            <Chip backgroundColor={`${tokens.color.dailyPlan}1A`} borderColor={tokens.color.dailyPlan} label={`${calculatedFoodsByDate[date].plans_count} ${calculatedFoodsByDate[date].plans_count === 1 ? "plan" : "planes"}`} textColor={tokens.color.textMain} />
            <Chip backgroundColor={`${tokens.color.program}1A`} borderColor={tokens.color.program} label={`${calendarFoodPeriodDayCount(foodAttachments[date].start, foodAttachments[date].end)} ${calendarFoodPeriodDayCount(foodAttachments[date].start, foodAttachments[date].end) === 1 ? "día" : "días"}`} textColor={tokens.color.textMain} />
            </View>
          </View> : null}
        </Pressable>
        {commitmentSupportsFoods(kind) && !foodAttachments[date] ? <View style={styles.selectedDateFooter}>
          <PickerCardAction icon={<List color={tokens.color.textMain} size={18} strokeWidth={2} />} label="Crear lista de alimentos" onPress={() => openFoodGenerator(date)} subject={shortDate(date)} variant="mutedFullWidth" />
        </View> : null}
      </View>) : <Text style={styles.helper}>Toca las fechas del calendario para seleccionarlas.</Text>}
    </View>
    <View style={styles.calendarAction}>
      <Button
        disabled={!selected.length || saving || hasFoodAttachments && serverSupportsPerDateLists !== true}
        label={`Registrar ${selected.length} ${selected.length === 1 ? "día" : "días"} ${commitmentRegistrationSubject[kind]}`}
        loading={saving}
        onPress={() => void register()}
      />
    </View>
    {hasFoodAttachments && serverSupportsPerDateLists === false ? <InlineNotice tone="error">El servidor seleccionado aún no permite guardar una lista distinta para cada fecha. Espera la actualización antes de registrar estos compromisos.</InlineNotice> : null}
    <View style={styles.selectedDatesSection}>
      <Text style={styles.sectionTitle}>Días comprometidos previamente · {existingCommitments.length}</Text>
      {existingCommitmentsError ? <InlineNotice tone="error">{existingCommitmentsError}</InlineNotice> : null}
      {existingCommitmentsLoading ? <Text style={styles.helper}>Cargando próximos compromisos…</Text> : null}
      {!existingCommitmentsLoading && !existingCommitments.length ? <Text style={styles.helper}>No hay próximos compromisos de este tipo.</Text> : null}
      {existingCommitments.map((commitment) => {
        const hasAttachedFoods = Boolean(commitment.food_period_start && commitment.food_period_end);
        return <View key={commitment.id} style={styles.selectedDateCard}>
          <Pressable accessibilityLabel={`Ver detalle: ${commitmentDayTitle[commitment.kind]} del ${shortDate(commitment.calendar_date)}`} accessibilityRole="button" onPress={() => router.push(`/calendar/commitments/${commitment.id}?date=${commitment.calendar_date}` as Href)} style={styles.selectedDateContent}>
            <View style={styles.selectedDateMainRow}>
              <View style={[styles.selectedDateIcon, { backgroundColor: `${presentation.color}33` }]}>
                <CommitmentIcon color={presentation.color} size={23} strokeWidth={2.1} />
              </View>
              <View style={styles.selectedDateCopy}>
                <Text style={styles.selectedDateTitle}>{commitmentDayTitle[commitment.kind]}</Text>
                <Text style={styles.selectedDateDate}>{shortDate(commitment.calendar_date)}</Text>
                {commitment.note ? <Text numberOfLines={1} style={styles.selectedDateNote}>{commitment.note}</Text> : null}
              </View>
              <Pressable
                accessibilityLabel={`Eliminar ${commitmentDayTitle[commitment.kind].toLowerCase()} del ${shortDate(commitment.calendar_date)}`}
                accessibilityRole="button"
                accessibilityState={{ busy: deletingCommitmentId === commitment.id, disabled: deletingCommitmentId != null }}
                disabled={deletingCommitmentId != null}
                hitSlop={8}
                onPress={(event) => { event.stopPropagation(); void deleteExistingCommitment(commitment); }}
                style={({ pressed }) => [styles.selectedDateRemove, deletingCommitmentId != null && styles.selectedDateRemoveDisabled, pressed && styles.selectedDateRemovePressed]}>
                <Trash2 color={tokens.color.danger} size={16} strokeWidth={2.2} />
              </Pressable>
            </View>
            {hasAttachedFoods ? <View style={styles.selectedDateListRow}>
              <View style={styles.selectedDateAttachmentIcon}>
                <Paperclip accessibilityLabel="Lista de alimentos adjunta" color={tokens.color.textSoft} size={18} strokeWidth={2} />
              </View>
              <View style={styles.selectedDateChips}>
                <Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={`${commitment.foods.length} ${commitment.foods.length === 1 ? "alimento" : "alimentos"}`} textColor={tokens.color.textMain} />
                <Chip backgroundColor={`${tokens.color.dailyPlan}1A`} borderColor={tokens.color.dailyPlan} label={`${commitment.food_plans_count} ${commitment.food_plans_count === 1 ? "plan" : "planes"}`} textColor={tokens.color.textMain} />
                <Chip backgroundColor={`${tokens.color.program}1A`} borderColor={tokens.color.program} label={`${calendarFoodPeriodDayCount(commitment.food_period_start!, commitment.food_period_end!)} ${calendarFoodPeriodDayCount(commitment.food_period_start!, commitment.food_period_end!) === 1 ? "día" : "días"}`} textColor={tokens.color.textMain} />
              </View>
            </View> : null}
          </Pressable>
        </View>;
      })}
    </View>
  </Screen>;
}

const styles = StyleSheet.create({
  addCommitmentHeading: { gap: tokens.spacing.xs },
  addCommitmentSubtitle: { color: tokens.color.textMain, fontSize: tokens.type.caption, lineHeight: 20 },
  addCommitmentTitle: { color: tokens.color.textMain, flexShrink: 1, fontSize: 18, fontWeight: tokens.weight.semibold, lineHeight: 24 },
  addCommitmentTitleRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  associatedFoodSection: { gap: tokens.spacing.md },
  calendarAction: { gap: 20, marginTop: 8 },
  calendarSection: { marginBottom: 34 - tokens.spacing.lg, paddingTop: tokens.spacing.sm },
  content: { gap: tokens.spacing.lg },
  currentSelectedDatesSection: { marginTop: -8 },
  selectedDateIcon: { alignItems: "center", borderRadius: 10, height: 40, justifyContent: "center", width: 40 },
  commitmentDots: { bottom: 4, flexDirection: "row", gap: 2, position: "absolute" },
  commitmentDotsPast: { opacity: 0.5 },
  commitmentDot: { borderRadius: 3, height: 5, width: 5 },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: tokens.spacing.sm },
  gridDate: { alignItems: "center", borderColor: "transparent", borderRadius: 10, borderWidth: 2, justifyContent: "center", minHeight: 40, width: "13.5%" },
  gridDateAdjacent: { opacity: 0.5 },
  gridDateExisting: { backgroundColor: tokens.color.surfaceMuted },
  gridDateFilled: { backgroundColor: `${tokens.color.dailyPlan}2E` },
  gridDateUpcomingFilled: { backgroundColor: `${tokens.color.dailyPlan}59` },
  gridDatePast: { opacity: 0.35 },
  gridDateToday: { borderWidth: 0 },
  gridHeader: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center", width: "13.5%" },
  gridNumber: { color: tokens.color.textMain, fontSize: 14, fontWeight: "500" },
  gridNumberPast: { opacity: 0.8 },
  gridNumberWithPlan: { color: tokens.color.textMain, fontWeight: "700" },
  helper: { color: tokens.color.textMuted, fontSize: 13, lineHeight: 19 },
  foodActionButtonContent: { transform: [{ translateX: -10 }] },
  foodPeriodAction: { gap: tokens.spacing.sm, marginBottom: 28 - tokens.spacing.lg, marginTop: 34 - tokens.spacing.md },
  foodPeriodControls: { gap: tokens.spacing.md },
  foodSectionTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: tokens.weight.extraBold },
  monthArrow: { alignItems: "center", height: 36, justifyContent: "center", width: 36 },
  monthNavigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: tokens.spacing.md },
  monthTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "600" },
  noteCount: { color: tokens.color.textMuted, fontSize: 12, textAlign: "right" },
  noteInput: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, color: tokens.color.textMain, minHeight: 96, padding: tokens.spacing.md },
  registrationPageIcon: { alignItems: "center", borderRadius: 12, height: 48, justifyContent: "center", width: 48 },
  sectionTitle: { color: tokens.color.textMain, fontSize: 16, fontWeight: "600" },
  selectedDateCard: { backgroundColor: tokens.color.surfaceCard, borderColor: "transparent", borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.xs, marginHorizontal: -tokens.spacing.screen, minHeight: 128, padding: tokens.card.outerPadding },
  selectedDateAttachmentIcon: { alignItems: "center", justifyContent: "center", width: 40 },
  selectedDateChips: { alignItems: "center", flex: 1, flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.xs },
  selectedDateContent: { flex: 1, gap: tokens.spacing.sm, justifyContent: "space-between" },
  selectedDateCopy: { flex: 1, gap: tokens.spacing.xs },
  selectedDateDate: { color: tokens.color.textMuted, fontSize: 13 },
  selectedDateFooter: { alignItems: "stretch", marginTop: tokens.spacing.sm, width: "100%" },
  selectedDateListRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  selectedDateMainRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  selectedDateNote: { color: tokens.color.textMain, fontSize: 13, lineHeight: 19 },
  selectedDateRemove: { alignItems: "center", backgroundColor: `${tokens.color.danger}1A`, borderRadius: tokens.radius.pill, height: 30, justifyContent: "center", width: 30 },
  selectedDateRemoveDisabled: { opacity: 0.45 },
  selectedDateRemovePressed: { opacity: 0.68 },
  selectedDateTitle: { color: tokens.color.textMain, fontSize: 16, fontWeight: tokens.weight.semibold },
  selectedDatesSection: { gap: tokens.spacing.md, marginTop: 34 },
});
