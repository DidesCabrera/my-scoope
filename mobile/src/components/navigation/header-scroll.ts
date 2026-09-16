export const HEADER_IDENTITY_SCROLL_THRESHOLD = 12;

export function isHeaderIdentityVisible(offsetY: number): boolean {
  return offsetY > HEADER_IDENTITY_SCROLL_THRESHOLD;
}
