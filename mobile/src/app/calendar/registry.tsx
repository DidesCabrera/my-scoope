import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { Bell, CalendarDays, ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react-native";
import { useCallback, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarCommitment, CalendarCommitmentKind, CalendarOverviewData } from "@/api/calendar-types";
import { useSession } from "@/auth/session-context";
import { commitmentKinds, commitmentPresentation, commitmentRegistrationTitle } from "@/components/calendarization/calendar-commitments";
import { CalendarCommitmentListCard } from "@/components/calendarization/calendar-commitment-list-card";
import { CalendarMonthPlaceholder } from "@/components/calendarization/calendar-month-calendar";
import { isCurrentMonthFromToday, monthKeyFromDate, monthLabel, shiftMonth } from "@/components/calendarization/calendar-month";
import { createCalendarMonthCache } from "@/components/calendarization/calendar-month-cache";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Card, InlineNotice, Screen, ScrollableTabBar } from "@/components/ui";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { tokens } from "@/design/tokens";

type CommitmentScope = "all" | CalendarCommitmentKind;

const tabLabels: Record<CalendarCommitmentKind, string> = {
  shopping: "Hacer compras",
  cooking: "Cocinar",
  training: "Entrenar",
  nutritionist: "Cita nutricionista",
};

function readableDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric" })
    .format(new Date(`${value}T12:00:00`));
}

function CommitmentHeader() {
  return <View style={styles.header}>
    <View accessibilityLabel="Hacer compras, cocinar, entrenar y cita nutricionista" accessible style={styles.headerIcons}>
      {commitmentKinds.map((kind) => {
        const presentation = commitmentPresentation[kind];
        const Icon = presentation.icon;
        return <View key={kind} style={[styles.headerIcon, { backgroundColor: `${presentation.color}33` }]}>
          <Icon color={presentation.color} size={24} strokeWidth={2.1} />
        </View>;
      })}
    </View>
    <Text accessibilityRole="header" style={styles.title}>Mis compromisos</Text>
    <Text style={styles.subtitle}>Marca en el calendario tus compromisos y planifícate con anticipación</Text>
  </View>;
}

export default function CommitmentRegistryScreen() {
  const router = useRouter();
  const setHeaderPresentation = useHeaderPresentation();
  const { apiRequest, status } = useSession();
  const monthCache = useMemo(() => createCalendarMonthCache(apiRequest), [apiRequest]);
  const [activeScope, setActiveScope] = useState<CommitmentScope>("all");
  const [visibleMonth, setVisibleMonth] = useState<string | null>(null);
  const [overview, setOverview] = useState<CalendarOverviewData | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [menuVisible, setMenuVisible] = useState(false);
  const [actionsVisible, setActionsVisible] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      action: { icon: "more", label: "Más opciones de compromisos", onPress: () => setActionsVisible(true) },
      fallback: "/calendar",
      identityVisible: compactHeaderVisible,
      mode: "back",
      secondaryAction: { icon: "plus", label: "Registrar un compromiso", onPress: () => setMenuVisible(true) },
      title: "Mis compromisos",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated") return;
    let active = true;
    void apiRequest<CalendarOverviewData>("/api/v1/calendar?days=1")
      .then((data) => { if (active) setVisibleMonth((current) => current ?? monthKeyFromDate(data.local_date)); })
      .catch((nextError) => { if (active) { setError(userFacingError(nextError)); setLoading(false); } });
    return () => { active = false; };
  }, [apiRequest, status]));

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated" || !visibleMonth) return;
    let active = true;
    const cached = monthCache.get(visibleMonth);
    if (cached) setOverview(cached);
    setLoading(!cached);
    setError(null);
    void monthCache.load(visibleMonth)
      .then((data) => { if (active) setOverview(data); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [monthCache, status, visibleMonth]));

  const monthDays = useMemo(() => overview?.days.filter((day) => monthKeyFromDate(day.calendar_date) === visibleMonth) ?? [], [overview, visibleMonth]);
  const commitments = useMemo(() => monthDays.flatMap((day) => (day.commitments ?? []).filter((item) =>
    (activeScope === "all" || item.kind === activeScope) && (!selectedDate || item.calendar_date === selectedDate)
  )), [activeScope, monthDays, selectedDate]);

  function openRegistration(kind: CalendarCommitmentKind) {
    setMenuVisible(false);
    router.push(`/calendar/commitments?kind=${kind}` as Href);
  }

  function selectDate(date: string) {
    if (monthKeyFromDate(date) !== visibleMonth) {
      setSelectedDate(date);
      setVisibleMonth(monthKeyFromDate(date));
      return;
    }
    setSelectedDate((current) => current === date ? null : date);
  }

  function changeMonth(delta: number) {
    if (!visibleMonth) return;
    const nextMonth = shiftMonth(visibleMonth, delta);
    const cached = monthCache.get(nextMonth);
    if (cached) setOverview(cached);
    setLoading(!cached);
    setSelectedDate(null);
    setVisibleMonth(nextMonth);
  }

  if (status === "anonymous") return <Redirect href="/login" />;

  return <>
    <Screen
      contentStyle={styles.content}
      headerMode="preserve"
      onHeaderVisibilityChange={setCompactHeaderVisible}
      scrollHeader={<CommitmentHeader />}
      stickyHeader={<ScrollableTabBar<CommitmentScope>
        accessibilityLabel="Tipos de compromisos"
        activeTab={activeScope}
        density="compact"
        onChange={(scope) => { setActiveScope(scope); setSelectedDate(null); }}
        tabs={[
          { key: "all", label: "Todos" },
          ...commitmentKinds.map((kind) => ({ key: kind, label: tabLabels[kind] })),
        ]}
      />}
      stickyHeaderStyle={styles.stickyHeader}>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      <View style={styles.calendarSection}>
        <View style={styles.monthNavigation}>
          <Pressable accessibilityLabel="Mes anterior" accessibilityRole="button" onPress={() => changeMonth(-1)} style={({ pressed }) => [styles.monthArrow, pressed && styles.pressed]}>
            <ChevronLeft color={tokens.color.textMain} size={20} />
          </Pressable>
          <Text accessibilityRole="header" style={styles.monthTitle}>{visibleMonth ? monthLabel(visibleMonth) : ""}</Text>
          <Pressable accessibilityLabel="Mes siguiente" accessibilityRole="button" onPress={() => changeMonth(1)} style={({ pressed }) => [styles.monthArrow, pressed && styles.pressed]}>
            <ChevronRight color={tokens.color.textMain} size={20} />
          </Pressable>
        </View>
        {loading ? <CalendarMonthPlaceholder /> : <View style={styles.grid}>
          {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
          {overview?.days.map((day) => {
            const visibleCommitments = (day.commitments ?? []).filter((item) => activeScope === "all" || item.kind === activeScope);
            const selected = selectedDate === day.calendar_date;
            return <Pressable
              accessibilityLabel={`${readableDate(day.calendar_date)}: ${day.has_plan ? "Con minuta diaria" : "Sin minuta diaria"}; ${visibleCommitments.length ? visibleCommitments.map((item) => commitmentPresentation[item.kind].label).join(", ") : "Sin compromisos"}`}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              key={day.calendar_date}
              onPress={() => selectDate(day.calendar_date)}
              style={({ pressed }) => [styles.gridDate, selected && styles.gridDateSelected, day.has_plan && styles.gridDateFilled, day.has_plan && isCurrentMonthFromToday(day.calendar_date, overview?.local_date) && styles.gridDateUpcomingFilled, monthKeyFromDate(day.calendar_date) !== visibleMonth && styles.gridDateAdjacent, pressed && styles.pressed]}>
              <Text style={[styles.gridNumber, day.has_plan && styles.gridNumberWithPlan, Boolean(overview?.local_date && day.calendar_date < overview.local_date) && styles.gridNumberPast]}>{day.calendar_date.slice(8, 10)}</Text>
              {visibleCommitments.length ? <View style={styles.commitmentDots}>{visibleCommitments.map((item) => <View key={item.id} style={[styles.commitmentDot, { backgroundColor: commitmentPresentation[item.kind].color }]} />)}</View> : null}
            </Pressable>;
          })}
        </View>}
        <Text style={styles.hint}>Toca un día para ver sus compromisos. Tócalo otra vez para ver todo el mes.</Text>
      </View>
      <Text accessibilityRole="header" style={styles.listTitle}>{selectedDate ? `Compromisos del ${readableDate(selectedDate)}` : `Compromisos de ${visibleMonth ? monthLabel(visibleMonth) : "este mes"}`}</Text>
      {!loading && !error && !commitments.length ? <Card><Text style={styles.empty}>No hay compromisos registrados para esta selección.</Text></Card> : null}
      {!loading && commitments.map((commitment: CalendarCommitment) => <CalendarCommitmentListCard commitment={commitment} key={commitment.id} onPress={() => router.push(`/calendar/commitments/${commitment.id}?date=${commitment.calendar_date}` as Href)} />)}
    </Screen>
    <ActionSheetModal onRequestClose={() => setMenuVisible(false)} visible={menuVisible}>
      <SafeAreaView edges={["left", "right"]} style={styles.sheet}>
        <ActionSheetHeader icon={CalendarDays} onClose={() => setMenuVisible(false)} title="Registrar compromiso" />
        <View style={styles.sheetContent}>
          <ActionSheetActions>
            {commitmentKinds.map((kind) => <ActionSheetAction icon={commitmentPresentation[kind].icon} key={kind} label={kind === "nutritionist" ? commitmentPresentation[kind].label : commitmentRegistrationTitle[kind]} onPress={() => openRegistration(kind)} />)}
          </ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
    <ActionSheetModal onRequestClose={() => setActionsVisible(false)} visible={actionsVisible}>
      <SafeAreaView edges={["left", "right"]} style={styles.sheet}>
        <ActionSheetHeader icon={MoreHorizontal} onClose={() => setActionsVisible(false)} title="Opciones de compromisos" />
        <View style={styles.sheetContent}>
          <ActionSheetActions>
            <ActionSheetAction icon={Bell} label="Configurar notificaciones de compromisos" onPress={() => { setActionsVisible(false); router.push("/calendar/commitment-notifications" as Href); }} />
          </ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  </>;
}

const styles = StyleSheet.create({
  calendarSection: { paddingVertical: tokens.spacing.sm },
  commitmentDot: { borderRadius: 3, height: 5, width: 5 },
  commitmentDots: { bottom: 4, flexDirection: "row", gap: 2, position: "absolute" },
  content: { gap: tokens.spacing.lg },
  empty: { color: tokens.color.textMuted, fontSize: 13 },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: tokens.spacing.sm },
  gridDate: { alignItems: "center", borderColor: "transparent", borderRadius: 10, borderWidth: 1, justifyContent: "center", minHeight: 40, width: "13.5%" },
  gridDateAdjacent: { opacity: 0.45 },
  gridDateFilled: { backgroundColor: `${tokens.color.dailyPlan}2E` },
  gridDateUpcomingFilled: { backgroundColor: `${tokens.color.dailyPlan}59` },
  gridDateSelected: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault },
  gridHeader: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center", width: "13.5%" },
  gridNumber: { color: tokens.color.textMain, fontSize: 14, fontWeight: "500" },
  gridNumberPast: { opacity: 0.8 },
  gridNumberWithPlan: { color: tokens.color.textMain, fontWeight: "700" },
  header: { gap: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  headerIcon: { alignItems: "center", borderRadius: tokens.radius.md, height: 40, justifyContent: "center", width: 40 },
  headerIcons: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  hint: { color: tokens.color.textMuted, fontSize: 12, lineHeight: 18, marginTop: tokens.spacing.sm },
  listTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: tokens.weight.semibold },
  monthArrow: { alignItems: "center", height: 36, justifyContent: "center", width: 36 },
  monthNavigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: tokens.spacing.md },
  monthTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: tokens.weight.semibold },
  pressed: { opacity: 0.65 },
  sheet: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  sheetContent: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  stickyHeader: { paddingTop: tokens.spacing.sm },
  subtitle: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  title: { color: tokens.color.textMain, fontSize: tokens.type.title, fontWeight: tokens.weight.semibold, lineHeight: 32 },
});
