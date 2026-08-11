(() => {
  const tabs = Array.from(document.querySelectorAll("[data-msos-tab]"));
  const panels = Array.from(document.querySelectorAll("[data-msos-panel]"));
  if (!tabs.length || !panels.length) return;

  const activate = (id, { focus = false, updateHash = true } = {}) => {
    const nextTab = tabs.find((tab) => tab.dataset.msosTab === id);
    const nextPanel = panels.find((panel) => panel.dataset.msosPanel === id);
    if (!nextTab || !nextPanel) return;

    tabs.forEach((tab) => {
      const active = tab === nextTab;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    panels.forEach((panel) => { panel.hidden = panel !== nextPanel; });
    if (focus) nextTab.focus();
    if (updateHash) history.replaceState(null, "", `#${id}`);
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activate(tab.dataset.msosTab));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      let target = index;
      if (event.key === "ArrowLeft") target = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "ArrowRight") target = (index + 1) % tabs.length;
      if (event.key === "Home") target = 0;
      if (event.key === "End") target = tabs.length - 1;
      activate(tabs[target].dataset.msosTab, { focus: true });
    });
  });

  const initialId = window.location.hash.slice(1);
  if (initialId) activate(initialId, { updateHash: false });
})();
