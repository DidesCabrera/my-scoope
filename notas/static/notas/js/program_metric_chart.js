document.addEventListener("DOMContentLoaded", () => {
  const numberFormatter = new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 });
  const decimalFormatter = new Intl.NumberFormat("es-CL", { maximumFractionDigits: 2 });

  function toNumber(value) {
    const number = Number(value || 0);
    return Number.isFinite(number) ? number : 0;
  }

  function formatNumber(value, decimals = 0) {
    const number = toNumber(value);
    if (decimals > 0) {
      return decimalFormatter.format(Number(number.toFixed(decimals)));
    }
    return numberFormatter.format(Math.round(number));
  }

  function heightPercent(value, maxValue) {
    const max = Math.max(toNumber(maxValue), 1);
    return Math.min(Math.max((toNumber(value) / max) * 100, 0), 100);
  }

  function segmentPercent(value, total) {
    const safeTotal = toNumber(total);
    if (!safeTotal) return 0;
    return Math.min(Math.max((toNumber(value) / safeTotal) * 100, 0), 100);
  }

  function makeElement(tag, className, attributes = {}) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    Object.entries(attributes).forEach(([key, value]) => {
      if (value === undefined || value === null) return;
      if (key === "text") {
        element.textContent = value;
      } else if (key === "html") {
        element.innerHTML = value;
      } else {
        element.setAttribute(key, value);
      }
    });
    return element;
  }

  function readChartData(chart) {
    const script = chart.querySelector(".js-program-chart-data");
    if (!script) return null;
    try {
      return JSON.parse(script.textContent || "{}");
    } catch (error) {
      console.warn("Program chart: invalid chart data", error);
      return null;
    }
  }

  function getMetricValues(metric) {
    const bars = Array.isArray(metric.bars) ? metric.bars : [];
    const values = bars
      .filter((bar) => !bar.isEmpty)
      .map((bar) => toNumber(bar.value));
    return values.length ? values : bars.map((bar) => toNumber(bar.value));
  }

  function getRawMetricMax(metric) {
    const values = getMetricValues(metric);
    if (metric.key === "alloc") return 100;
    return Math.max(...values, 1);
  }

  function getMetricScaleStep(metric) {
    if (metric.key === "alloc") return 25;
    if (metric.key === "ppk") return 0.5;
    if (metric.unit === "kcal" || metric.key === "calories") return 500;
    return 50;
  }

  function getMetricMax(metric) {
    if (metric.key === "alloc") return 100;

    const rawMax = getRawMetricMax(metric);
    const step = getMetricScaleStep(metric);
    const scaleMax = Math.ceil(rawMax / step) * step;
    return scaleMax <= rawMax ? scaleMax + step : scaleMax;
  }

  function getMetricTicks(metric, metricMax) {
    const step = getMetricScaleStep(metric);
    const ticks = [];
    for (let tick = step; tick <= metricMax + (step / 1000); tick += step) {
      ticks.push(Number(tick.toFixed(metric.key === "ppk" ? 2 : 0)));
    }
    return ticks;
  }

  function getMetricMin(metric) {
    const values = getMetricValues(metric).filter((value) => value > 0);
    if (metric.key === "alloc") return 0;
    return values.length ? Math.min(...values) : 0;
  }

  function getGuideValues(metric, metricMax) {
    return {
      max: toNumber(metricMax),
      min: getMetricMin(metric),
    };
  }

  function guideYFromValue(value, metricMax, top, bottom) {
    const percent = heightPercent(value, metricMax);
    const drawableHeight = Math.max(bottom - top, 1);
    return Math.min(Math.max(bottom - ((percent / 100) * drawableHeight), top), bottom);
  }

  function renderTabs(chart, data, activeKey) {
    const tabsContainer = chart.querySelector(".js-program-chart-tabs");
    if (!tabsContainer) return [];
    tabsContainer.innerHTML = "";

    return (data.metrics || []).map((metric) => {
      const tab = makeElement("button", "panel-tab program-chart-tab js-program-chart-tab", {
        type: "button",
        role: "tab",
        "data-metric": metric.key,
        "aria-selected": metric.key === activeKey ? "true" : "false",
        text: metric.label,
      });
      tab.classList.toggle("is-active", metric.key === activeKey);
      tabsContainer.appendChild(tab);
      return tab;
    });
  }

  function renderAxis(data, options = {}) {
    const scope = data.scope || "program";
    const labels = Array.isArray(data.axisLabels) ? data.axisLabels : [];
    const axisCount = data.axisCount || (scope === "week" ? labels.length || data.daysCount : data.weeksCount) || 1;
    const axis = makeElement("div", `program-chart-week-axis program-chart-week-axis--${scope}`, {
      style: `--program-chart-axis-count: ${axisCount}; --program-chart-weeks: ${data.weeksCount || 1};`,
      "aria-label": "Etiquetas del gráfico",
    });

    labels.forEach((label) => {
      const mobileLabel = label.mobileLabel || label.label;
      axis.appendChild(makeElement("span", "", {
        "data-mobile-label": mobileLabel,
        text: options.uppercase ? (scope === "week" ? mobileLabel : label.label).toUpperCase() : (scope === "week" ? mobileLabel : label.label),
      }));
    });

    return axis;
  }


  function compactRangeLabel(label, metric) {
    const displayUnit = metric.key === "calories" ? "cal" : (metric.unit || "");
    const cleaned = String(label || "")
      .replace(/\bMin:\s*/gi, "")
      .replace(/\bMax:\s*/gi, "")
      .replace(/\s+/g, " ")
      .trim();
    if (!displayUnit) return cleaned;

    const escapedUnit = displayUnit.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const sourceUnit = metric.key === "calories" ? "(?:kcal|cal)" : escapedUnit;
    const unitPattern = new RegExp(`\\s*${sourceUnit}\\b`, "gi");
    return `${cleaned.replace(unitPattern, "")} ${displayUnit}`;
  }

  function renderRangeBadge(metric, label, modifierKey = "") {
    const modifier = modifierKey ? ` program-chart-axis-header__range--${metric.key}-${modifierKey}` : "";
    const allocInitials = { protein: "P", carbs: "C", fat: "G" };
    const compactLabel = metric.key === "alloc" && modifierKey
      ? `${allocInitials[modifierKey] || String(modifierKey).charAt(0).toUpperCase()} ${String(label).replace(/^\S+\s+/, "")}`
      : label;
    return makeElement("span", `program-chart-axis-header__range program-chart-axis-header__range--${metric.key}${modifier}`, {
      text: compactRangeLabel(compactLabel, metric),
    });
  }

  function renderAxisHeader(metric, options = {}) {
    const header = makeElement("div", "program-chart-axis-header");
    const heading = makeElement("div", "program-chart-axis-header__heading");
    const title = makeElement("h3", "program-chart-axis-header__title", {
      text: metric.label || "Gráfico",
    });
    const unit = makeElement("span", "program-chart-axis-header__unit", {
      text: metric.unit || "",
    });
    const rangeLabels = Array.isArray(metric.rangeLabels) ? metric.rangeLabels : [];
    const rangeGroup = makeElement("div", "program-chart-axis-header__ranges");

    heading.appendChild(title);
    if (metric.unit && !options.hideUnit) heading.appendChild(unit);
    header.appendChild(heading);
    if (rangeLabels.length) {
      rangeLabels.forEach((rangeItem) => {
        rangeGroup.appendChild(renderRangeBadge(metric, `${rangeItem.label} ${rangeItem.value}`, rangeItem.key));
      });
      header.appendChild(rangeGroup);
    } else if (metric.rangeLabel) {
      rangeGroup.appendChild(renderRangeBadge(metric, metric.rangeLabel));
      header.appendChild(rangeGroup);
    }
    return header;
  }

  function groupBarsByWeek(bars, weeksCount) {
    const groups = Array.from({ length: Math.max(weeksCount, 1) }, (_, index) => ({
      weekNumber: index + 1,
      bars: [],
    }));

    (bars || []).forEach((bar) => {
      const weekIndex = Math.max(toNumber(bar.weekNumber) - 1, 0);
      if (!groups[weekIndex]) {
        groups[weekIndex] = { weekNumber: weekIndex + 1, bars: [] };
      }
      groups[weekIndex].bars.push(bar);
    });

    return groups;
  }

  function getChartMinWidth(data) {
    const weeks = Math.min(Math.max(toNumber(data.weeksCount || 1), 1), 12);
    // Business rule: programs are capped at 12 weeks and the viewport should
    // show up to 4 complete weeks before horizontal scroll is needed.
    if ((data.scope || "program") !== "program") return "100%";
    if (weeks <= 4) return "100%";
    return `${weeks * 25}%`;
  }

  function ensureOutlineSvg(plot) {
    let svg = plot.querySelector(":scope > .program-chart-outline-svg");
    if (svg) return svg;

    svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.classList.add("program-chart-outline-svg");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    plot.appendChild(svg);
    return svg;
  }

  function clearOutlineSvg(svg) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
  }

  function ensureGridSvg(plot) {
    let svg = plot.querySelector(":scope > .program-chart-grid-svg");
    if (svg) return svg;

    svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.classList.add("program-chart-grid-svg");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    plot.appendChild(svg);
    return svg;
  }

  function makeGridPath(x1, x2, y) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("class", "program-chart-grid-path");
    path.setAttribute("d", `M ${x1.toFixed(2)} ${y.toFixed(2)} L ${x2.toFixed(2)} ${y.toFixed(2)}`);
    return path;
  }

  function makeGridLabel(x, y, label) {
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("class", "program-chart-grid-label");
    text.setAttribute("x", x.toFixed(2));
    text.setAttribute("y", y.toFixed(2));
    text.textContent = label;
    return text;
  }

  function getGridLabel(metricKey, value) {
    const decimals = metricKey === "ppk" ? 2 : 0;
    return formatNumber(value, decimals);
  }

  function makeOutlinePath(d) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("class", "program-chart-outline-path");
    path.setAttribute("d", d);
    return path;
  }

  function makeOutlineDot(x, y) {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("class", "program-chart-outline-dot");
    circle.setAttribute("cx", x.toFixed(2));
    circle.setAttribute("cy", y.toFixed(2));
    circle.setAttribute("r", "2.35");
    return circle;
  }

  function ensureGuideSvg(plot) {
    let svg = plot.querySelector(":scope > .program-chart-guide-svg");
    if (svg) return svg;

    svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.classList.add("program-chart-guide-svg");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    plot.appendChild(svg);
    return svg;
  }

  function makeGuidePath(kind, x1, x2, y) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("class", `program-chart-guide-path program-chart-guide-path--${kind}`);
    path.setAttribute("d", `M ${x1.toFixed(2)} ${y.toFixed(2)} L ${x2.toFixed(2)} ${y.toFixed(2)}`);
    return path;
  }

  function makeGuideDot(kind, x, y) {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("class", `program-chart-guide-dot program-chart-guide-dot--${kind}`);
    circle.setAttribute("cx", x.toFixed(2));
    circle.setAttribute("cy", y.toFixed(2));
    circle.setAttribute("r", "3.75");
    return circle;
  }

  function getOutlineBars(plot) {
    return Array.from(plot.querySelectorAll(".program-chart-bar, .program-chart-stacked-bar"))
      .filter((bar) => {
        const rect = bar.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      });
  }

  function getChartSlots(plot) {
    return Array.from(plot.querySelectorAll(".program-chart-bar-slot"))
      .filter((slot) => {
        const rect = slot.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      });
  }

  function getDrawableBounds(plot, plotRect, height) {
    const slots = getChartSlots(plot);
    if (!slots.length) {
      return { top: 0, bottom: height };
    }

    const top = Math.min(...slots.map((slot) => slot.getBoundingClientRect().top - plotRect.top));
    const bottom = Math.max(...slots.map((slot) => slot.getBoundingClientRect().bottom - plotRect.top));
    return {
      top: Math.min(Math.max(top, 0), height),
      bottom: Math.min(Math.max(bottom, 0), height),
    };
  }

  function getChartLineBounds(plot, plotRect, width) {
    const slots = getChartSlots(plot);
    if (!slots.length) {
      return { x1: 0, x2: width };
    }

    const firstRect = slots[0].getBoundingClientRect();
    const lastRect = slots[slots.length - 1].getBoundingClientRect();
    return {
      x1: Math.min(Math.max(firstRect.left - plotRect.left, 0), width),
      x2: Math.min(Math.max(lastRect.right - plotRect.left, 0), width),
    };
  }

  function prepareSvg(svg, width, height) {
    svg.setAttribute("width", width.toFixed(2));
    svg.setAttribute("height", height.toFixed(2));
    svg.setAttribute("viewBox", `0 0 ${width.toFixed(2)} ${height.toFixed(2)}`);
    clearOutlineSvg(svg);
  }

  function renderPlotGrid(plot, plotRect, width, height) {
    const svg = ensureGridSvg(plot);
    prepareSvg(svg, width, height);

    const metricMax = toNumber(plot.dataset.metricMax);
    const ticks = (plot.dataset.gridTicks || "")
      .split(",")
      .map((value) => toNumber(value))
      .filter((value) => value > 0 && value <= metricMax);
    if (!ticks.length || metricMax <= 0) return;

    const drawableBounds = getDrawableBounds(plot, plotRect, height);
    const { x1, x2 } = getChartLineBounds(plot, plotRect, width);

    ticks.forEach((tick) => {
      const y = guideYFromValue(tick, metricMax, drawableBounds.top, drawableBounds.bottom);
      svg.appendChild(makeGridPath(x1, x2, y));
      svg.appendChild(makeGridLabel(x1 + 4, y + 4, getGridLabel(plot.dataset.metricKey, tick)));
    });
  }

  function renderPlotGuides(plot, plotRect, width, height, bars) {
    const svg = ensureGuideSvg(plot);
    prepareSvg(svg, width, height);

    // Alloc already represents a normalized 0-100% composition. The max/min
    // horizontal guides add noise in this view, so only draw guides for
    // absolute metrics such as kcal, grams and ppk.
    if (plot.classList.contains("program-chart-plot--alloc")) return;

    const metricMax = toNumber(plot.dataset.metricMax);
    if (!bars.length || metricMax <= 0) return;

    const { x1, x2 } = getChartLineBounds(plot, plotRect, width);
    const drawableBounds = getDrawableBounds(plot, plotRect, height);

    ["max", "min"].forEach((kind) => {
      const rawValue = toNumber(plot.dataset[`guide${kind.charAt(0).toUpperCase()}${kind.slice(1)}`]);
      const y = guideYFromValue(rawValue, metricMax, drawableBounds.top, drawableBounds.bottom);
      svg.appendChild(makeGuidePath(kind, x1, x2, y));
      svg.appendChild(makeGuideDot(kind, x1, y));
      svg.appendChild(makeGuideDot(kind, x2, y));
    });
  }


  function alignBarTooltips(plot) {
    plot.querySelectorAll(".program-chart-bar-slot").forEach((slot) => {
      const tooltip = slot.querySelector(".program-chart-bar-tooltip");
      const bar = slot.querySelector(".program-chart-bar, .program-chart-stacked-bar");
      if (!tooltip || !bar) return;

      const slotRect = slot.getBoundingClientRect();
      const barRect = bar.getBoundingClientRect();
      if (!slotRect.width || !barRect.width) return;

      const center = (barRect.left + (barRect.width / 2)) - slotRect.left;
      const centerPercent = Math.min(Math.max((center / slotRect.width) * 100, 0), 100);
      slot.style.setProperty("--program-chart-tooltip-x", `${centerPercent.toFixed(2)}%`);
    });
  }

  let activeFloatingTooltipSlot = null;

  function ensureFloatingTooltip() {
    let tooltip = document.querySelector(".js-program-chart-floating-tooltip");
    if (tooltip) return tooltip;

    tooltip = makeElement("span", "program-chart-floating-tooltip js-program-chart-floating-tooltip", {
      role: "tooltip",
      "aria-hidden": "true",
    });
    document.body.appendChild(tooltip);
    return tooltip;
  }

  function getTooltipSource(slot) {
    return slot ? slot.querySelector(".program-chart-bar-tooltip") : null;
  }

  function getTooltipAnchor(slot) {
    return slot ? slot.querySelector(".program-chart-bar, .program-chart-stacked-bar") : null;
  }

  function hideFloatingTooltip() {
    const tooltip = document.querySelector(".js-program-chart-floating-tooltip");
    activeFloatingTooltipSlot = null;
    if (!tooltip) return;
    tooltip.classList.remove("is-visible");
    tooltip.setAttribute("aria-hidden", "true");
  }

  function positionFloatingTooltip(slot) {
    const tooltip = ensureFloatingTooltip();
    const anchor = getTooltipAnchor(slot);
    if (!anchor) return;

    const anchorRect = anchor.getBoundingClientRect();
    const centerX = anchorRect.left + (anchorRect.width / 2);
    const anchorTop = anchorRect.top;
    const viewportPadding = 8;

    tooltip.style.left = `${centerX}px`;
    tooltip.style.top = `${anchorTop}px`;
    tooltip.style.setProperty("--program-chart-floating-tooltip-arrow-x", "50%");

    const tooltipRect = tooltip.getBoundingClientRect();
    const halfWidth = tooltipRect.width / 2;
    const minLeft = viewportPadding + halfWidth;
    const maxLeft = window.innerWidth - viewportPadding - halfWidth;
    const clampedLeft = Math.min(Math.max(centerX, minLeft), maxLeft);
    const arrowX = Math.min(
      Math.max(centerX - (clampedLeft - halfWidth), 12),
      Math.max(tooltipRect.width - 12, 12),
    );
    const minTop = viewportPadding + tooltipRect.height + 12;
    const clampedTop = Math.max(anchorTop, minTop);

    tooltip.style.left = `${clampedLeft}px`;
    tooltip.style.top = `${clampedTop}px`;
    tooltip.style.setProperty("--program-chart-floating-tooltip-arrow-x", `${arrowX.toFixed(2)}px`);
  }

  function showFloatingTooltip(slot) {
    const source = getTooltipSource(slot);
    const anchor = getTooltipAnchor(slot);
    if (!source || !anchor) return;

    const tooltip = ensureFloatingTooltip();
    const html = slot.dataset.floatingTooltipHtml || source.innerHTML;
    slot.dataset.floatingTooltipHtml = html;
    tooltip.innerHTML = html;
    tooltip.setAttribute("aria-hidden", "false");
    tooltip.classList.add("is-visible");
    activeFloatingTooltipSlot = slot;
    positionFloatingTooltip(slot);
  }

  function bindFloatingTooltip(slot) {
    const source = getTooltipSource(slot);
    if (!source || slot.dataset.floatingTooltipBound === "true") return;

    source.setAttribute("aria-hidden", "true");
    slot.dataset.floatingTooltipBound = "true";
    slot.addEventListener("pointerenter", () => showFloatingTooltip(slot));
    slot.addEventListener("pointermove", () => {
      if (activeFloatingTooltipSlot === slot) positionFloatingTooltip(slot);
    });
    slot.addEventListener("pointerleave", hideFloatingTooltip);
    slot.addEventListener("focusin", () => showFloatingTooltip(slot));
    slot.addEventListener("focusout", hideFloatingTooltip);
  }

  window.addEventListener("scroll", hideFloatingTooltip, true);
  window.addEventListener("resize", hideFloatingTooltip);


  function renderPlotOutline(plot) {
    const svg = ensureOutlineSvg(plot);
    const plotRect = plot.getBoundingClientRect();
    const width = Math.max(plot.offsetWidth, plot.clientWidth, plotRect.width, 1);
    const height = Math.max(plot.offsetHeight, plot.clientHeight, plotRect.height, 1);
    const bars = getOutlineBars(plot);

    // Keep the SVG coordinate system locked to the plot border-box. On mobile,
    // fractional layout, horizontal overflow and late font/layout adjustments can
    // make a CSS-sized SVG drift slightly from the DOMRect-based bar positions.
    // Explicit width/height attributes plus the same viewBox keep the silhouette
    // and the bars in the same coordinate space.
    svg.setAttribute("width", width.toFixed(2));
    svg.setAttribute("height", height.toFixed(2));
    svg.setAttribute("viewBox", `0 0 ${width.toFixed(2)} ${height.toFixed(2)}`);
    clearOutlineSvg(svg);
    alignBarTooltips(plot);
    renderPlotGrid(plot, plotRect, width, height);
    renderPlotGuides(plot, plotRect, width, height, bars);

    if (!bars.length) return;

    const points = bars.map((bar) => {
      const rect = bar.getBoundingClientRect();
      const x1 = Math.min(Math.max(rect.left - plotRect.left, 0), width);
      const x2 = Math.min(Math.max(rect.right - plotRect.left, 0), width);
      const xCenter = Math.min(Math.max(x1 + ((x2 - x1) / 2), 0), width);
      const yTop = Math.min(Math.max(rect.top - plotRect.top, 0), height);
      return { xCenter, yTop };
    });

    const lineCommands = points.map((point, index) => (
      `${index === 0 ? "M" : "L"} ${point.xCenter.toFixed(2)} ${point.yTop.toFixed(2)}`
    ));
    svg.appendChild(makeOutlinePath(lineCommands.join(" ")));

    points.forEach((point, index) => {
      if (index === 0) return;
      svg.appendChild(makeOutlineDot(point.xCenter, point.yTop));
    });
  }

  function renderVisibleOutlines(root) {
    const scope = root || document;
    scope.querySelectorAll(".program-chart-plot").forEach((plot) => {
      if (!plot.offsetParent) return;
      renderPlotOutline(plot);
    });
  }

  function scheduleVisibleOutlines(root) {
    window.requestAnimationFrame(() => {
      renderVisibleOutlines(root);
      window.requestAnimationFrame(() => renderVisibleOutlines(root));
    });
  }


  function getBarHeightPercent(metric, bar, metricMax) {
    if (metric.kind === "stacked") {
      const stackTotal = metric.key === "alloc" ? 100 : toNumber(bar.stackTotal || bar.value);
      return metric.key === "alloc" ? (stackTotal ? 100 : 0) : heightPercent(bar.value, metricMax);
    }
    return heightPercent(bar.value, metricMax);
  }

  function getSilhouetteSideHeight(currentHeight, neighborHeight) {
    const current = Math.max(toNumber(currentHeight), 0);
    if (!current) return 0;
    const neighbor = Math.max(toNumber(neighborHeight), 0);
    if (neighbor >= current) return 0;
    return Math.min(((current - neighbor) / current) * 100, 100);
  }

  function getSilhouetteStyle(currentHeight, leftHeight = 0, rightHeight = 0) {
    const left = getSilhouetteSideHeight(currentHeight, leftHeight);
    const right = getSilhouetteSideHeight(currentHeight, rightHeight);
    return `--program-chart-outline-left-height: ${left.toFixed(2)}%; --program-chart-outline-right-height: ${right.toFixed(2)}%;`;
  }

  function renderBarTooltip(metric, bar) {
    if (bar.isEmpty) return null;

    const tooltip = makeElement("span", "program-chart-bar-tooltip", {
      role: "tooltip",
    });
    const iconRow = makeElement("span", "program-chart-bar-tooltip__icon-row");
    const iconShell = makeElement("span", "program-chart-bar-tooltip__icon-shell");
    iconShell.appendChild(makeElement("i", "program-chart-bar-tooltip__icon", {
      "data-lucide": "clipboard-list",
      "aria-hidden": "true",
    }));
    iconRow.appendChild(iconShell);

    const name = makeElement("span", "program-chart-bar-tooltip__name", {
      text: bar.dailyplanName || "Plan diario",
    });
    const value = makeElement("span", "program-chart-bar-tooltip__value", {
      text: bar.titleValue || `${formatNumber(bar.value, metric.decimals || 0)} ${metric.unit || ""}`.trim(),
    });

    tooltip.appendChild(iconRow);
    tooltip.appendChild(name);
    tooltip.appendChild(value);
    return tooltip;
  }

  function renderSegment(segment, stackTotal, barIsEmpty, showSegmentValues, extraClasses = []) {
    const percent = segmentPercent(segment.value, stackTotal);
    const segmentClasses = [
      "program-chart-stacked-bar__segment",
      `program-chart-stacked-bar__segment--${segment.key}`,
      ...extraClasses,
    ].filter(Boolean);
    const element = makeElement("span", segmentClasses.join(" "), {
      style: `height: ${percent.toFixed(2)}%;`,
      "aria-label": `${segment.label || ""} ${segment.valueLabel || ""}`.trim(),
    });

    if (showSegmentValues && !barIsEmpty && toNumber(segment.value) > 0) {
      const value = makeElement("span", "program-chart-segment-value", {
        text: formatNumber(segment.value),
      });
      element.appendChild(value);
    }

    return element;
  }

  function renderBar(metric, bar, metricMax, showBarValues, silhouette = {}, scope = "program") {
    const slotClasses = ["program-chart-bar-slot"];
    if (bar.isWeekStart) slotClasses.push("is-week-start");
    if (bar.isEmpty) slotClasses.push("is-empty");

    const slot = makeElement("div", slotClasses.join(" "), {
      "aria-label": bar.title,
    });

    if (metric.kind === "stacked") {
      const stackTotal = metric.key === "alloc" ? 100 : toNumber(bar.stackTotal || bar.value);
      const outerHeight = getBarHeightPercent(metric, bar, metricMax);
      const stacked = makeElement("div", "program-chart-stacked-bar", {
        style: `height: ${outerHeight.toFixed(2)}%; ${getSilhouetteStyle(outerHeight, silhouette.leftHeight, silhouette.rightHeight)}`,
      });

      const segments = Array.isArray(bar.segments) ? bar.segments : [];
      const topSegmentIndex = segments.reduce((lastIndex, segment, index) => (
        toNumber(segment.value) > 0 ? index : lastIndex
      ), -1);

      segments.forEach((segment, index) => {
        stacked.appendChild(renderSegment(
          segment,
          stackTotal,
          bar.isEmpty,
          showBarValues,
          index === topSegmentIndex ? ["is-stack-top"] : [],
        ));
      });

      slot.appendChild(stacked);
      const tooltip = renderBarTooltip(metric, bar);
      if (tooltip) {
        slot.appendChild(tooltip);
        bindFloatingTooltip(slot);
      }
      return slot;
    }

    const outerHeight = getBarHeightPercent(metric, bar, metricMax);
    const singleBar = makeElement("div", "program-chart-bar", {
      style: `height: ${outerHeight.toFixed(2)}%; ${getSilhouetteStyle(outerHeight, silhouette.leftHeight, silhouette.rightHeight)}`,
    });
    if (showBarValues && !bar.isEmpty) {
      const valueLabel = makeElement("span", "program-chart-bar-value");
      valueLabel.appendChild(makeElement("span", "program-chart-bar-value__number", {
        text: formatNumber(bar.value, metric.decimals || 0),
      }));
      if (scope === "week" && metric.unit) {
        valueLabel.appendChild(makeElement("span", "program-chart-bar-value__unit", {
          text: metric.unit,
        }));
      }
      singleBar.appendChild(valueLabel);
    }
    slot.appendChild(singleBar);
    const tooltip = renderBarTooltip(metric, bar);
    if (tooltip) {
      slot.appendChild(tooltip);
      bindFloatingTooltip(slot);
    }
    return slot;
  }

  function renderLegend(metric) {
    if (metric.kind !== "stacked") return null;

    const legend = makeElement("div", "program-chart-legend", {
      "aria-label": metric.legendLabel || "Leyenda",
    });

    const items = metric.legendItems && metric.legendItems.length
      ? metric.legendItems
      : [
          { key: "protein", label: "P%" },
          { key: "carbs", label: "C%" },
          { key: "fat", label: "F%" },
        ];

    items.forEach((item) => {
      const label = makeElement("span");
      label.appendChild(makeElement("i", `program-chart-legend__swatch program-chart-legend__swatch--${item.key}`));
      label.appendChild(document.createTextNode(item.label));
      legend.appendChild(label);
    });

    return legend;
  }

  function renderPane(data, metric, showBarValues, options = {}) {
    const pane = makeElement("div", "program-chart-pane js-program-chart-pane", {
      "data-metric": metric.key,
    });

    const scope = data.scope || "program";
    const weeksCount = Math.max(toNumber(data.weeksCount || 1), 1);
    const layout = makeElement("div", "program-chart-layout");
    const axis = makeElement("div", `program-chart-main-axis program-chart-main-axis--${scope}`, {
      style: `--program-chart-days: ${data.daysCount || 1}; --program-chart-weeks: ${weeksCount}; --program-chart-min-width: ${getChartMinWidth(data)};`,
      "data-weeks-count": Math.min(weeksCount, 12),
    });
    if (options.syncScroll) {
      axis.classList.add("js-program-chart-scroll-sync");
    }
    const rawMetricMax = getRawMetricMax(metric);
    const metricMax = getMetricMax(metric);
    const guideValues = getGuideValues(metric, rawMetricMax);
    const gridTicks = getMetricTicks(metric, metricMax);
    const plot = makeElement("div", `program-chart-plot program-chart-plot--${scope} program-chart-plot--${metric.kind} program-chart-plot--${metric.key}`, {
      style: `--program-chart-days: ${data.daysCount || 1}; --program-chart-weeks: ${weeksCount};`,
      "aria-label": `Gráfico de ${metric.label}`,
      "data-metric-max": metricMax,
      "data-metric-key": metric.key,
      "data-grid-ticks": gridTicks.join(","),
      "data-guide-max": guideValues.max,
      "data-guide-min": guideValues.min,
    });

    const bars = Array.isArray(metric.bars) ? metric.bars : [];
    const barHeights = bars.map((bar) => getBarHeightPercent(metric, bar, metricMax));

    if (scope === "program") {
      let barIndex = 0;
      groupBarsByWeek(bars, weeksCount).forEach((week) => {
        const weekColumn = makeElement("div", "program-chart-week-column", {
          "data-week-number": week.weekNumber,
          "aria-label": `Semana ${week.weekNumber}`,
        });
        week.bars.forEach((bar) => {
          const silhouette = {
            leftHeight: barHeights[barIndex - 1] || 0,
            rightHeight: barHeights[barIndex + 1] || 0,
          };
          weekColumn.appendChild(renderBar(metric, bar, metricMax, showBarValues, silhouette, scope));
          barIndex += 1;
        });
        plot.appendChild(weekColumn);
      });
    } else {
      bars.forEach((bar, index) => {
        const silhouette = {
          leftHeight: barHeights[index - 1] || 0,
          rightHeight: barHeights[index + 1] || 0,
        };
        plot.appendChild(renderBar(metric, bar, metricMax, showBarValues, silhouette, scope));
      });
    }

    if (options.externalHeader) {
      pane.appendChild(renderAxisHeader(metric, { hideUnit: true }));
    } else {
      axis.appendChild(renderAxisHeader(metric));
    }
    axis.appendChild(plot);
    if (!options.externalAxis) {
      axis.appendChild(renderAxis(data));
    }
    layout.appendChild(axis);
    pane.appendChild(layout);

    const legend = options.externalHeader ? null : renderLegend(metric);
    if (legend) pane.appendChild(legend);

    return pane;
  }

  function bindSynchronizedScroll(body) {
    const scrollContainers = Array.from(body.querySelectorAll(".js-program-chart-scroll-sync"));
    let isSyncing = false;

    scrollContainers.forEach((container) => {
      container.addEventListener("scroll", () => {
        if (isSyncing) return;
        isSyncing = true;
        const left = container.scrollLeft;
        scrollContainers.forEach((target) => {
          if (target !== container) target.scrollLeft = left;
        });
        window.requestAnimationFrame(() => {
          isSyncing = false;
          scheduleVisibleOutlines(body);
        });
      }, { passive: true });
    });
  }

  function renderChart(chart) {
    const data = readChartData(chart);
    if (!data || !Array.isArray(data.metrics) || !data.metrics.length) return;

    const isProgramScope = (data.scope || "program") === "program";
    const isWeekScope = (data.scope || "") === "week" || chart.classList.contains("program-chart-panel--week");
    const isProgramPreview = (
      (isProgramScope && (
        chart.classList.contains("program-chart-panel--card")
        || chart.classList.contains("program-chart-panel--detail")
      ))
      || isWeekScope
      || chart.classList.contains("program-chart-panel--week-card-kpi-preview")
    );
    const showBarValues = isProgramPreview ? false : chart.dataset.showBarValues === "true";
    const body = chart.querySelector(".js-program-chart-body");
    if (!body) return;

    const activeMetric = data.metrics.find((metric) => metric.isActive) || data.metrics[0];
    const tabs = isProgramPreview ? [] : renderTabs(chart, data, activeMetric.key);
    chart.classList.toggle("program-chart-panel--stacked-preview", isProgramPreview);
    body.classList.toggle("program-chart-panel__body--stacked-preview", isProgramPreview);
    body.innerHTML = "";

    if (isProgramPreview) {
      const previewHeader = makeElement("div", "program-chart-preview-axis-header js-program-chart-scroll-sync", {
        style: `--program-chart-min-width: ${getChartMinWidth(data)};`,
      });
      previewHeader.appendChild(renderAxis(data, { uppercase: true }));
      body.appendChild(previewHeader);
    }

    data.metrics.forEach((metric) => {
      const pane = renderPane(data, metric, showBarValues, {
        externalHeader: isProgramPreview,
        externalAxis: isProgramPreview,
        syncScroll: isProgramPreview,
      });
      pane.hidden = !isProgramPreview && metric.key !== activeMetric.key;
      body.appendChild(pane);
    });

    scheduleVisibleOutlines(body);
    if (isProgramPreview) bindSynchronizedScroll(body);
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }

    if (isProgramPreview) return;

    function activate(metricKey) {
      tabs.forEach((tab) => {
        const isActive = tab.dataset.metric === metricKey;
        tab.classList.toggle("is-active", isActive);
        tab.setAttribute("aria-selected", isActive ? "true" : "false");
      });

      body.querySelectorAll(".js-program-chart-pane").forEach((pane) => {
        pane.hidden = pane.dataset.metric !== metricKey;
      });
      scheduleVisibleOutlines(body);
    }

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => activate(tab.dataset.metric));
    });
  }

  document.querySelectorAll(".js-program-chart").forEach(renderChart);

  if ("ResizeObserver" in window) {
    const outlineResizeObserver = new ResizeObserver((entries) => {
      const roots = new Set();
      entries.forEach((entry) => {
        const plot = entry.target.closest(".program-chart-plot");
        if (plot) roots.add(plot);
      });
      roots.forEach((plot) => scheduleVisibleOutlines(plot.parentElement || plot));
    });

    document.querySelectorAll(".program-chart-plot").forEach((plot) => {
      outlineResizeObserver.observe(plot);
    });
  }

  let resizeFrame = null;
  window.addEventListener("resize", () => {
    if (resizeFrame) window.cancelAnimationFrame(resizeFrame);
    resizeFrame = window.requestAnimationFrame(() => {
      resizeFrame = null;
      renderVisibleOutlines(document);
    });
  });
});
