export const SCREEN_BOTTOM_SPACING = 96;

export function screenBottomSpacing(keyboardVisible: boolean, bottomInset: number): number {
  return keyboardVisible ? Math.max(16, bottomInset + 8) : SCREEN_BOTTOM_SPACING;
}
