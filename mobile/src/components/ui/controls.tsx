import { ActivityIndicator, KeyboardTypeOptions, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { tokens } from "@/design/tokens";

export function Button({
  label,
  onPress,
  variant = "primary",
  disabled = false,
  loading = false,
}: {
  label: string;
  onPress(): void;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
  loading?: boolean;
}) {
  const buttonStyle = variant === "primary" ? styles.buttonPrimary : styles.buttonSecondary;
  const textStyle = variant === "primary" ? styles.buttonPrimaryText : styles.buttonSecondaryText;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: disabled || loading, busy: loading }}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        buttonStyle,
        variant === "danger" && styles.buttonDanger,
        (disabled || loading) && styles.buttonDisabled,
        pressed && styles.buttonPressed,
      ]}>
      {loading ? <ActivityIndicator color={variant === "primary" ? tokens.color.surfaceApp : tokens.color.textMain} /> : null}
      <Text style={[textStyle, variant === "danger" && styles.buttonDangerText]}>{label}</Text>
    </Pressable>
  );
}

export function Field({
  label,
  value,
  onChangeText,
  placeholder,
  keyboardType,
  autoCapitalize = "none",
  secureTextEntry = false,
}: {
  label: string;
  value: string;
  onChangeText(value: string): void;
  placeholder?: string;
  keyboardType?: KeyboardTypeOptions;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
  secureTextEntry?: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        autoCapitalize={autoCapitalize}
        keyboardType={keyboardType}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={tokens.color.textSubtle}
        selectionColor={tokens.color.interactivePrimary}
        secureTextEntry={secureTextEntry}
        style={styles.input}
        value={value}
      />
    </View>
  );
}

export function ChoiceRow<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange(value: T): void;
}) {
  return (
    <View style={styles.field} accessibilityRole="radiogroup">
      <Text style={styles.fieldLabel}>{label}</Text>
      <View style={styles.choiceRow}>
        {options.map((option) => {
          const selected = option.value === value;
          return (
            <Pressable
              key={option.value}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              onPress={() => onChange(option.value)}
              style={[styles.choice, selected && styles.choiceSelected]}>
              <Text style={[styles.choiceText, selected && styles.choiceTextSelected]}>{option.label}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  button: { alignItems: "center", borderRadius: tokens.radius.lg, flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "center", minHeight: 54, paddingHorizontal: tokens.spacing.lg },
  buttonPrimary: { backgroundColor: tokens.color.textMain },
  buttonSecondary: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderWidth: 1 },
  buttonDanger: { backgroundColor: "transparent", borderColor: tokens.color.danger },
  buttonDisabled: { opacity: 0.45 },
  buttonPressed: { opacity: 0.72, transform: [{ translateY: 1 }] },
  buttonPrimaryText: { color: tokens.color.surfaceApp, fontSize: tokens.type.body, fontWeight: "800" },
  buttonSecondaryText: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: "700" },
  buttonDangerText: { color: tokens.color.danger },
  field: { gap: 7 },
  fieldLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  input: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.lg, borderWidth: 1, color: tokens.color.textMain, fontSize: 17, minHeight: 54, paddingHorizontal: tokens.spacing.lg },
  choiceRow: { flexDirection: "row", gap: tokens.spacing.sm },
  choice: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.lg, borderWidth: 1, flex: 1, justifyContent: "center", minHeight: 50, paddingHorizontal: 10 },
  choiceSelected: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  choiceText: { color: tokens.color.textMuted, fontSize: 14, fontWeight: "700" },
  choiceTextSelected: { color: tokens.color.surfaceApp },
});
