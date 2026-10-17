import { Field } from "./controls";
import type { NativeMeasurementFieldProps } from "./native-measurement-field.types";

export function NativeMeasurementField({ inputStyle, kind, inlineLabel = false, label, labelStyle, onChange, value }: NativeMeasurementFieldProps) {
  return <Field inputStyle={[inlineLabel && { textAlign: "right" }, inputStyle]} keyboardType={kind === "weight" ? "decimal-pad" : "number-pad"} label={label} labelStyle={labelStyle} onChangeText={onChange} value={value} />;
}
