type SupplementIntakeSelection = {
  dailyPlanId: string;
  intakeId: string;
  selectionSession: string;
  supplementId: number;
};

const pendingSelections = new Map<string, SupplementIntakeSelection>();

function selectionKey(dailyPlanId: string, intakeId: string) {
  return `${dailyPlanId}:${intakeId}`;
}

export function stageSupplementIntakeSelection(selection: SupplementIntakeSelection) {
  pendingSelections.set(selectionKey(selection.dailyPlanId, selection.intakeId), selection);
}

export function consumeSupplementIntakeSelection(dailyPlanId: string, intakeId: string) {
  const key = selectionKey(dailyPlanId, intakeId);
  const selection = pendingSelections.get(key);
  pendingSelections.delete(key);
  return selection;
}
