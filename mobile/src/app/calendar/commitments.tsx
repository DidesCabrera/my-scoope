import { type Href, Redirect, useFocusEffect, useLocalSearchParams, usePathname, useRouter } from "expo-router";
import { ChevronLeft, ChevronRight } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BackHandler, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarCommitment, CalendarCommitmentKind, CalendarOverviewData, CalendarPeriodFoodsData } from "@/api/calendar-types";
import { useSession } from "@/auth/session-context";
import { commitmentDayTitle, commitmentFoodPanelItem, commitmentPresentation, commitmentRegistrationTitle } from "@/components/calendarization/calendar-commitments";
import { calendarFoodDayRole, selectCalendarFoodDate, validCalendarFoodPeriod } from "@/components/calendarization/calendar-food-period";
import { monthKeyFromDate, monthLabel, monthWindow, shiftMonth } from "@/components/calendarization/calendar-month";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { GroupedFoodsCard } from "@/components/panels";
import { Button, Card, InlineNotice, LoadingState, Screen, SectionPageHeader } from "@/components/ui";
import { Chip } from "@/components/ui/chip";
import { tokens } from "@/design/tokens";

function isCommitmentKind(value: string | undefined): value is CalendarCommitmentKind {
  return value === "shopping" || value === "cooking" || value === "training";
}

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" })
    .format(new Date(`${value}T12:00:00`));
}

type FoodAttachment = { start: string; end: string };

export default function RegisterCommitmentsScreen() {
  const router = useRouter();
  const pathname = usePathname();
  const { kind: requestedKind } = useLocalSearchParams<{ kind?: string }>();
  const kind = isCommitmentKind(requestedKind) ? requestedKind : null;
  const setHeaderPresentation = useHeaderPresentation();
  const { apiRequest, status } = useSession();
  const [localToday, setLocalToday] = useState<string | null>(null);
  const [visibleMonth, setVisibleMonth] = useState<string | null>(null);
  const [monthOverview, setMonthOverview] = useState<CalendarOverviewData | null>(null);
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
        setVisibleMonth(monthKeyFromDate(result.local_date));
        setFoodMonth(monthKeyFromDate(result.local_date));
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
    setLoading(true);
    setError(null);
    setMonthOverview(null);
    setVisibleMonth(shiftMonth(visibleMonth, delta));
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
      router.replace("/calendar" as Href);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  }

  if (editingFoodDate) return <Screen contentStyle={styles.content} key={`commitment-detail-${editingFoodDate}`}>
    <SectionPageHeader icon={pageIcon} indicator={<Chip backgroundColor={tokens.color.surfaceMuted} borderColor={tokens.color.borderDefault} label={shortDate(editingFoodDate)} textColor={tokens.color.textMain} />} section="calendarization" title={commitmentDayTitle[kind]} />
    {kind !== "training" ? <GroupedFoodsCard
      intro={<>
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
              const accent = tokens.color.food;
              return <Pressable
                accessibilityLabel={`${shortDate(day)}: ${shoppingDate ? "día para hacer compras, " : ""}${role === "single" ? "inicio y término" : role === "start" ? "inicio" : role === "end" ? "término" : role === "between" ? "dentro del periodo" : "fuera del periodo"}`}
                accessibilityRole="button"
                accessibilityState={{ disabled: foodRangeLocked }}
                disabled={foodRangeLocked}
                key={`food-${day}`}
                onPress={() => chooseFoodDate(day)}
                style={[styles.gridDate, endpoint && { backgroundColor: `${accent}26`, borderColor: accent }, role === "between" && { backgroundColor: `${accent}33` }, monthKeyFromDate(day) !== foodMonth && styles.gridDateAdjacent]}>
                <Text style={[styles.gridNumber, endpoint && { color: accent, fontWeight: "700" }, role === "between" && { color: accent }]}>{day.slice(8, 10)}</Text>
                {shoppingDate ? <View style={styles.shoppingDateDot} /> : null}
              </Pressable>;
            })}
          </View>
          {foodStartDate && !foodEndDate ? <InlineNotice>Ahora elige la fecha de término.</InlineNotice> : null}
          {foodPreview ? <Button label="Limpiar selección" onPress={clearFoodSelection} variant="secondary" />
            : <Button disabled={!validCalendarFoodPeriod(foodStartDate, foodEndDate) || foodLoading} label="Calcular lista de alimentos" loading={foodLoading} onPress={() => void calculateFoodList()} />}
          {foodPreview ? <Text style={styles.helper}>{typeof foodPreview.meals_count === "number"
            ? `${foodPreview.plans_count} ${foodPreview.plans_count === 1 ? "plan" : "planes"} y ${foodPreview.meals_count} ${foodPreview.meals_count === 1 ? "comida programada" : "comidas programadas"} en este periodo.`
            : `${foodPreview.plans_count} ${foodPreview.plans_count === 1 ? "plan programado" : "planes programados"} en este periodo.`}</Text> : null}
        {foodError ? <InlineNotice tone="error">{foodError}</InlineNotice> : null}
        {foodLoading ? <LoadingState label="Calculando alimentos…" /> : null}
      </>}
      items={foodPreview?.foods.map(commitmentFoodPanelItem) ?? []}
      key={`${editingFoodDate}:${foodStartDate}:${foodEndDate}`}
      onOpenItem={(food) => { if (food.detailId != null) router.push(`/libraries/foods/${food.detailId}` as Href); }}
      showContents={Boolean(foodPreview)}
      title={kind === "cooking" ? "Alimentos para cocinar" : "Alimentos para comprar"}
    /> : null}
    <Card>
      <Text style={styles.sectionTitle}>Nota (opcional)</Text>
      <TextInput accessibilityLabel={`Nota del ${commitmentDayTitle[kind].toLowerCase()} del ${shortDate(editingFoodDate)}`} maxLength={500} multiline onChangeText={(value) => setNotesByDate((current) => ({ ...current, [editingFoodDate]: value }))} placeholder="Agrega una nota para recordar los detalles…" placeholderTextColor={tokens.color.textMuted} style={styles.noteInput} textAlignVertical="top" value={notesByDate[editingFoodDate] ?? ""} />
      <Text style={styles.noteCount}>{(notesByDate[editingFoodDate] ?? "").length}/500</Text>
    </Card>
  </Screen>;

  return <Screen contentStyle={styles.content} key="commitment-registration">
    <SectionPageHeader countLabel="fechas" icon={pageIcon} section="calendarization" subtitle="Marca varios días; puedes cambiar de mes sin perder tu selección." title={commitmentRegistrationTitle[kind]} />
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
        {selected.map((date) => <Pressable accessibilityLabel={`Ver detalle: ${commitmentDayTitle[kind]} del ${shortDate(date)}`} accessibilityRole="button" key={date} onPress={() => openFoodEditor(date)} style={styles.selectedDateRow}>
          <View style={[styles.selectedDateIcon, { backgroundColor: `${presentation.color}28` }]}><CommitmentIcon color={presentation.color} size={20} /></View>
          <View style={styles.selectedDateDetails}>
            <Text style={styles.selectedDateTitle}>{commitmentDayTitle[kind]} · {shortDate(date)}</Text>
            {kind !== "training" ? <Text style={styles.helper}>{foodAttachments[date]
              ? `Lista: ${shortDate(foodAttachments[date].start)} – ${shortDate(foodAttachments[date].end)}`
              : "Sin lista de alimentos adjunta"}</Text> : null}
            {notesByDate[date]?.trim() ? <Text numberOfLines={1} style={styles.helper}>{notesByDate[date].trim()}</Text> : null}
          </View>
          <ChevronRight color={tokens.color.textMuted} size={20} />
        </Pressable>)}
      </View> : <Text style={styles.helper}>Toca las fechas del calendario para seleccionarlas.</Text>}
    </Card>
    {hasFoodAttachments && serverSupportsPerDateLists === false ? <InlineNotice tone="error">El servidor seleccionado aún no permite guardar una lista distinta para cada fecha. Espera la actualización antes de registrar estos compromisos.</InlineNotice> : null}
    <Button disabled={!selected.length || saving || hasFoodAttachments && serverSupportsPerDateLists !== true} label="Registrar en el calendario" loading={saving} onPress={() => void register()} />
  </Screen>;
}

const styles = StyleSheet.create({
  content: { gap: tokens.spacing.lg },
  selectedDateIcon: { alignItems: "center", borderRadius: tokens.radius.md, height: 42, justifyContent: "center", width: 42 },
  existingDot: { borderRadius: 3, bottom: 3, height: 5, position: "absolute", width: 5 },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: tokens.spacing.sm },
  gridDate: { alignItems: "center", borderColor: "transparent", borderRadius: 10, borderWidth: 2, justifyContent: "center", minHeight: 40, width: "13.5%" },
  gridDateAdjacent: { opacity: 0.5 },
  gridDateExisting: { backgroundColor: tokens.color.surfaceMuted },
  gridDatePast: { opacity: 0.35 },
  gridHeader: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center", width: "13.5%" },
  gridNumber: { color: tokens.color.textMain, fontSize: 14, fontWeight: "500" },
  helper: { color: tokens.color.textMuted, fontSize: 13, lineHeight: 19 },
  foodInstruction: { color: tokens.color.textMain, fontSize: 16, lineHeight: 23 },
  legend: { color: tokens.color.textMuted, fontSize: 12, marginTop: tokens.spacing.sm },
  monthArrow: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 10, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  monthNavigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: tokens.spacing.md },
  monthTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "600" },
  noteCount: { color: tokens.color.textMuted, fontSize: 12, textAlign: "right" },
  noteInput: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, color: tokens.color.textMain, minHeight: 96, padding: tokens.spacing.md },
  sectionTitle: { color: tokens.color.textMain, fontSize: 16, fontWeight: "600" },
  selectedDateDetails: { flex: 1, gap: tokens.spacing.xs },
  selectedDateRow: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 72, padding: tokens.spacing.md },
  selectedDateTitle: { color: tokens.color.textMain, fontSize: 14, fontWeight: "600" },
  selectedDates: { gap: tokens.spacing.xs },
  shoppingDateDot: { backgroundColor: tokens.color.food, borderRadius: 3, bottom: 4, height: 5, position: "absolute", width: 5 },
});
