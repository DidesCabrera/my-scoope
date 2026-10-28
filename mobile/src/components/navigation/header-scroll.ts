export const HEADER_IDENTITY_SCROLL_THRESHOLD = 12;
const HEADER_IDENTITY_SCROLL_HYSTERESIS = 6;

export function isHeaderIdentityVisible(offsetY: number): boolean {
  return offsetY > HEADER_IDENTITY_SCROLL_THRESHOLD;
}

export function nextHeaderIdentityVisibility(offsetY: number, visible: boolean): boolean {
  if (!Number.isFinite(offsetY)) return visible;
  return visible
    ? offsetY > HEADER_IDENTITY_SCROLL_THRESHOLD - HEADER_IDENTITY_SCROLL_HYSTERESIS
    : offsetY > HEADER_IDENTITY_SCROLL_THRESHOLD + HEADER_IDENTITY_SCROLL_HYSTERESIS;
}
