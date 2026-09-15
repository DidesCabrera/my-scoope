export type ComparisonRowLayout = { height: number; y: number };

export function reorderedItemsForDrop<T extends { id: string }>(
  items: T[],
  layouts: Record<string, ComparisonRowLayout>,
  sourceIndex: number,
  translationY: number,
): T[] {
  const source = items[sourceIndex];
  const sourceLayout = source ? layouts[source.id] : undefined;
  if (!source || !sourceLayout || !Number.isFinite(translationY)) return items;

  const draggedCenter = sourceLayout.y + sourceLayout.height / 2 + translationY;
  let destinationIndex = sourceIndex;
  let closestDistance = Number.POSITIVE_INFINITY;

  items.forEach((item, index) => {
    const layout = layouts[item.id];
    if (!layout) return;
    const distance = Math.abs(draggedCenter - (layout.y + layout.height / 2));
    if (distance < closestDistance) {
      closestDistance = distance;
      destinationIndex = index;
    }
  });

  if (destinationIndex === sourceIndex) return items;
  const reordered = [...items];
  const [moved] = reordered.splice(sourceIndex, 1);
  reordered.splice(destinationIndex, 0, moved);
  return reordered;
}
