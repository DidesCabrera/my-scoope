import { Picker } from "@react-native-picker/picker";
import { ChevronDown, Ruler, Scale } from "lucide-react-native";
import { useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import type { NativeMeasurementFieldProps } from "./native-measurement-field.types";
import { NativeWheelAdornment } from "./native-wheel-adornment";
import { nativeWheelMetrics } from "./native-wheel-metrics";
import {
  HEIGHT_VALUES,
  heightFromValue,
  WEIGHT_GRAM_VALUES,
  WEIGHT_KILOGRAM_VALUES,
  weightPartsFromValue,
  weightValueFromParts,
} from "./native-measurement-values";

function displayValue(value: string, kind: NativeMeasurementFieldProps["kind"]): string {
  if (!value) return kind === "height" ? "Seleccionar altura" : "Seleccionar peso";
  if (kind === "height") return `${heightFromValue(value)} cm`;
  const { grams, kilograms } = weightPartsFromValue(value);
  return grams ? `${kilograms},${grams / 100} kg` : `${kilograms} kg`;
}

export function NativeMeasurementField({ containerStyle, disabled = false, inputStyle, kind, label, labelStyle, onChange, value }: NativeMeasurementFieldProps) {
  const initialWeight = weightPartsFromValue(value);
  const [visible, setVisible] = useState(false);
  const [height, setHeight] = useState(() => heightFromValue(value));
  const [kilograms, setKilograms] = useState(initialWeight.kilograms);
  const [grams, setGrams] = useState(initialWeight.grams);
  const Icon = kind === "height" ? Ruler : Scale;

  const open = () => {
    if (disabled) return;
    setHeight(heightFromValue(value));
    const nextWeight = weightPartsFromValue(value);
    setKilograms(nextWeight.kilograms);
    setGrams(nextWeight.grams);
    setVisible((current) => !current);
  };

  const changeHeight = (next: number) => {
    setHeight(next);
    onChange(String(next));
  };

  const changeKilograms = (next: number) => {
    const nextGrams = next === 350 ? 0 : grams;
    setKilograms(next);
    setGrams(nextGrams);
    onChange(weightValueFromParts(next, nextGrams));
  };

  const changeGrams = (next: number) => {
    setGrams(next);
    onChange(weightValueFromParts(kilograms, next));
  };

  const pickerStyle = Platform.OS === "ios" ? styles.iosPicker : styles.androidPicker;

  return (
    <View style={styles.field}>
      <Text style={[styles.label, labelStyle]}>{label}</Text>
      <Pressable
        accessibilityLabel={`${label}: ${displayValue(value, kind)}`}
        accessibilityRole="button"
        accessibilityState={{ disabled, expanded: visible }}
        disabled={disabled}
        onPress={open}
        style={({ pressed }) => [styles.input, containerStyle, disabled && styles.disabled, pressed && styles.pressed]}>
        <Icon color={tokens.color.textMuted} size={18} />
        <Text style={[styles.value, inputStyle]}>{displayValue(value, kind)}</Text>
        <ChevronDown color={tokens.color.textSoft} size={18} />
      </Pressable>
      {visible ? (
        <View style={styles.inlinePicker}>
          <View accessibilityLabel={kind === "height" ? "Altura en centímetros" : "Peso en kilos y gramos"} style={styles.pickers}>
            {kind === "height" ? (
              <View style={styles.pickerColumn}>
                <Picker dropdownIconColor={tokens.color.textMain} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(next) => changeHeight(Number(next))} selectedValue={height} style={pickerStyle}>
                  {HEIGHT_VALUES.map((option) => <Picker.Item key={option} label={`${option} cm`} value={option} />)}
                </Picker>
              </View>
            ) : (
              <>
                <View style={[styles.pickerColumn, styles.weightPickerColumn]}>
                  <Picker dropdownIconColor={tokens.color.textMain} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(next) => changeKilograms(Number(next))} selectedValue={kilograms} style={pickerStyle}>
                    {WEIGHT_KILOGRAM_VALUES.map((option) => <Picker.Item key={option} label={String(option)} value={option} />)}
                  </Picker>
                </View>
                <NativeWheelAdornment label="," width={16} />
                <View style={[styles.pickerColumn, styles.weightPickerColumn]}>
                  <Picker dropdownIconColor={tokens.color.textMain} enabled={kilograms < 350} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(next) => changeGrams(Number(next))} selectedValue={grams} style={pickerStyle}>
                    {WEIGHT_GRAM_VALUES.map((option) => <Picker.Item key={option} label={String(option / 100)} value={option} />)}
                  </Picker>
                </View>
                <NativeWheelAdornment label="kg" width={30} />
              </>
            )}
          </View>
          <Pressable accessibilityRole="button" onPress={() => setVisible(false)} style={styles.doneButton}>
            <Text style={styles.doneLabel}>Listo</Text>
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  androidPicker: { color: tokens.color.textMain, minHeight: 54, width: "100%" },
  disabled: { opacity: 0.45 },
  doneButton: { alignItems: "center", alignSelf: "flex-end", justifyContent: "center", minHeight: 44, paddingHorizontal: tokens.spacing.lg },
  doneLabel: { color: tokens.color.interactivePrimary, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  field: { gap: 7 },
  inlinePicker: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, overflow: "hidden", paddingBottom: tokens.spacing.xs },
  input: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, flexDirection: "row", gap: tokens.spacing.sm, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 44, paddingHorizontal: tokens.spacing.lg },
  iosPicker: { color: tokens.color.textMain, height: nativeWheelMetrics.height, width: "100%" },
  label: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  pickerColumn: { flex: 1, minWidth: 0 },
  pickerItem: { color: tokens.color.textMain, fontSize: nativeWheelMetrics.fontSize },
  pickers: { alignItems: "center", flexDirection: "row", justifyContent: "center" },
  pressed: { opacity: 0.72 },
  value: { color: tokens.color.textMain, flex: 1, fontSize: 17 },
  weightPickerColumn: { flex: 0, width: nativeWheelMetrics.compactColumnWidth },
});
