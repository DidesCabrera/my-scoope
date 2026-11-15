document.querySelectorAll("[data-preparation-nutrition]").forEach((section) => {
  const tabs = Array.from(section.querySelectorAll("[data-nutrition-tab]"));
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((candidate) => {
        const selected = candidate === tab;
        candidate.setAttribute("aria-selected", String(selected));
        section.querySelector("#" + candidate.getAttribute("aria-controls")).hidden = !selected;
      });
    });
  });
});
