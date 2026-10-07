import { Picker } from "@react-native-picker/picker";
import { ChevronDown, Ruler, Scale } from "lucide-react-native";
import { useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { tokens } from "@/design/tokens";
import { ActionSheetHeader, ActionSheetModal } from "./action-sheet-modal";
import { Button } from "./controls";
import type { NativeMeasurementFieldProps } from "./native-measurement-field.types";
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
  return grams ? `${kilograms} kg ${grams} g` : `${kilograms} kg`;
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
    setVisible(true);
  };

  const save = () => {
    onChange(kind === "height" ? String(height) : weightValueFromParts(kilograms, grams));
    setVisible(false);
  };

  const pickerStyle = Platform.OS === "ios" ? styles.iosPicker : styles.androidPicker;

  return (
    <>
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
      </View>

      <ActionSheetModal onRequestClose={() => setVisible(false)} visible={visible}>
        <SafeAreaView edges={["left", "right"]} style={styles.sheet}>
          <ActionSheetHeader icon={Icon} onClose={() => setVisible(false)} title={kind === "height" ? "Seleccionar altura" : "Seleccionar peso"} />
          <View style={styles.sheetContent}>
            <View accessibilityLabel={kind === "height" ? "Altura en centímetros" : "Peso en kilos y gramos"} style={styles.pickers}>
              {kind === "height" ? (
                <View style={styles.pickerColumn}>
                  <Picker dropdownIconColor={tokens.color.textMain} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(next) => setHeight(Number(next))} selectedValue={height} style={pickerStyle}>
                    {HEIGHT_VALUES.map((option) => <Picker.Item key={option} label={`${option} cm`} value={option} />)}
                  </Picker>
                </View>
              ) : (
                <>
                  <View style={styles.pickerColumn}>
                    <Text style={styles.unitLabel}>KILOS</Text>
                    <Picker dropdownIconColor={tokens.color.textMain} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(next) => { const selected = Number(next); setKilograms(selected); if (selected === 350) setGrams(0); }} selectedValue={kilograms} style={pickerStyle}>
                      {WEIGHT_KILOGRAM_VALUES.map((option) => <Picker.Item key={option} label={`${option} kg`} value={option} />)}
                    </Picker>
                  </View>
                  <View style={styles.pickerColumn}>
                    <Text style={styles.unitLabel}>GRAMOS</Text>
                    <Picker dropdownIconColor={tokens.color.textMain} enabled={kilograms < 350} itemStyle={styles.pickerItem} mode="dropdown" onValueChange={(next) => setGrams(Number(next))} selectedValue={grams} style={pickerStyle}>
                      {WEIGHT_GRAM_VALUES.map((option) => <Picker.Item key={option} label={`${option} g`} value={option} />)}
                    </Picker>
                  </View>
                </>
              )}
            </View>
            <Text accessibilityLiveRegion="polite" style={styles.summary}>{kind === "height" ? `${height} centímetros` : displayValue(weightValueFromParts(kilograms, grams), "weight")}</Text>
            <Button bleed={false} label="Listo" onPress={save} />
            <Button bleed={false} label="Cancelar" onPress={() => setVisible(false)} variant="secondary" />
          </View>
        </SafeAreaView>
      </ActionSheetModal>
    </>
  );
}

const styles = StyleSheet.create({
  androidPicker: { color: tokens.color.textMain, minHeight: 54, width: "100%" },
  disabled: { opacity: 0.45 },
  field: { gap: 7 },
  input: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, flexDirection: "row", gap: tokens.spacing.sm, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 44, paddingHorizontal: tokens.spacing.lg },
  iosPicker: { color: tokens.color.textMain, height: 180, width: "100%" },
  label: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  pickerColumn: { flex: 1, minWidth: 0 },
  pickerItem: { color: tokens.color.textMain, fontSize: 20 },
  pickers: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  pressed: { opacity: 0.72 },
  sheet: { backgroundColor: tokens.color.surfaceCard, borderTopLeftRadius: tokens.radius.card, borderTopRightRadius: tokens.radius.card, maxHeight: "88%", overflow: "hidden" },
  sheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  summary: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold, textAlign: "center" },
  unitLabel: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, letterSpacing: 1, textAlign: "center" },
  value: { color: tokens.color.textMain, flex: 1, fontSize: 17 },
});
