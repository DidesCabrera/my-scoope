(function () {
  const scrollStorageKey = "myscoope.mealCheckIn.scrollPosition";

  function storeScrollPosition() {
    try {
      if ("scrollRestoration" in history) history.scrollRestoration = "manual";
      sessionStorage.setItem(
        scrollStorageKey,
        JSON.stringify({
          path: `${window.location.pathname}${window.location.search}`,
          y: window.scrollY,
        }),
      );
    } catch (_error) {
      // The form still works when browser storage is unavailable.
    }
  }

  function restoreScrollPosition() {
    let stored;
    try {
      stored = JSON.parse(sessionStorage.getItem(scrollStorageKey) || "null");
      sessionStorage.removeItem(scrollStorageKey);
    } catch (_error) {
      return;
    }

    const currentPath = `${window.location.pathname}${window.location.search}`;
    if (!stored || stored.path !== currentPath || !Number.isFinite(stored.y)) return;

    const restore = () => window.scrollTo({ top: stored.y, behavior: "auto" });
    requestAnimationFrame(() => requestAnimationFrame(restore));
    window.addEventListener("load", restore, { once: true });
    window.setTimeout(restore, 150);
  }

  function bootMealCheckIn() {
    restoreScrollPosition();

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

    document.querySelectorAll("[data-meal-checkin-status], [data-meal-note-form]").forEach((form) => {
      form.addEventListener("submit", storeScrollPosition);
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
