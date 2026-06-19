document.addEventListener("DOMContentLoaded", () => {
  const pickers = Array.from(document.querySelectorAll(".js-program-slot-picker"));

  function closeAllExcept(currentPicker) {
    pickers.forEach((picker) => {
      if (picker !== currentPicker) {
        picker.hidden = true;
        picker.closest(".program-day-cell")?.classList.remove("is-picking");
      }
    });
  }

  function closeSlotCards(scope, exceptId = null) {
    const container = scope || document;

    container.querySelectorAll(".js-program-slot-card").forEach((card) => {
      if (card.id !== exceptId) {
        card.hidden = true;
      }
    });

    container.querySelectorAll(".program-day-cell.has-plan").forEach((cell) => {
      if (cell.dataset.slotCardTarget !== exceptId) {
        cell.classList.remove("is-selected");
        cell.setAttribute("aria-expanded", "false");
      }
    });
  }

  function shouldIgnoreCellToggle(event) {
    return Boolean(
      event.target.closest(
        "a, button, input, select, textarea, label, form, .program-slot-picker, .program-day-cell__actions, .program-day-cell__menu, .card"
      )
    );
  }

  function toggleSlotCard(cell) {
    const targetId = cell.dataset.slotCardTarget;
    if (!targetId) return;

    const weekRow = cell.closest(".program-week-row");
    const card = weekRow?.querySelector(`#${CSS.escape(targetId)}`);
    if (!card) return;

    const shouldOpen = card.hidden;
    closeSlotCards(weekRow, shouldOpen ? targetId : null);

    card.hidden = !shouldOpen;
    cell.classList.toggle("is-selected", shouldOpen);
    cell.setAttribute("aria-expanded", shouldOpen ? "true" : "false");

    if (shouldOpen && window.lucide) {
      window.lucide.createIcons();
    }
  }

  function syncSearch(picker) {
    const input = picker.querySelector(".js-program-slot-search");
    const options = Array.from(picker.querySelectorAll(".js-program-slot-option"));
    if (!input) return;

    const query = input.value.trim().toLowerCase();
    options.forEach((option) => {
      const haystack = option.dataset.search || "";
      option.hidden = query && !haystack.includes(query);
    });
  }

  function syncPreview(radio) {
    const picker = radio.closest(".js-program-slot-picker");
    const preview = picker.querySelector(".js-program-slot-preview");
    const name = picker.querySelector(".js-program-slot-preview-name");
    const kpis = picker.querySelector(".js-program-slot-preview-kpis");
    if (!preview || !name || !kpis) return;

    name.textContent = radio.dataset.name || "Plan seleccionado";
    kpis.textContent = `${radio.dataset.kcal || 0} kcal · P ${radio.dataset.protein || 0}g · C ${radio.dataset.carbs || 0}g · F ${radio.dataset.fat || 0}g`;
    preview.hidden = false;
  }

  document.querySelectorAll(".program-day-cell.has-plan").forEach((cell) => {
    cell.addEventListener("click", (event) => {
      if (shouldIgnoreCellToggle(event)) return;
      toggleSlotCard(cell);
    });

    cell.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      if (shouldIgnoreCellToggle(event)) return;

      event.preventDefault();
      toggleSlotCard(cell);
    });
  });

  document.querySelectorAll(".js-program-slot-open").forEach((button) => {
    button.addEventListener("click", () => {
      const cell = button.closest(".program-day-cell");
      const picker = cell?.querySelector(".js-program-slot-picker");
      if (!picker) return;

      button.closest(".program-day-cell__menu")?.removeAttribute("open");

      const shouldOpen = picker.hidden;
      closeAllExcept(picker);
      if (shouldOpen) {
        closeSlotCards(cell?.closest(".program-week-row"));
      }
      picker.hidden = !shouldOpen;
      cell.classList.toggle("is-picking", shouldOpen);

      if (shouldOpen) {
        const search = picker.querySelector(".js-program-slot-search");
        search?.focus();
      }
    });
  });

  document.querySelectorAll(".js-program-slot-close").forEach((button) => {
    button.addEventListener("click", () => {
      const picker = button.closest(".js-program-slot-picker");
      picker.hidden = true;
      picker.closest(".program-day-cell")?.classList.remove("is-picking");
    });
  });

  pickers.forEach((picker) => {
    const search = picker.querySelector(".js-program-slot-search");
    if (search) {
      search.addEventListener("input", () => syncSearch(picker));
    }

    picker.querySelectorAll('input[name="dailyplan_id"]').forEach((radio) => {
      radio.addEventListener("change", () => syncPreview(radio));
    });
  });
});
