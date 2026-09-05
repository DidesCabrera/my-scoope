export function renderAllocBar({ value, kind, kind2 = "" }) {
  const pct = Math.round(Number(value) || 0);
  const safeKind2 = String(kind2 || "").trim();

  return `
    <div class="picker-alloc-item-wrap">
      ${safeKind2 ? `<p class="kind2">${safeKind2}</p>` : ""}

      <div
        class="picker-alloc-item alloc-bar-comp alloc-bar-comp--kpi"
        style="--alloc: ${pct};"
      >
        <div class="alloc-bar-bg"></div>
        <div class="alloc-bar-fill alloc-bar-fill--${kind}"></div>
        <span class="alloc-bar-text">${pct}%</span>
      </div>
    </div>
  `;
}
