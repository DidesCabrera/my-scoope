import { type Href, useRouter } from "expo-router";
import { CalendarCheck2, CalendarClock, CalendarDays, ChevronRight, Plus, type LucideIcon } from "lucide-react-native";
import { useId, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import type { EmptyDaySituation } from "@/components/home/home-empty-day";
import { commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { Card } from "@/components/ui";
import { tokens } from "@/design/tokens";

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long" }).format(new Date(`${value}T12:00:00`));
}

function NoticeGradient({ color }: { color: string }) {
  const gradientId = useId().replace(/:/g, "");
  const [size, setSize] = useState({ width: 0, height: 0 });
  const gradientLength = size.width * Math.cos(Math.PI / 6) + size.height * Math.sin(Math.PI / 6);

  return <View onLayout={({ nativeEvent: { layout } }) => {
    setSize((current) => current.width === layout.width && current.height === layout.height ? current : { width: layout.width, height: layout.height });
  }} pointerEvents="none" style={StyleSheet.absoluteFill}>
    {size.width && size.height ? <Svg height={size.height} width={size.width}>
      <Defs>
        <LinearGradient gradientUnits="userSpaceOnUse" id={gradientId} x1={0} x2={gradientLength * Math.cos(Math.PI / 6)} y1={0} y2={gradientLength * Math.sin(Math.PI / 6)}>
          <Stop offset="0" stopColor={color} stopOpacity={0.2} />
          <Stop offset="1" stopColor={color} stopOpacity={0.13} />
        </LinearGradient>
      </Defs>
      <Rect fill={`url(#${gradientId})`} height={size.height} width={size.width} />
    </Svg> : null}
  </View>;
}

function HomeEmptyNotice({ color, firstActionLabel, icon: Icon, message, onFirstAction, title }: {
  color: string;
  firstActionLabel: string;
  icon: LucideIcon;
  message: string;
  onFirstAction(): void;
  title: string;
}) {
  const router = useRouter();
  return <Card style={styles.noticeCard}>
    <NoticeGradient color={color} />
    <View style={styles.noticeCopy}>
      <View style={styles.heading}>
        <View style={[styles.noticeIcon, { backgroundColor: `${color}80` }]}><Icon color={tokens.color.entityIconForeground} size={16} strokeWidth={2.2} /></View>
        <Text accessibilityRole="header" adjustsFontSizeToFit minimumFontScale={0.8} numberOfLines={1} style={styles.noticeTitle}>{title}</Text>
      </View>
      <Text style={styles.noticeMessage}>{message}</Text>
    </View>
    <View style={styles.noticeActions}>
      <Pressable accessibilityLabel={firstActionLabel} accessibilityRole="button" hitSlop={6} onPress={onFirstAction} style={({ pressed }) => [styles.noticeAction, { backgroundColor: `${color}33` }, pressed && styles.noticeActionPressed]}>
        <Plus color={tokens.color.entityIconForeground} size={14} strokeWidth={2.2} />
        <Text adjustsFontSizeToFit minimumFontScale={0.75} numberOfLines={1} style={styles.noticeActionLabel}>{firstActionLabel}</Text>
      </Pressable>
      <Pressable accessibilityLabel="Ver calendario" accessibilityRole="button" hitSlop={6} onPress={() => router.push("/calendar" as Href)} style={({ pressed }) => [styles.noticeAction, { backgroundColor: `${color}33` }, pressed && styles.noticeActionPressed]}>
        <CalendarDays color={tokens.color.entityIconForeground} size={14} strokeWidth={2.2} />
        <ChevronRight color={tokens.color.entityIconForeground} size={14} strokeWidth={2.2} />
      </Pressable>
    </View>
  </Card>;
}

export function HomeEmptyDayNotice({ localDate, situation }: { localDate: string; situation: EmptyDaySituation }) {
  const router = useRouter();
  const planned = situation.kind === "planned";
  const message = planned
    ? `Tienes una minuta programada para ${situation.scheduledPlanDate ? `el ${dateLabel(situation.scheduledPlanDate)}` : "una fecha futura"}.`
    : situation.kind === "unknown"
      ? "Revisa tu calendario y elige una minuta para hoy."
      : "Agrega una minuta o programa al calendario.";

  return <HomeEmptyNotice color={tokens.color.dailyPlan} firstActionLabel="Minuta para hoy" icon={CalendarClock} message={message} onFirstAction={() => router.push(`/calendar/days/${localDate}?origin=home&section=assign` as Href)} title="Hoy no tienes una minuta" />;
}

export function HomeEmptyCommitmentsNotice({ nextDate, onAdd }: { nextDate?: string; onAdd(): void }) {
  const message = nextDate
    ? `Tienes compromisos programados para el ${dateLabel(nextDate)}.`
    : "Agrega un compromiso o revisa tu calendario.";
  return <HomeEmptyNotice color={commitmentPresentation.nutritionist.color} firstActionLabel="Compromiso para hoy" icon={CalendarCheck2} message={message} onFirstAction={onAdd} title="Hoy no tienes compromisos" />;
}

const styles = StyleSheet.create({
  heading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  noticeAction: { alignItems: "center", borderRadius: 999, flexDirection: "row", gap: 4, justifyContent: "center", minHeight: 34, paddingHorizontal: 12 },
  noticeActionLabel: { color: tokens.color.entityIconForeground, fontSize: 12, fontWeight: "700" },
  noticeActionPressed: { opacity: 0.72 },
  noticeActions: { alignSelf: "stretch", flexDirection: "row", gap: tokens.spacing.xs, justifyContent: "space-between", marginTop: 12 },
  noticeCard: { backgroundColor: tokens.color.surfaceApp, borderWidth: 0, overflow: "hidden" },
  noticeCopy: { gap: tokens.spacing.sm },
  noticeIcon: { alignItems: "center", borderRadius: tokens.radius.sm, height: 26, justifyContent: "center", width: 26 },
  noticeTitle: { color: tokens.color.textMain, flex: 1, fontSize: 19, fontWeight: tokens.weight.extraBold, lineHeight: 25, minWidth: 0 },
  noticeMessage: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
});
