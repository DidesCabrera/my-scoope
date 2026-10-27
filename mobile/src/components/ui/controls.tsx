import { useContext, type ReactNode } from "react";
import { Plus } from "lucide-react-native";
import { ActivityIndicator, KeyboardTypeOptions, Pressable, StyleProp, StyleSheet, Text, TextInput, TextStyle, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { tokens } from "@/design/tokens";
import { ButtonSurfaceContext } from "./button-surface-context";

export function Button({
  bleed = true,
  icon,
  label,
  onPress,
  variant = "primary",
  surface,
  multicolorSurface = "muted",
  disabled = false,
  loading = false,
}: {
  bleed?: boolean;
  icon?: ReactNode;
  label: string;
  onPress(): void;
  variant?: "primary" | "secondary" | "surfaceCard" | "chipPrimary" | "danger" | "gradient" | "multicolor";
  surface?: "app" | "card";
  multicolorSurface?: "app" | "muted";
  disabled?: boolean;
  loading?: boolean;
}) {
  const onCard = useContext(ButtonSurfaceContext);
  const gradient = variant === "gradient";
  const multicolor = variant === "multicolor" || gradient;
  const chipPrimary = variant === "chipPrimary";
  const buttonStyle = variant === "primary" ? styles.buttonPrimary : multicolor ? styles.buttonMulticolor : variant === "surfaceCard" ? styles.buttonSurfaceCard : chipPrimary ? styles.buttonChipPrimary : styles.buttonSecondary;
  const textStyle = variant === "primary" || gradient ? styles.buttonPrimaryText : chipPrimary ? styles.buttonChipPrimaryText : styles.buttonSecondaryText;
  const chipHasPlus = chipPrimary && label.startsWith("+ ");
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={chipHasPlus ? label.slice(2) : label}
      accessibilityState={{ disabled: disabled || loading, busy: loading }}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        bleed && !chipPrimary && styles.buttonBleed,
        buttonStyle,
        (variant === "secondary" || variant === "surfaceCard") && (surface === "card" || (surface !== "app" && onCard)) && styles.buttonSecondaryOnCard,
        variant === "danger" && styles.buttonDanger,
        (disabled || loading) && styles.buttonDisabled,
        pressed && styles.buttonPressed,
      ]}>
      {multicolor ? <>
        <Svg aria-hidden pointerEvents="none" style={StyleSheet.absoluteFill}>
          <Defs>
            <LinearGradient id="button-border-macros" x1="0" x2="1" y1="0" y2="1">
              <Stop offset="0" stopColor={tokens.color.protein} />
              <Stop offset="0.5" stopColor={tokens.color.carbs} />
              <Stop offset="1" stopColor={tokens.color.fat} />
            </LinearGradient>
          </Defs>
          <Rect fill="url(#button-border-macros)" height="100%" width="100%" />
        </Svg>
        {!gradient ? <View style={[styles.buttonMulticolorInset, multicolorSurface === "app" && styles.buttonMulticolorInsetApp]} /> : null}
      </> : null}
      {loading ? <ActivityIndicator color={variant === "primary" || gradient ? tokens.color.surfaceApp : tokens.color.textMain} /> : null}
      {!loading ? icon ?? (chipHasPlus ? <Plus color={tokens.color.surfaceApp} size={18} strokeWidth={2.2} /> : null) : null}
      <Text style={[textStyle, variant === "danger" && styles.buttonDangerText]}>{chipHasPlus ? label.slice(2) : label}</Text>
    </Pressable>
  );
}

export function Field({
  hideLabel = false,
  inputStyle,
  label,
  labelIcon,
  labelStyle,
  value,
  onChangeText,
  placeholder,
  keyboardType,
  autoCapitalize = "none",
  autoCorrect,
  maxLength,
  secureTextEntry = false,
}: {
  hideLabel?: boolean;
  inputStyle?: StyleProp<TextStyle>;
  label: string;
  labelIcon?: ReactNode;
  labelStyle?: StyleProp<TextStyle>;
  value: string;
  onChangeText(value: string): void;
  placeholder?: string;
  keyboardType?: KeyboardTypeOptions;
  autoCapitalize?: "none" | "sentences" | "words" | "characters";
  autoCorrect?: boolean;
  maxLength?: number;
  secureTextEntry?: boolean;
}) {
  return (
    <View style={styles.field}>
      {!hideLabel ? <View style={styles.fieldLabelRow}>
        {labelIcon}
        <Text style={[styles.fieldLabel, labelStyle]}>{label}</Text>
      </View> : null}
      <TextInput
        accessibilityLabel={label}
        autoCapitalize={autoCapitalize}
        autoCorrect={autoCorrect}
        keyboardType={keyboardType}
        maxLength={maxLength}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={tokens.color.textSubtle}
        selectionColor={tokens.color.interactivePrimary}
        secureTextEntry={secureTextEntry}
        style={[styles.input, inputStyle]}
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

export function SystemSwitch({ accessibilityLabel, disabled = false, onValueChange, value }: { accessibilityLabel: string; disabled?: boolean; onValueChange(value: boolean): void; value: boolean }) {
  return (
    <Pressable
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="switch"
      accessibilityState={{ checked: value, disabled }}
      disabled={disabled}
      hitSlop={8}
      onPress={() => onValueChange(!value)}
      style={({ pressed }) => [styles.systemSwitch, value && styles.systemSwitchActive, disabled && styles.systemSwitchDisabled, pressed && styles.systemSwitchPressed]}>
      <View style={[styles.systemSwitchKnob, value && styles.systemSwitchKnobActive]} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: { alignItems: "center", borderRadius: tokens.radius.pill, flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "center", minHeight: 44, paddingHorizontal: tokens.spacing.lg },
  buttonBleed: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  buttonPrimary: { backgroundColor: tokens.color.textMain },
  buttonMulticolor: { overflow: "hidden" },
  buttonMulticolorInset: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, bottom: 2, left: 2, position: "absolute", right: 2, top: 2 },
  buttonMulticolorInsetApp: { backgroundColor: tokens.color.surfaceApp },
  buttonSecondary: { backgroundColor: tokens.color.surfaceCard },
  buttonSecondaryOnCard: { backgroundColor: tokens.color.surfaceMuted },
  buttonSurfaceCard: { backgroundColor: tokens.color.surfaceCard },
  buttonChipPrimary: { alignSelf: "stretch", backgroundColor: tokens.color.textMain, borderRadius: tokens.radius.pill, gap: 8, marginHorizontal: -6, minHeight: 44, paddingHorizontal: 16 },
  buttonDanger: { backgroundColor: "transparent", borderColor: tokens.color.danger, borderWidth: 1 },
  buttonDisabled: { opacity: 0.45 },
  buttonPressed: { opacity: 0.72, transform: [{ translateY: 1 }] },
  buttonPrimaryText: { color: tokens.color.surfaceApp, fontSize: tokens.type.body, fontWeight: "800" },
  buttonSecondaryText: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: "700" },
  buttonChipPrimaryText: { color: tokens.color.surfaceApp, fontSize: 16, fontWeight: "700" },
  buttonDangerText: { color: tokens.color.danger },
  field: { gap: 7 },
  systemSwitch: { backgroundColor: tokens.color.borderStrong, borderRadius: tokens.radius.pill, height: 28, padding: 3, width: 48 },
  systemSwitchActive: { backgroundColor: tokens.color.success },
  systemSwitchDisabled: { opacity: 0.45 },
  systemSwitchKnob: { backgroundColor: tokens.color.textMain, borderRadius: 11, height: 22, width: 22 },
  systemSwitchKnobActive: { transform: [{ translateX: 20 }] },
  systemSwitchPressed: { opacity: 0.72 },
  fieldLabelRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  fieldLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  input: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, color: tokens.color.textMain, fontSize: 17, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 44, paddingHorizontal: tokens.spacing.lg },
  choiceRow: { flexDirection: "row", gap: tokens.spacing.sm },
  choice: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.lg, borderWidth: 1, flex: 1, justifyContent: "center", minHeight: 50, paddingHorizontal: 10 },
  choiceSelected: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  choiceText: { color: tokens.color.textMuted, fontSize: 14, fontWeight: "700" },
  choiceTextSelected: { color: tokens.color.surfaceApp },
});
