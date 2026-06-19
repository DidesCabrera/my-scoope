document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".js-program-chart").forEach((chart) => {
    const tabs = Array.from(chart.querySelectorAll(".js-program-chart-tab"));
    const panes = Array.from(chart.querySelectorAll(".js-program-chart-pane"));

    function activate(metricKey) {
      tabs.forEach((tab) => {
        const isActive = tab.dataset.metric === metricKey;
        tab.classList.toggle("is-active", isActive);
        tab.setAttribute("aria-selected", isActive ? "true" : "false");
      });

      panes.forEach((pane) => {
        pane.hidden = pane.dataset.metric !== metricKey;
      });
    }

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => activate(tab.dataset.metric));
    });
  });
});
