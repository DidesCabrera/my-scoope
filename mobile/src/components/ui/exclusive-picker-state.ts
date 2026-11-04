export function nextExclusivePicker<Key extends string>(
  current: Key | null,
  picker: Key,
  expanded: boolean,
): Key | null {
  if (expanded) return picker;
  return current === picker ? null : current;
}
