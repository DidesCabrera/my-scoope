(function () {
  const tabList = document.querySelector("[data-food-detail-tabs]");
  if (!tabList) return;

  const tabs = Array.from(tabList.querySelectorAll("[data-detail-tab]"));
  const panels = Array.from(document.querySelectorAll("[data-detail-panel]"));
  const validKeys = new Set(tabs.map((tab) => tab.dataset.detailTab));

  function activateTab(key, options = {}) {
    if (!validKeys.has(key)) return;

    tabs.forEach((tab) => {
      const isActive = tab.dataset.detailTab === key;
      tab.setAttribute("aria-selected", String(isActive));
      tab.tabIndex = isActive ? 0 : -1;
      if (isActive && options.focus) tab.focus();
    });

    panels.forEach((panel) => {
      panel.hidden = panel.dataset.detailPanel !== key;
    });

    if (options.updateHash && window.history?.replaceState) {
      window.history.replaceState(null, "", `#${key}`);
    }
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => {
      activateTab(tab.dataset.detailTab, { updateHash: true });
    });

    tab.addEventListener("keydown", (event) => {
      let nextIndex = null;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = tabs.length - 1;
      if (nextIndex === null) return;

      event.preventDefault();
      activateTab(tabs[nextIndex].dataset.detailTab, { focus: true, updateHash: true });
    });
  });

  const initialKey = window.location.hash.slice(1);
  activateTab(validKeys.has(initialKey) ? initialKey : "identidad");
})();
