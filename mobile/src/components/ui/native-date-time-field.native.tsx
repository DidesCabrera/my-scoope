import DateTimePicker, { DateTimePickerAndroid, type DateTimePickerEvent } from "@react-native-community/datetimepicker";
import { CalendarDays, ChevronDown, Clock3 } from "lucide-react-native";
import { useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import type { NativeDateTimeFieldProps } from "./native-date-time-field.types";
import { pickerDateFromValue, pickerValueFromDate } from "./native-date-time-values";

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
          <DateTimePicker {...pickerProps} display="spinner" locale="es-CL" onChange={handleChange} />
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
  label: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  pressed: { opacity: 0.72 },
  value: { color: tokens.color.textMain, flex: 1, fontSize: 17 },
});
