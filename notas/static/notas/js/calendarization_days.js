document.addEventListener("DOMContentLoaded", function () {
  const calendar = document.querySelector("[data-calendarization-controller]");
  if (!calendar) return;

  const dayButtons = Array.from(
    calendar.querySelectorAll("[data-calendarization-day]"),
  );
  const panels = Array.from(calendar.querySelectorAll('[role="tabpanel"]'));

  dayButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      dayButtons.forEach(function (candidate) {
        const isSelected = candidate === button;
        candidate.classList.toggle("is-selected", isSelected);
        candidate.setAttribute("aria-selected", isSelected ? "true" : "false");
      });

      const selectedPanelId = button.getAttribute("aria-controls");
      panels.forEach(function (panel) {
        panel.hidden = panel.id !== selectedPanelId;
      });
    });
  });
});
