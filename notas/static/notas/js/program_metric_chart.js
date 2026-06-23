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
    const axisCount = data.axisCount || data.weeksCount || 1;
    const axis = makeElement("div", `program-chart-week-axis program-chart-week-axis--${data.scope || "program"}`, {
      style: `--program-chart-axis-count: ${axisCount}; --program-chart-weeks: ${data.weeksCount || 1};`,
      "aria-label": "Etiquetas del gráfico",
    });

    (data.axisLabels || []).forEach((label) => {
      axis.appendChild(makeElement("span", "", {
        "data-mobile-label": label.mobileLabel || label.label,
        text: label.label,
      }));
    });

    return axis;
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

  function renderSegment(segment, stackTotal, barIsEmpty, showSegmentValues) {
    const percent = segmentPercent(segment.value, stackTotal);
    const element = makeElement("span", `program-chart-stacked-bar__segment program-chart-stacked-bar__segment--${segment.key}`, {
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

  function renderBar(metric, bar, metricMax, showBarValues) {
    const slotClasses = ["program-chart-bar-slot"];
    if (bar.isWeekStart) slotClasses.push("is-week-start");
    if (bar.isEmpty) slotClasses.push("is-empty");

    const slot = makeElement("div", slotClasses.join(" "), {
      title: bar.title,
      "aria-label": bar.title,
    });

    if (metric.kind === "stacked") {
      const stackTotal = metric.key === "alloc" ? 100 : toNumber(bar.stackTotal || bar.value);
      const outerHeight = metric.key === "alloc" ? (stackTotal ? 100 : 0) : heightPercent(bar.value, metricMax);
      const stacked = makeElement("div", "program-chart-stacked-bar", {
        style: `height: ${outerHeight.toFixed(2)}%;`,
      });

      (bar.segments || []).forEach((segment) => {
        stacked.appendChild(renderSegment(segment, stackTotal, bar.isEmpty, showBarValues));
      });

      slot.appendChild(stacked);
      return slot;
    }

    const singleBar = makeElement("div", "program-chart-bar", {
      style: `height: ${heightPercent(bar.value, metricMax).toFixed(2)}%;`,
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
    if (scope === "program") {
      groupBarsByWeek(metric.bars || [], weeksCount).forEach((week) => {
        const weekColumn = makeElement("div", "program-chart-week-column", {
          "data-week-number": week.weekNumber,
          "aria-label": `Semana ${week.weekNumber}`,
        });
        week.bars.forEach((bar) => {
          weekColumn.appendChild(renderBar(metric, bar, metricMax, showBarValues));
        });
        plot.appendChild(weekColumn);
      });
    } else {
      (metric.bars || []).forEach((bar) => {
        plot.appendChild(renderBar(metric, bar, metricMax, showBarValues));
      });
    }

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

    function activate(metricKey) {
      tabs.forEach((tab) => {
        const isActive = tab.dataset.metric === metricKey;
        tab.classList.toggle("is-active", isActive);
        tab.setAttribute("aria-selected", isActive ? "true" : "false");
      });

      body.querySelectorAll(".js-program-chart-pane").forEach((pane) => {
        pane.hidden = pane.dataset.metric !== metricKey;
      });
    }

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => activate(tab.dataset.metric));
    });
  }

  document.querySelectorAll(".js-program-chart").forEach(renderChart);
});
