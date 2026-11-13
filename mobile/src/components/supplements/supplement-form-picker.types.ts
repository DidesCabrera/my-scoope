export type SupplementFormPickerProps = {
  label: string;
  onChange(value: string): void;
  onExpandedChange?(expanded: boolean): void;
  options: { label: string; value: string }[];
  value: string;
};
