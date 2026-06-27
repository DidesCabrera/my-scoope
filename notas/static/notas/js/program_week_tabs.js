document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".js-program-week-tabs").forEach((tablist) => {
    const shell = tablist.closest(".program-board-shell");
    const tabs = Array.from(tablist.querySelectorAll(".js-program-week-tab"));
    const panels = Array.from(shell?.querySelectorAll(".js-program-week-panel") || []);

    if (!tabs.length || !panels.length) return;

    function activateTab(tab, options = {}) {
      const targetId = tab.dataset.target;
      if (!targetId) return;

      tabs.forEach((item) => {
        const isActive = item === tab;
        item.classList.toggle("is-active", isActive);
        item.setAttribute("aria-selected", isActive ? "true" : "false");
        item.setAttribute("tabindex", isActive ? "0" : "-1");
      });

      panels.forEach((panel) => {
        const isActive = panel.id === targetId;
        panel.classList.toggle("is-active", isActive);
        panel.hidden = !isActive;
      });

      document.dispatchEvent(new CustomEvent("program-week-tab:changed", {
        detail: { targetId },
      }));

      if (options.focus) tab.focus();
    }

    tablist.addEventListener("click", (event) => {
      const tab = event.target.closest(".js-program-week-tab");
      if (!tab || !tablist.contains(tab)) return;
      activateTab(tab);
    });

    tablist.addEventListener("keydown", (event) => {
      const currentIndex = tabs.indexOf(document.activeElement);
      if (currentIndex === -1) return;

      let nextIndex = currentIndex;
      if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % tabs.length;
      if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = tabs.length - 1;
      if (nextIndex === currentIndex && event.key !== "Home" && event.key !== "End") return;

      event.preventDefault();
      activateTab(tabs[nextIndex], { focus: true });
    });

    const selectedTab = tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0];
    activateTab(selectedTab);
  });
});
