import type { StyleProp, TextStyle, ViewStyle } from "react-native";

export type NativeMeasurementFieldProps = {
  containerStyle?: StyleProp<ViewStyle>;
  defaultValue?: string;
  disabled?: boolean;
  iconColor?: string;
  inlineLabel?: boolean;
  inputStyle?: StyleProp<TextStyle>;
  kind: "height" | "portion" | "weight";
  label: string;
  labelStyle?: StyleProp<TextStyle>;
  onChange(value: string): void;
  unit?: "g" | "ml";
  value: string;
};
