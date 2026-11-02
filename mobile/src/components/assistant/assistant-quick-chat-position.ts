export function clampQuickChatButtonOffset(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, value));
}

export function nearestQuickChatHorizontalEdge(value: number, leftEdge: number, rightEdge: number) {
  const bounded = clampQuickChatButtonOffset(value, leftEdge, rightEdge);
  return bounded - leftEdge <= rightEdge - bounded ? leftEdge : rightEdge;
}

export function quickChatHorizontalEdgeForRelease(releaseX: number, viewportWidth: number, leftEdge: number, rightEdge: number) {
  return releaseX <= viewportWidth / 2 ? leftEdge : rightEdge;
}
