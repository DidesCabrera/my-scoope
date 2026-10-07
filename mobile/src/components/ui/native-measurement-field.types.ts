import type { StyleProp, TextStyle, ViewStyle } from "react-native";

export type NativeMeasurementFieldProps = {
  containerStyle?: StyleProp<ViewStyle>;
  disabled?: boolean;
  inputStyle?: StyleProp<TextStyle>;
  kind: "height" | "weight";
  label: string;
  labelStyle?: StyleProp<TextStyle>;
  onChange(value: string): void;
  value: string;
};
