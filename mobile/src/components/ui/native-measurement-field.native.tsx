import { Picker } from "@react-native-picker/picker";
import { Check, ChevronDown, Ruler, Scale } from "lucide-react-native";
import { useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import { recordWheelPickerInteraction } from "@/observability/sentry";
import type { NativeMeasurementFieldProps } from "./native-measurement-field.types";
import { NativeWheelAdornment } from "./native-wheel-adornment";
import { nativeWheelMetrics } from "./native-wheel-metrics";
import {
  HEIGHT_VALUES,
  PORTION_VALUES,
  heightFromValue,
  portionFromValue,
  WEIGHT_GRAM_VALUES,
  WEIGHT_KILOGRAM_VALUES,
  weightPartsFromValue,
  weightValueFromParts,
} from "./native-measurement-values";

function displayValue(value: string, kind: NativeMeasurementFieldProps["kind"], unit: "g" | "ml" = "g"): string {
  if (!value) return kind === "height" ? "Seleccionar altura" : kind === "portion" ? "Seleccionar porción" : "Seleccionar peso";
  if (kind === "height") return `${heightFromValue(value)} cm`;
  if (kind === "portion") return `${portionFromValue(value).toLocaleString("es-CL")} ${unit}`;
  const { grams, kilograms } = weightPartsFromValue(value);
  return grams ? `${kilograms},${grams / 100} kg` : `${kilograms} kg`;
}

export function NativeMeasurementField({ containerStyle, defaultValue, disabled = false, iconColor = tokens.color.textMuted, inlineLabel = false, inputStyle, kind, label, labelStyle, onChange, unit = "g", value }: NativeMeasurementFieldProps) {
  const pickerValue = value || defaultValue || "";
  const initialWeight = weightPartsFromValue(pickerValue);
  const [visible, setVisible] = useState(false);
  const [height, setHeight] = useState(() => heightFromValue(pickerValue));
  const [portion, setPortion] = useState(() => portionFromValue(pickerValue));
  const [kilograms, setKilograms] = useState(initialWeight.kilograms);
  const [grams, setGrams] = useState(initialWeight.grams);
  const Icon = kind === "height" ? Ruler : Scale;

  const open = () => {
    if (disabled) return;
    if (visible) {
      recordWheelPickerInteraction(kind, "cancel");
      setVisible(false);
      return;
    }
    const nextPickerValue = value || defaultValue || "";
    setHeight(heightFromValue(nextPickerValue));
    setPortion(portionFromValue(nextPickerValue));
    const nextWeight = weightPartsFromValue(nextPickerValue);
    setKilograms(nextWeight.kilograms);
    setGrams(nextWeight.grams);
    recordWheelPickerInteraction(kind, "open");
    setVisible(true);
  };

  const changeHeight = (next: number) => {
    setHeight(next);
  };

  const changePortion = (next: number) => {
    setPortion(next);
  };

  const changeKilograms = (next: number) => {
    const nextGrams = next === 350 ? 0 : grams;
    setKilograms(next);
    setGrams(nextGrams);
  };

  const changeGrams = (next: number) => {
    setGrams(next);
  };

  const commit = () => {
    const nextValue = kind === "height"
      ? String(height)
      : kind === "portion"
        ? String(portion)
        : weightValueFromParts(kilograms, kilograms === 350 ? 0 : grams);
    recordWheelPickerInteraction(kind, "commit");
    onChange(nextValue);
    setVisible(false);
  };

  const pickerStyle = Platform.OS === "ios" ? styles.iosPicker : styles.androidPicker;

  const selector = (
    <Pressable
      accessibilityLabel={`${label}: ${displayValue(value, kind, unit)}`}
      accessibilityRole="button"
      accessibilityState={{ disabled, expanded: visible }}
      disabled={disabled}
      onPress={open}
      style={({ pressed }) => [styles.input, inlineLabel && styles.inlineInput, containerStyle, disabled && styles.disabled, pressed && styles.pressed]}>
      {!inlineLabel ? <Icon color={iconColor} size={18} /> : null}
      <Text style={[styles.value, inlineLabel && styles.inlineValue, inputStyle]}>{displayValue(value, kind, unit)}</Text>
      <ChevronDown color={tokens.color.textSoft} size={18} />
    </Pressable>
  );

  return (
    <View style={styles.field}>
      {inlineLabel ? (
        <View style={styles.inlineFieldRow}>
          <View style={styles.inlineLabelRow}>
            <Icon color={iconColor} size={18} />
            <Text style={[styles.label, labelStyle]}>{label}</Text>
          </View>
          {selector}
        </View>
      ) : (
        <>
          <Text style={[styles.label, labelStyle]}>{label}</Text>
          {selector}
        </>
      )}
      {visible ? (
        <View style={styles.inlinePicker}>
          <View accessibilityLabel={kind === "height" ? "Altura en centímetros" : kind === "portion" ? `Porción en ${unit}` : "Peso en kilos y gramos"} style={styles.pickers}>
            {kind === "height" ? (
              <View style={styles.pickerColumn}>
                <Picker dropdownIconColor={tokens.color.textMain} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(next) => changeHeight(Number(next))} selectedValue={height} style={pickerStyle}>
                  {HEIGHT_VALUES.map((option) => <Picker.Item key={option} label={`${option} cm`} value={option} />)}
                </Picker>
              </View>
            ) : kind === "portion" ? (
              <View style={[styles.pickerColumn, styles.portionPickerColumn]}>
                <Picker dropdownIconColor={tokens.color.textMain} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(next) => changePortion(Number(next))} selectedValue={portion} style={pickerStyle}>
                  {PORTION_VALUES.map((option) => <Picker.Item key={option} label={`${option.toLocaleString("es-CL")} ${unit}`} value={option} />)}
                </Picker>
              </View>
            ) : (
              <>
                <View style={[styles.pickerColumn, styles.weightKilogramsPickerColumn]}>
                  <Picker dropdownIconColor={tokens.color.textMain} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(next) => changeKilograms(Number(next))} selectedValue={kilograms} style={pickerStyle}>
                    {WEIGHT_KILOGRAM_VALUES.map((option) => <Picker.Item key={option} label={String(option)} value={option} />)}
                  </Picker>
                </View>
                <NativeWheelAdornment label="," width={8} />
                <View style={[styles.pickerColumn, styles.weightGramsPickerColumn]}>
                  <Picker dropdownIconColor={tokens.color.textMain} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(next) => changeGrams(Number(next))} selectedValue={grams} style={pickerStyle}>
                    {WEIGHT_GRAM_VALUES.map((option) => <Picker.Item key={option} label={String(option / 100)} value={option} />)}
                  </Picker>
                </View>
                <NativeWheelAdornment label="kg" width={30} />
              </>
            )}
          </View>
          <Pressable accessibilityLabel="Listo" accessibilityRole="button" onPress={commit} style={({ pressed }) => [styles.doneButton, pressed && styles.pressed]}>
            <Check color={tokens.color.interactivePrimary} size={22} strokeWidth={2.6} />
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  androidPicker: { color: tokens.color.textMain, minHeight: 54, width: "100%" },
  disabled: { opacity: 0.45 },
  doneButton: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.pill, bottom: tokens.spacing.sm, height: 40, justifyContent: "center", position: "absolute", right: tokens.spacing.sm, width: 40, zIndex: 2 },
  field: { gap: 7 },
  inlineFieldRow: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  inlineInput: { marginHorizontal: 0, minWidth: 120, width: "40%" },
  inlineLabelRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  inlinePicker: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, overflow: "hidden", position: "relative" },
  input: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, flexDirection: "row", gap: tokens.spacing.sm, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 44, paddingHorizontal: tokens.spacing.lg },
  iosPicker: { color: tokens.color.textMain, height: nativeWheelMetrics.height, width: "100%" },
  label: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  pickerColumn: { flex: 1, minWidth: 0 },
  portionPickerColumn: { flex: 0, width: 180 },
  pickerItem: { color: tokens.color.textMain, fontSize: nativeWheelMetrics.fontSize },
  pickers: { alignItems: "center", flexDirection: "row", justifyContent: "center" },
  pressed: { opacity: 0.72 },
  inlineValue: { textAlign: "right" },
  value: { color: tokens.color.textMain, flex: 1, fontSize: 17 },
  weightGramsPickerColumn: { flex: 0, width: 80 },
  weightKilogramsPickerColumn: { flex: 0, width: 96 },
});
