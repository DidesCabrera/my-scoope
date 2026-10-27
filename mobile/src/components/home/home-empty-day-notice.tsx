import { type Href, useRouter } from "expo-router";
import { CalendarCheck2, CalendarClock, CalendarDays, ClipboardClock } from "lucide-react-native";
import { useId, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { commitmentDayTitle } from "@/components/calendarization/calendar-commitments";
import type { EmptyDaySituation } from "@/components/home/home-empty-day";
import { Button, Card } from "@/components/ui";
import { tokens } from "@/design/tokens";

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long" }).format(new Date(`${value}T12:00:00`));
}

function PlannedCardGradient() {
  const gradientId = useId().replace(/:/g, "");
  const [size, setSize] = useState({ width: 0, height: 0 });
  const gradientLength = size.width * Math.cos(Math.PI / 6) + size.height * Math.sin(Math.PI / 6);

  return <View onLayout={({ nativeEvent: { layout } }) => {
    setSize((current) => current.width === layout.width && current.height === layout.height ? current : { width: layout.width, height: layout.height });
  }} pointerEvents="none" style={StyleSheet.absoluteFill}>
    {size.width && size.height ? <Svg height={size.height} width={size.width}>
      <Defs>
        <LinearGradient gradientUnits="userSpaceOnUse" id={gradientId} x1={0} x2={gradientLength * Math.cos(Math.PI / 6)} y1={0} y2={gradientLength * Math.sin(Math.PI / 6)}>
          <Stop offset="0" stopColor={tokens.color.dailyPlan} stopOpacity={0.0526} />
          <Stop offset="1" stopColor={tokens.color.dailyPlan} stopOpacity={0} />
        </LinearGradient>
      </Defs>
      <Rect fill={`url(#${gradientId})`} height={size.height} width={size.width} />
    </Svg> : null}
  </View>;
}

export function HomeEmptyDayNotice({ localDate, situation }: { localDate: string; situation: EmptyDaySituation }) {
  const router = useRouter();
  const planned = situation.kind === "planned";
  const commitment = situation.kind === "commitment";
  const Icon = commitment ? CalendarCheck2 : CalendarDays;
  const title = planned
    ? `Hoy no tienes una minuta. Tienes una minuta programada para ${situation.scheduledPlanDate ? `el ${dateLabel(situation.scheduledPlanDate)}` : "una fecha futura"}.`
    : commitment
      ? "Hoy no tienes una minuta. Agrega una minuta o programa al calendario."
      : situation.kind === "empty"
        ? "Hoy no tienes una minuta. Agrega una minuta o programa al calendario."
        : "Hoy no tienes una minuta planificada";
  const description = commitment
      ? `${commitmentDayTitle[situation.commitment.kind]} · ${dateLabel(situation.commitment.calendar_date)}. Revisa lo que agendaste y prepara tu día.`
      : situation.kind === "unknown"
        ? "Revisa tu calendario para ver tus próximos planes y compromisos. Empieza con las opciones de abajo."
        : null;
  const onPress = () => {
    if (commitment) {
      router.push(`/calendar/commitments/${situation.commitment.id}?date=${situation.commitment.calendar_date}` as Href);
    } else {
      router.push("/calendar" as Href);
    }
  };

  return <Card accent={planned ? undefined : tokens.color.program} style={planned ? styles.plannedCard : undefined}>
    {planned ? <PlannedCardGradient /> : null}
    <View style={[styles.heading, planned && styles.plannedHeading]}>
      {planned ? <View style={styles.plannedIcon}><CalendarClock color={tokens.color.entityIconForeground} size={21} strokeWidth={2.2} /></View> : <Icon color={tokens.color.program} size={23} strokeWidth={2.1} />}
      <Text accessibilityRole={planned ? undefined : "header"} style={planned ? styles.plannedText : styles.title}>{title}</Text>
    </View>
    {description ? <Text style={styles.description}>{description}</Text> : null}
    {planned ? (
      <View style={styles.plannedActions}>
        <Pressable accessibilityLabel="Elegir minuta para hoy" accessibilityRole="button" hitSlop={6} onPress={() => router.push(`/calendar/days/${localDate}?origin=home&section=assign` as Href)} style={({ pressed }) => [styles.plannedAction, pressed && styles.plannedActionPressed]}>
          <ClipboardClock color={tokens.color.entityIconForeground} size={14} strokeWidth={2.2} />
          <Text style={styles.plannedActionLabel}>Elegir minuta para hoy</Text>
        </Pressable>
        <Pressable accessibilityLabel="Ver calendario" accessibilityRole="button" hitSlop={6} onPress={onPress} style={({ pressed }) => [styles.plannedAction, pressed && styles.plannedActionPressed]}>
          <CalendarDays color={tokens.color.entityIconForeground} size={14} strokeWidth={2.2} />
          <Text style={styles.plannedActionLabel}>Ver calendario</Text>
        </Pressable>
      </View>
    ) : <Button label={commitment ? "Ver compromiso" : "Ver calendario"} onPress={onPress} variant="secondary" />}
  </Card>;
}

const styles = StyleSheet.create({
  description: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  heading: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.sm },
  plannedAction: { alignItems: "center", borderColor: tokens.color.dailyPlan, borderRadius: 999, borderWidth: 1, flexDirection: "row", gap: 4, justifyContent: "center", minHeight: 34, paddingHorizontal: 13 },
  plannedActionLabel: { color: tokens.color.entityIconForeground, fontSize: 12, fontWeight: "700" },
  plannedActionPressed: { opacity: 0.72 },
  plannedActions: { alignSelf: "flex-end", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.xs, justifyContent: "flex-end" },
  plannedCard: { backgroundColor: `${tokens.color.dailyPlan}0D`, borderColor: `${tokens.color.dailyPlan}80`, borderWidth: 1, overflow: "hidden", paddingTop: tokens.card.outerPadding - 6 },
  plannedHeading: { gap: tokens.spacing.md },
  plannedIcon: { alignItems: "center", backgroundColor: `${tokens.color.dailyPlan}80`, borderRadius: tokens.radius.md, height: 40, justifyContent: "center", width: 40 },
  plannedText: { color: tokens.color.textMuted, flex: 1, fontSize: tokens.type.body, lineHeight: 23, transform: [{ translateY: -4 }] },
  title: { color: tokens.color.textMain, flex: 1, fontSize: 19, fontWeight: tokens.weight.extraBold, lineHeight: 25 },
});
