type PresetSupplementSelection = {
  presetId: string;
  selectionSession: string;
  supplementId: number;
};

const pendingSelections = new Map<string, PresetSupplementSelection>();

export function stagePresetSupplementSelection(selection: PresetSupplementSelection) {
  pendingSelections.set(selection.presetId, selection);
}

export function consumePresetSupplementSelection(presetId: string) {
  const selection = pendingSelections.get(presetId);
  pendingSelections.delete(presetId);
  return selection;
}
