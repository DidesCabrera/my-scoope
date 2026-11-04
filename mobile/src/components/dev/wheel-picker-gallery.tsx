import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Card, NativeDateTimeField, NativeMeasurementField, textStyles } from "@/components/ui";
import { nextExclusivePicker } from "@/components/ui/exclusive-picker-state";
import { tokens } from "@/design/tokens";

const previewWidths = [
  { label: "iPhone 17 Pro", width: 402 },
  { label: "iPhone compacto", width: 375 },
  { label: "Pantalla mínima", width: 320 },
] as const;

export function WheelPickerGallery() {
  const [date, setDate] = useState("2026-09-30");
  const [time, setTime] = useState("23:55");
  const [height, setHeight] = useState("250");
  const [weight, setWeight] = useState("349.9");
  const [expandedPicker, setExpandedPicker] = useState<string | null>(null);

  return (
    <View style={styles.gallery}>
      <Text style={textStyles.muted}>
        Abre cada selector para comparar las mismas opciones en anchos reales. Los valores extremos ayudan a detectar texto cortado o ruedas que compiten por espacio.
      </Text>
      {previewWidths.map((preview) => {
        const datePicker = `${preview.width}:date`;
        const timePicker = `${preview.width}:time`;
        const heightPicker = `${preview.width}:height`;
        const weightPicker = `${preview.width}:weight`;
        return (
          <View key={preview.width} style={[styles.devicePreview, { width: preview.width }]}>
            <View style={styles.devicePreviewHeader}>
              <Text style={styles.devicePreviewName}>{preview.label}</Text>
              <Text style={styles.devicePreviewWidth}>{preview.width} pt</Text>
            </View>
            <View style={styles.devicePreviewScreen}>
              <Card>
                <NativeDateTimeField
                  expanded={expandedPicker === datePicker}
                  label="Fecha de nacimiento"
                  maximumValue="2026-12-31"
                  minimumValue="1900-01-01"
                  mode="date"
                  onChange={setDate}
                  onExpandedChange={(expanded) => setExpandedPicker((current) => nextExclusivePicker(current, datePicker, expanded))}
                  value={date}
                />
                <NativeDateTimeField expanded={expandedPicker === timePicker} label="Hora de la comida" minuteInterval={5} mode="time" onChange={setTime} onExpandedChange={(expanded) => setExpandedPicker((current) => nextExclusivePicker(current, timePicker, expanded))} value={time} />
                <NativeMeasurementField expanded={expandedPicker === heightPicker} kind="height" label="Estatura" onChange={setHeight} onExpandedChange={(expanded) => setExpandedPicker((current) => nextExclusivePicker(current, heightPicker, expanded))} value={height} />
                <NativeMeasurementField expanded={expandedPicker === weightPicker} kind="weight" label="Peso" onChange={setWeight} onExpandedChange={(expanded) => setExpandedPicker((current) => nextExclusivePicker(current, weightPicker, expanded))} value={weight} />
              </Card>
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  devicePreview: {
    alignSelf: "center",
    backgroundColor: tokens.color.surfacePage,
    borderColor: tokens.color.borderStrong,
    borderRadius: 30,
    borderWidth: 1,
    maxWidth: "100%",
    overflow: "hidden",
  },
  devicePreviewHeader: {
    alignItems: "center",
    borderBottomColor: tokens.color.borderSoft,
    borderBottomWidth: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: tokens.spacing.screen,
    paddingVertical: tokens.spacing.md,
  },
  devicePreviewName: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  devicePreviewScreen: { paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.lg },
  devicePreviewWidth: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"] },
  gallery: { gap: tokens.spacing.lg, minWidth: 0, width: "100%" },
});
