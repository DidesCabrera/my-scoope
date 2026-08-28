import { Pressable, StyleSheet, Text } from "react-native";

import { tokens } from "@/design/tokens";

type PickerCardActionProps = {
  label: string;
  onPress(): void;
  subject: string;
};

export function PickerCardAction({ label, onPress, subject }: PickerCardActionProps) {
  return (
    <Pressable
      accessibilityLabel={`${label}: ${subject}`}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.action, pressed && styles.pressed]}>
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  action: {
    alignItems: "center",
    backgroundColor: tokens.color.textMain,
    borderRadius: tokens.radius.pill,
    justifyContent: "center",
    minHeight: 38,
    minWidth: 112,
    paddingHorizontal: tokens.spacing.lg,
  },
  label: { color: tokens.color.surfaceApp, fontSize: tokens.type.caption, fontWeight: "800" },
  pressed: { opacity: 0.68 },
});
