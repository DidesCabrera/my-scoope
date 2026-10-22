import { DateTimePickerAndroid, type DateTimePickerEvent } from "@react-native-community/datetimepicker";
import { Picker } from "@react-native-picker/picker";
import { CalendarDays, Check, ChevronDown, Clock3 } from "lucide-react-native";
import { useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import { recordWheelPickerInteraction } from "@/observability/sentry";
import type { NativeDateTimeFieldProps } from "./native-date-time-field.types";
import { pickerDateFromValue, pickerValueFromDate } from "./native-date-time-values";
import { committedDateTimeDraft, dateTimeDraftFromDate, type DateTimeDraft } from "./native-picker-draft-values";
import { NativeWheelAdornment } from "./native-wheel-adornment";
import { nativeWheelMetrics } from "./native-wheel-metrics";

const DAY_VALUES = Array.from({ length: 31 }, (_, day) => day + 1);
const HOUR_VALUES = Array.from({ length: 24 }, (_, hour) => hour);
const MONTH_VALUES = Array.from({ length: 12 }, (_, month) => month);

function displayValue(value: string, mode: NativeDateTimeFieldProps["mode"]): string {
  const date = pickerDateFromValue(value, mode);
  if (mode === "time") return value || "Seleccionar hora";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return "Seleccionar fecha";
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(date);
}

export function NativeDateTimeField({
  containerStyle,
  disabled = false,
  hideLabel = false,
  iconColor = tokens.color.textMuted,
  iconInLabel = false,
  inputStyle,
  inlineLabel = false,
  label,
  labelStyle,
  maximumValue,
  minimumValue,
  minuteInterval = 5,
  mode,
  onChange,
  value,
}: NativeDateTimeFieldProps) {
  const [expanded, setExpanded] = useState(false);
  const selected = pickerDateFromValue(value, mode);
  const [draft, setDraft] = useState<DateTimeDraft>(() => dateTimeDraftFromDate(selected));
  const minuteValues = Array.from({ length: Math.ceil(60 / minuteInterval) }, (_, index) => index * minuteInterval);
  const minimumDate = minimumValue ? pickerDateFromValue(minimumValue, "date") : new Date(1900, 0, 1);
  const maximumDate = maximumValue ? pickerDateFromValue(maximumValue, "date") : new Date(new Date().getFullYear() + 100, 11, 31);
  const yearValues = Array.from({ length: maximumDate.getFullYear() - minimumDate.getFullYear() + 1 }, (_, index) => minimumDate.getFullYear() + index);
  const Icon = mode === "date" ? CalendarDays : Clock3;
  const pickerProps = {
    is24Hour: true,
    maximumDate: maximumValue ? pickerDateFromValue(maximumValue, "date") : undefined,
    minimumDate: minimumValue ? pickerDateFromValue(minimumValue, "date") : undefined,
    minuteInterval,
    mode,
    value: selected,
  } as const;

  const handleChange = (event: DateTimePickerEvent, next?: Date) => {
    if (Platform.OS === "android") setExpanded(false);
    if (event.type === "set" && next) onChange(pickerValueFromDate(next, mode));
  };

  const open = () => {
    if (disabled) return;
    if (Platform.OS === "android") {
      DateTimePickerAndroid.open({ ...pickerProps, onChange: handleChange });
      return;
    }
    if (expanded) {
      recordWheelPickerInteraction(mode, "cancel");
      setExpanded(false);
      return;
    }
    setDraft(dateTimeDraftFromDate(selected));
    recordWheelPickerInteraction(mode, "open");
    setExpanded(true);
  };

  const changeTimePart = (part: "hour" | "minute", next: number) => {
    setDraft((current) => ({ ...current, [part]: next }));
  };

  const changeDatePart = (part: "day" | "month" | "year", next: number) => {
    setDraft((current) => ({ ...current, [part]: next }));
  };

  const commit = () => {
    const bounded = committedDateTimeDraft(draft, mode, selected, minimumDate, maximumDate);
    recordWheelPickerInteraction(mode, "commit");
    onChange(pickerValueFromDate(bounded, mode));
    setExpanded(false);
  };

  const input = (
    <Pressable
        accessibilityLabel={`${label}: ${displayValue(value, mode)}`}
        accessibilityRole="button"
        accessibilityState={{ disabled, expanded }}
        disabled={disabled}
        onPress={open}
        style={({ pressed }) => [styles.input, containerStyle, disabled && styles.disabled, pressed && styles.pressed]}>
        {!iconInLabel ? <Icon color={iconColor} size={18} /> : null}
        <Text style={[styles.value, inputStyle]}>{displayValue(value, mode)}</Text>
        <ChevronDown color={tokens.color.textSoft} size={18} />
    </Pressable>
  );

  return (
    <View style={styles.field}>
      {inlineLabel ? (
        <View style={styles.inlineHeader}>
          {!hideLabel ? <View style={styles.inlineLabelGroup}>{iconInLabel ? <Icon color={iconColor} size={18} /> : null}<Text style={[styles.label, labelStyle]}>{label}</Text></View> : null}
          {input}
        </View>
      ) : (
        <>
          {!hideLabel ? <Text style={[styles.label, labelStyle]}>{label}</Text> : null}
          {input}
        </>
      )}
      {Platform.OS === "ios" && expanded ? (
        <View style={styles.inlinePicker}>
          {mode === "time" ? (
            <View accessibilityLabel="Hora en formato de 24 horas" style={styles.timePickerRow}>
              <Picker itemStyle={styles.pickerItem} onValueChange={(next) => changeTimePart("hour", Number(next))} selectedValue={draft.hour} style={styles.timePicker}>
                {HOUR_VALUES.map((hour) => <Picker.Item key={hour} label={String(hour).padStart(2, "0")} value={hour} />)}
              </Picker>
              <NativeWheelAdornment label=":" width={8} />
              <Picker itemStyle={styles.pickerItem} onValueChange={(next) => changeTimePart("minute", Number(next))} selectedValue={draft.minute} style={styles.timePicker}>
                {minuteValues.map((minute) => <Picker.Item key={minute} label={String(minute).padStart(2, "0")} value={minute} />)}
              </Picker>
            </View>
          ) : (
            <View accessibilityLabel="Fecha" style={styles.datePickerRow}>
              <Picker itemStyle={styles.pickerItem} onValueChange={(next) => changeDatePart("day", Number(next))} selectedValue={draft.day} style={styles.dateDayPicker}>
                {DAY_VALUES.map((day) => <Picker.Item key={day} label={String(day)} value={day} />)}
              </Picker>
              <Picker itemStyle={styles.pickerItem} onValueChange={(next) => changeDatePart("month", Number(next))} selectedValue={draft.month} style={styles.dateMonthPicker}>
                {MONTH_VALUES.map((month) => <Picker.Item key={month} label={new Intl.DateTimeFormat("es-CL", { month: "short" }).format(new Date(2024, month, 1))} value={month} />)}
              </Picker>
              <Picker itemStyle={styles.pickerItem} onValueChange={(next) => changeDatePart("year", Number(next))} selectedValue={draft.year} style={styles.dateYearPicker}>
                {yearValues.map((year) => <Picker.Item key={year} label={String(year)} value={year} />)}
              </Picker>
            </View>
          )}
          <Pressable accessibilityLabel="Listo" accessibilityRole="button" onPress={commit} style={({ pressed }) => [styles.doneButton, pressed && styles.pressed]}>
            <Check color={tokens.color.interactivePrimary} size={22} strokeWidth={2.6} />
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  disabled: { opacity: 0.45 },
  doneButton: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.pill, bottom: tokens.spacing.sm, height: 40, justifyContent: "center", position: "absolute", right: tokens.spacing.sm, width: 40, zIndex: 2 },
  field: { gap: 7 },
  inlinePicker: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, overflow: "hidden", position: "relative" },
  inlineHeader: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  inlineLabelGroup: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm },
  input: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, flexDirection: "row", gap: tokens.spacing.sm, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 44, paddingHorizontal: tokens.spacing.lg },
  dateDayPicker: { height: nativeWheelMetrics.height, width: 90 },
  dateMonthPicker: { height: nativeWheelMetrics.height, marginLeft: -8, width: 104 },
  datePickerRow: { alignItems: "center", flexDirection: "row", height: nativeWheelMetrics.height, justifyContent: "center" },
  dateYearPicker: { height: nativeWheelMetrics.height, marginLeft: -8, width: 104 },
  label: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  pickerItem: { color: tokens.color.textMain, fontSize: nativeWheelMetrics.fontSize },
  pressed: { opacity: 0.72 },
  timePicker: { height: nativeWheelMetrics.height, width: nativeWheelMetrics.compactColumnWidth },
  timePickerRow: { alignItems: "center", flexDirection: "row", height: nativeWheelMetrics.height, justifyContent: "center" },
  value: { color: tokens.color.textMain, flex: 1, fontSize: 17 },
});
