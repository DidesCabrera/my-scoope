import { Field } from "./controls";
import type { NativeDateTimeFieldProps } from "./native-date-time-field.types";

// Non-native fallback used by TypeScript and static web exports. Metro selects
// the .native implementation on iOS and Android.
export function NativeDateTimeField({ hideLabel, inputStyle, label, labelStyle, mode, onChange, value }: NativeDateTimeFieldProps) {
  return (
    <Field
      inputStyle={inputStyle}
      hideLabel={hideLabel}
      keyboardType="numbers-and-punctuation"
      label={label}
      labelStyle={labelStyle}
      onChangeText={onChange}
      placeholder={mode === "date" ? "AAAA-MM-DD" : "HH:MM"}
      value={value}
    />
  );
}
