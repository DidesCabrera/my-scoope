document.addEventListener("DOMContentLoaded", function () {
  const calendar = document.querySelector("[data-home-calendar]");

  if (!calendar) {
    return;
  }

  const dayButtons = Array.from(calendar.querySelectorAll("[data-home-calendar-day]"));
  const panels = Array.from(calendar.querySelectorAll('[role="tabpanel"]'));
  const planCards = Array.from(calendar.querySelectorAll("[data-home-calendar-plan-card]"));

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

  function setPlanCardExpanded(card, isExpanded) {
    const preview = card.querySelector("[data-home-calendar-plan-preview]");

    if (!preview) {
      return;
    }

    card.classList.toggle("is-expanded", isExpanded);
    card.setAttribute("aria-expanded", isExpanded ? "true" : "false");
    preview.hidden = !isExpanded;
  }

  function togglePlanCard(card) {
    setPlanCardExpanded(card, !card.classList.contains("is-expanded"));
  }

  dayButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      selectDay(button);
    });
  });

  planCards.forEach(function (card) {
    card.addEventListener("click", function (event) {
      if (event.target.closest("a, button, input, textarea, select")) {
        return;
      }

      togglePlanCard(card);
    });

    card.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }

      event.preventDefault();
      togglePlanCard(card);
    });
  });
});
