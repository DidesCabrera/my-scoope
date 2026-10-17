import type { StyleProp, TextStyle, ViewStyle } from "react-native";

export type NativeDateTimeFieldProps = {
  containerStyle?: StyleProp<ViewStyle>;
  disabled?: boolean;
  hideLabel?: boolean;
  iconColor?: string;
  iconInLabel?: boolean;
  inputStyle?: StyleProp<TextStyle>;
  inlineLabel?: boolean;
  label: string;
  labelStyle?: StyleProp<TextStyle>;
  maximumValue?: string;
  minimumValue?: string;
  minuteInterval?: 1 | 5 | 10 | 15 | 20 | 30;
  mode: "date" | "time";
  onChange(value: string): void;
  value: string;
};
