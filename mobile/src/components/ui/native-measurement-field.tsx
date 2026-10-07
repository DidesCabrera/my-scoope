import { Field } from "./controls";
import type { NativeMeasurementFieldProps } from "./native-measurement-field.types";

export function NativeMeasurementField({ inputStyle, kind, label, labelStyle, onChange, value }: NativeMeasurementFieldProps) {
  return <Field inputStyle={inputStyle} keyboardType={kind === "height" ? "number-pad" : "decimal-pad"} label={label} labelStyle={labelStyle} onChangeText={onChange} value={value} />;
}
