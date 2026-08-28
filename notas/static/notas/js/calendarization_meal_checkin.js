(function () {
  function bootMealCheckIn() {
    document.querySelectorAll("[data-meal-checkin-status]").forEach((form) => {
      const checkbox = form.querySelector("[data-meal-checkin-checkbox]");
      const action = form.querySelector("[data-meal-checkin-action]");
      if (!checkbox || !action) return;

      checkbox.addEventListener("change", () => {
        action.value = checkbox.checked ? "completed" : "skipped";
        checkbox.disabled = true;
        form.requestSubmit();
      });
    });

    document.querySelectorAll("[data-meal-note]").forEach((section) => {
      const editButton = section.querySelector("[data-meal-note-edit]");
      const display = section.querySelector("[data-meal-note-display]");
      const form = section.querySelector("[data-meal-note-form]");
      const input = section.querySelector("[data-meal-note-input]");
      const count = section.querySelector("[data-meal-note-count]");

      editButton?.addEventListener("click", () => {
        display?.setAttribute("hidden", "");
        editButton.setAttribute("hidden", "");
        form?.removeAttribute("hidden");
        input?.focus();
      });

      input?.addEventListener("input", () => {
        if (count) count.textContent = `${input.value.length}/500`;
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootMealCheckIn);
  } else {
    bootMealCheckIn();
  }
})();
