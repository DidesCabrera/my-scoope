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

  function getMetricMax(metric) {
    const bars = Array.isArray(metric.bars) ? metric.bars : [];
    if (metric.kind === "stacked") {
      return Math.max(...bars.map((bar) => toNumber(bar.value)), 1);
    }
    return Math.max(...bars.map((bar) => toNumber(bar.value)), 1);
  }

  function renderTabs(chart, data, activeKey) {
    const tabsContainer = chart.querySelector(".js-program-chart-tabs");
    if (!tabsContainer) return [];
    tabsContainer.innerHTML = "";

    return (data.metrics || []).map((metric) => {
      const tab = makeElement("button", "program-chart-tab js-program-chart-tab", {
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

  function renderAxis(data) {
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
        text: scope === "week" ? mobileLabel : label.label,
      }));
    });

    return axis;
  }


  function renderAxisHeader(metric) {
    const header = makeElement("div", "program-chart-axis-header");
    const title = makeElement("h3", "program-chart-axis-header__title", {
      text: metric.label || "Gráfico",
    });
    const range = makeElement("span", "program-chart-axis-header__range", {
      text: metric.rangeLabel || "",
    });

    header.appendChild(title);
    if (metric.rangeLabel) header.appendChild(range);
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
    circle.setAttribute("r", "3.5");
    return circle;
  }

  function getOutlineBars(plot) {
    return Array.from(plot.querySelectorAll(".program-chart-bar, .program-chart-stacked-bar"))
      .filter((bar) => {
        const rect = bar.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      });
  }

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

    if (!bars.length) return;

    const points = bars.map((bar) => {
      const rect = bar.getBoundingClientRect();
      const x1 = Math.min(Math.max(rect.left - plotRect.left, 0), width);
      const x2 = Math.min(Math.max(rect.right - plotRect.left, 0), width);
      const yTop = Math.min(Math.max(rect.top - plotRect.top, 0), height);
      const yBottom = Math.min(Math.max(rect.bottom - plotRect.top, 0), height);
      return { x1, x2, yTop, yBottom };
    });

    points.forEach((point, index) => {
      const previous = points[index - 1];
      const next = points[index + 1];
      const isFirst = index === 0;
      const isLast = index === points.length - 1;
      const leftStop = previous ? Math.min(previous.yTop, point.yBottom) : point.yTop;
      const rightStop = next ? Math.min(next.yTop, point.yBottom) : point.yTop;
      const commands = [];

      if (!isFirst && leftStop > point.yTop) {
        commands.push(`M ${point.x1.toFixed(2)} ${leftStop.toFixed(2)}`);
        commands.push(`L ${point.x1.toFixed(2)} ${point.yTop.toFixed(2)}`);
      }

      commands.push(`M ${point.x1.toFixed(2)} ${point.yTop.toFixed(2)}`);
      commands.push(`L ${point.x2.toFixed(2)} ${point.yTop.toFixed(2)}`);

      if (!isLast && rightStop > point.yTop) {
        commands.push(`L ${point.x2.toFixed(2)} ${rightStop.toFixed(2)}`);
      }

      svg.appendChild(makeOutlinePath(commands.join(" ")));
      svg.appendChild(makeOutlineDot(point.x1, point.yTop));
      svg.appendChild(makeOutlineDot(point.x2, point.yTop));
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

  function renderBar(metric, bar, metricMax, showBarValues, silhouette = {}) {
    const slotClasses = ["program-chart-bar-slot"];
    if (bar.isWeekStart) slotClasses.push("is-week-start");
    if (bar.isEmpty) slotClasses.push("is-empty");

    const slot = makeElement("div", slotClasses.join(" "), {
      title: bar.title,
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
      return slot;
    }

    const outerHeight = getBarHeightPercent(metric, bar, metricMax);
    const singleBar = makeElement("div", "program-chart-bar", {
      style: `height: ${outerHeight.toFixed(2)}%; ${getSilhouetteStyle(outerHeight, silhouette.leftHeight, silhouette.rightHeight)}`,
    });
    if (showBarValues && !bar.isEmpty) {
      singleBar.appendChild(makeElement("span", "program-chart-bar-value", {
        text: formatNumber(bar.value, metric.decimals || 0),
      }));
    }
    slot.appendChild(singleBar);
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

  function renderPane(data, metric, showBarValues) {
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
    const plot = makeElement("div", `program-chart-plot program-chart-plot--${scope} program-chart-plot--${metric.kind} program-chart-plot--${metric.key}`, {
      style: `--program-chart-days: ${data.daysCount || 1}; --program-chart-weeks: ${weeksCount};`,
      "aria-label": `Gráfico de ${metric.label}`,
    });

    plot.appendChild(makeElement("span", "program-chart-guide program-chart-guide--max", { "aria-hidden": "true" }));
    plot.appendChild(makeElement("span", "program-chart-guide program-chart-guide--min", { "aria-hidden": "true" }));

    const metricMax = getMetricMax(metric);
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
          weekColumn.appendChild(renderBar(metric, bar, metricMax, showBarValues, silhouette));
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
        plot.appendChild(renderBar(metric, bar, metricMax, showBarValues, silhouette));
      });
    }

    axis.appendChild(renderAxisHeader(metric));
    axis.appendChild(plot);
    axis.appendChild(renderAxis(data));
    layout.appendChild(axis);
    pane.appendChild(layout);

    const legend = renderLegend(metric);
    if (legend) pane.appendChild(legend);

    return pane;
  }

  function renderChart(chart) {
    const data = readChartData(chart);
    if (!data || !Array.isArray(data.metrics) || !data.metrics.length) return;

    const showBarValues = chart.dataset.showBarValues === "true";
    const body = chart.querySelector(".js-program-chart-body");
    if (!body) return;

    const activeMetric = data.metrics.find((metric) => metric.isActive) || data.metrics[0];
    const tabs = renderTabs(chart, data, activeMetric.key);
    body.innerHTML = "";

    data.metrics.forEach((metric) => {
      const pane = renderPane(data, metric, showBarValues);
      pane.hidden = metric.key !== activeMetric.key;
      body.appendChild(pane);
    });

    scheduleVisibleOutlines(body);

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
