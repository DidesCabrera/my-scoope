document.addEventListener("DOMContentLoaded", function () {
  const calendar = document.querySelector("[data-home-calendar]");

  if (!calendar) {
    return;
  }

  const dayButtons = Array.from(calendar.querySelectorAll("[data-home-calendar-day]"));
  const panels = Array.from(calendar.querySelectorAll('[role="tabpanel"]'));

  function selectDay(selectedButton) {
    dayButtons.forEach(function (button) {
      const isSelected = button === selectedButton;
      button.classList.toggle("is-selected", isSelected);
      button.setAttribute("aria-selected", isSelected ? "true" : "false");
    });

    panels.forEach(function (panel) {
      panel.hidden = panel.id !== selectedButton.getAttribute("aria-controls");
    });
  }

  dayButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      selectDay(button);
    });
  });
});
