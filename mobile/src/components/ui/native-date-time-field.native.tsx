import { DateTimePickerAndroid, type DateTimePickerEvent } from "@react-native-community/datetimepicker";
import { Picker } from "@react-native-picker/picker";
import { CalendarDays, ChevronDown, Clock3 } from "lucide-react-native";
import { useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import type { NativeDateTimeFieldProps } from "./native-date-time-field.types";
import { pickerDateFromValue, pickerValueFromDate } from "./native-date-time-values";
import { NativeWheelAdornment } from "./native-wheel-adornment";
import { nativeWheelMetrics } from "./native-wheel-metrics";

function displayValue(value: string, mode: NativeDateTimeFieldProps["mode"]): string {
  const date = pickerDateFromValue(value, mode);
  if (mode === "time") return value || "Seleccionar hora";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return "Seleccionar fecha";
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(date);
}

export function NativeDateTimeField({
  containerStyle,
  disabled = false,
  inputStyle,
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
  const hourValues = Array.from({ length: 24 }, (_, hour) => hour);
  const minuteValues = Array.from({ length: Math.ceil(60 / minuteInterval) }, (_, index) => index * minuteInterval);
  const minimumDate = minimumValue ? pickerDateFromValue(minimumValue, "date") : new Date(1900, 0, 1);
  const maximumDate = maximumValue ? pickerDateFromValue(maximumValue, "date") : new Date(new Date().getFullYear() + 100, 11, 31);
  const yearValues = Array.from({ length: maximumDate.getFullYear() - minimumDate.getFullYear() + 1 }, (_, index) => minimumDate.getFullYear() + index);
  const monthValues = Array.from({ length: 12 }, (_, month) => month);
  const dayValues = Array.from({ length: new Date(selected.getFullYear(), selected.getMonth() + 1, 0).getDate() }, (_, day) => day + 1);
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
    setExpanded((current) => !current);
  };

  const changeTimePart = (part: "hour" | "minute", next: number) => {
    const updated = new Date(selected);
    if (part === "hour") updated.setHours(next);
    else updated.setMinutes(next);
    onChange(pickerValueFromDate(updated, "time"));
  };

  const changeDatePart = (part: "day" | "month" | "year", next: number) => {
    const year = part === "year" ? next : selected.getFullYear();
    const month = part === "month" ? next : selected.getMonth();
    const lastDay = new Date(year, month + 1, 0).getDate();
    const day = Math.min(part === "day" ? next : selected.getDate(), lastDay);
    const updated = new Date(year, month, day);
    const bounded = updated < minimumDate ? minimumDate : updated > maximumDate ? maximumDate : updated;
    onChange(pickerValueFromDate(bounded, "date"));
  };

  return (
    <View style={styles.field}>
      <Text style={[styles.label, labelStyle]}>{label}</Text>
      <Pressable
        accessibilityLabel={`${label}: ${displayValue(value, mode)}`}
        accessibilityRole="button"
        accessibilityState={{ disabled, expanded }}
        disabled={disabled}
        onPress={open}
        style={({ pressed }) => [styles.input, containerStyle, disabled && styles.disabled, pressed && styles.pressed]}>
        <Icon color={tokens.color.textMuted} size={18} />
        <Text style={[styles.value, inputStyle]}>{displayValue(value, mode)}</Text>
        <ChevronDown color={tokens.color.textSoft} size={18} />
      </Pressable>
      {Platform.OS === "ios" && expanded ? (
        <View style={styles.inlinePicker}>
          {mode === "time" ? (
            <View accessibilityLabel="Hora en formato de 24 horas" style={styles.timePickerRow}>
              <Picker itemStyle={styles.pickerItem} onValueChange={(next) => changeTimePart("hour", Number(next))} selectedValue={selected.getHours()} style={styles.timePicker}>
                {hourValues.map((hour) => <Picker.Item key={hour} label={String(hour).padStart(2, "0")} value={hour} />)}
              </Picker>
              <NativeWheelAdornment label=":" width={16} />
              <Picker itemStyle={styles.pickerItem} onValueChange={(next) => changeTimePart("minute", Number(next))} selectedValue={selected.getMinutes()} style={styles.timePicker}>
                {minuteValues.map((minute) => <Picker.Item key={minute} label={String(minute).padStart(2, "0")} value={minute} />)}
              </Picker>
            </View>
          ) : (
            <View accessibilityLabel="Fecha" style={styles.datePickerRow}>
              <Picker itemStyle={styles.pickerItem} onValueChange={(next) => changeDatePart("day", Number(next))} selectedValue={selected.getDate()} style={styles.dateDayPicker}>
                {dayValues.map((day) => <Picker.Item key={day} label={String(day)} value={day} />)}
              </Picker>
              <Picker itemStyle={styles.pickerItem} onValueChange={(next) => changeDatePart("month", Number(next))} selectedValue={selected.getMonth()} style={styles.dateMonthPicker}>
                {monthValues.map((month) => <Picker.Item key={month} label={new Intl.DateTimeFormat("es-CL", { month: "short" }).format(new Date(2024, month, 1))} value={month} />)}
              </Picker>
              <Picker itemStyle={styles.pickerItem} onValueChange={(next) => changeDatePart("year", Number(next))} selectedValue={selected.getFullYear()} style={styles.dateYearPicker}>
                {yearValues.map((year) => <Picker.Item key={year} label={String(year)} value={year} />)}
              </Picker>
            </View>
          )}
          <Pressable accessibilityRole="button" onPress={() => setExpanded(false)} style={styles.doneButton}>
            <Text style={styles.doneLabel}>Listo</Text>
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  disabled: { opacity: 0.45 },
  doneButton: { alignItems: "center", alignSelf: "flex-end", minHeight: 44, justifyContent: "center", paddingHorizontal: tokens.spacing.lg },
  doneLabel: { color: tokens.color.interactivePrimary, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  field: { gap: 7 },
  inlinePicker: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, overflow: "hidden", paddingBottom: tokens.spacing.xs },
  input: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, flexDirection: "row", gap: tokens.spacing.sm, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 44, paddingHorizontal: tokens.spacing.lg },
  dateDayPicker: { height: nativeWheelMetrics.height, width: 96 },
  dateMonthPicker: { height: nativeWheelMetrics.height, width: 94 },
  datePickerRow: { alignItems: "center", flexDirection: "row", height: nativeWheelMetrics.height, justifyContent: "center" },
  dateYearPicker: { height: nativeWheelMetrics.height, width: 104 },
  label: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  pickerItem: { color: tokens.color.textMain, fontSize: nativeWheelMetrics.fontSize },
  pressed: { opacity: 0.72 },
  timePicker: { height: nativeWheelMetrics.height, width: nativeWheelMetrics.compactColumnWidth },
  timePickerRow: { alignItems: "center", flexDirection: "row", height: nativeWheelMetrics.height, justifyContent: "center" },
  value: { color: tokens.color.textMain, flex: 1, fontSize: 17 },
});
