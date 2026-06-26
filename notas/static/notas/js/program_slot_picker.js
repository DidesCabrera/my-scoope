document.addEventListener("DOMContentLoaded", () => {
  const page = document.querySelector("[data-program-dailyplans]");
  const picker = document.querySelector(".js-program-slot-picker-global");
  let activeCell = null;
  let optionsRendered = false;

  function getDailyplans() {
    if (!page) return [];
    try {
      return JSON.parse(page.dataset.programDailyplans || "[]");
    } catch (error) {
      return [];
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatNumber(value) {
    const number = Number(value || 0);
    return Number.isFinite(number) ? number.toFixed(0) : "0";
  }

  function renderOptions() {
    if (!picker || optionsRendered) return;

    const results = picker.querySelector(".js-program-slot-results");
    if (!results) return;

    const dailyplans = getDailyplans();
    if (!dailyplans.length) {
      results.innerHTML = '<div class="program-slot-picker__empty picker-item">No hay planes diarios disponibles en tu librería.</div>';
      optionsRendered = true;
      return;
    }

    results.innerHTML = dailyplans.map((dailyplan) => {
      const name = escapeHtml(dailyplan.name || "Plan diario");
      const kcal = formatNumber(dailyplan.total_kcal);
      const protein = formatNumber(dailyplan.protein);
      const carbs = formatNumber(dailyplan.carbs);
      const fat = formatNumber(dailyplan.fat);

      return `
        <label class="program-slot-picker__option picker-item js-program-slot-option" data-search="${name.toLowerCase()}">
          <input
            type="radio"
            name="dailyplan_id"
            value="${escapeHtml(dailyplan.id)}"
            data-name="${name}"
            data-kcal="${kcal}"
            data-protein="${protein}"
            data-carbs="${carbs}"
            data-fat="${fat}"
            required
          >
          <span class="program-slot-picker__option-body">
            <span class="picker-item-header">
              <span class="picker-item-name">${name}</span>
              <span class="picker-item-unit">${kcal} kcal</span>
            </span>
            <span class="picker-item-meta">P ${protein}g · C ${carbs}g · F ${fat}g</span>
            <span class="picker-item-badges">
              <span class="picker-item-badge picker-item-badge--user">Plan diario</span>
            </span>
          </span>
        </label>
      `;
    }).join("");

    results.querySelectorAll('input[name="dailyplan_id"]').forEach((radio) => {
      radio.addEventListener("change", () => syncPreview(radio));
    });
    optionsRendered = true;
  }

  function closePicker() {
    if (!picker) return;
    picker.hidden = true;
    picker.querySelector(".js-program-slot-search").value = "";
    picker.querySelector(".js-program-slot-preview").hidden = true;
    picker.querySelectorAll('input[name="dailyplan_id"]').forEach((radio) => {
      radio.checked = false;
    });
    syncSearch();
    activeCell?.classList.remove("is-picking");
    activeCell = null;
  }

  function closeSlotCards(scope, exceptId = null) {
    const container = scope || document;

    container.querySelectorAll(".js-program-slot-card").forEach((card) => {
      if (card.id !== exceptId) {
        card.hidden = true;
      }
    });

    container.querySelectorAll(".program-day-cell").forEach((cell) => {
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

  function isMobileViewport() {
    return window.innerWidth <= 980;
  }

  function activateDefaultDetailBlock(root) {
    root.querySelectorAll(".card-detail-block").forEach((detailBlock) => {
      const defaultSelector = isMobileViewport()
        ? detailBlock.dataset.defaultMobile
        : detailBlock.dataset.defaultDesktop;
      const buttons = Array.from(detailBlock.querySelectorAll("[data-target]"));
      const panelSelectors = [...new Set(buttons.map((button) => button.dataset.target).filter(Boolean))];

      panelSelectors.forEach((selector) => {
        const panel = detailBlock.querySelector(selector);
        if (!panel) return;
        const isDefault = selector === defaultSelector;
        panel.style.display = isDefault ? "block" : "none";
        panel.style.opacity = isDefault ? "1" : "0";
        panel.classList.toggle("is-visible", isDefault);
      });

      buttons.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.target === defaultSelector);
      });
    });
  }

  function getSlotCardTarget(cell) {
    if (cell.dataset.slotCardTarget) return cell.dataset.slotCardTarget;
    const weekNumber = cell.dataset.weekNumber || "0";
    const dayNumber = cell.dataset.dayNumber || "0";
    return `program-week-${weekNumber}-day-${dayNumber}-empty-card`;
  }

  function renderEmptySlotCard(cell, weekRow, targetId) {
    const container = weekRow?.querySelector(".js-program-week-selected-cards");
    if (!container) return null;

    let card = weekRow.querySelector(`#${CSS.escape(targetId)}`);
    if (card) return card;

    const dayLabel = cell.dataset.dayLabel || "Este día";
    container.insertAdjacentHTML("beforeend", `
      <div id="${escapeHtml(targetId)}" class="program-day-empty-card js-program-slot-card" hidden>
        <i data-lucide="clipboard-list" class="program-day-empty-card__icon" aria-hidden="true"></i>
        <div class="program-day-empty-card__body">
          <strong>${escapeHtml(dayLabel)} no tiene plan asignado.</strong>
          <span>Elije un plan para este día.</span>
        </div>
      </div>
    `);
    return weekRow.querySelector(`#${CSS.escape(targetId)}`);
  }

  async function ensureSlotCard(cell, weekRow, targetId) {
    let card = weekRow?.querySelector(`#${CSS.escape(targetId)}`);
    if (card) return card;

    const container = weekRow?.querySelector(".js-program-week-selected-cards");
    if (!container) return null;

    const url = cell.dataset.slotCardUrl;
    if (!url) return renderEmptySlotCard(cell, weekRow, targetId);

    cell.classList.add("is-loading-card");
    try {
      const response = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!response.ok) return null;
      const payload = await response.json();
      container.insertAdjacentHTML("beforeend", payload.html || "");
      card = weekRow.querySelector(`#${CSS.escape(targetId)}`);
      if (card) {
        card.hidden = true;
        activateDefaultDetailBlock(card);
      }
      return card;
    } finally {
      cell.classList.remove("is-loading-card");
    }
  }

  async function toggleSlotCard(cell, forceOpen = false) {
    const targetId = getSlotCardTarget(cell);
    if (!targetId) return;

    const weekRow = cell.closest(".program-week-child-card");
    const card = await ensureSlotCard(cell, weekRow, targetId);
    if (!card) return;

    const shouldOpen = forceOpen || card.hidden;
    closePicker();
    closeSlotCards(weekRow, shouldOpen ? targetId : null);

    card.hidden = !shouldOpen;
    cell.classList.toggle("is-selected", shouldOpen);
    cell.setAttribute("aria-expanded", shouldOpen ? "true" : "false");

    if (shouldOpen && window.lucide) {
      window.lucide.createIcons();
    }
  }

  function syncSearch() {
    if (!picker) return;
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
    if (!picker) return;
    const preview = picker.querySelector(".js-program-slot-preview");
    const name = picker.querySelector(".js-program-slot-preview-name");
    const kpis = picker.querySelector(".js-program-slot-preview-kpis");
    if (!preview || !name || !kpis) return;

    name.textContent = radio.dataset.name || "Plan seleccionado";
    kpis.textContent = `${radio.dataset.kcal || 0} kcal · P ${radio.dataset.protein || 0}g · C ${radio.dataset.carbs || 0}g · F ${radio.dataset.fat || 0}g`;
    preview.hidden = false;
  }

  document.querySelectorAll(".program-day-cell").forEach((cell) => {
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

  function openPickerForCell(cell) {
    if (!picker || !cell) return;

    renderOptions();

    const shouldOpen = picker.hidden || activeCell !== cell;
    closePicker();

    if (!shouldOpen) return;

    const weekInput = picker.querySelector('input[name="week_number"]');
    const dayInput = picker.querySelector('input[name="day_number"]');
    if (weekInput) weekInput.value = cell.dataset.weekNumber || "";
    if (dayInput) dayInput.value = cell.dataset.dayNumber || "";

    cell.appendChild(picker);
    picker.hidden = false;
    activeCell = cell;
    cell.classList.add("is-picking");
    closeSlotCards(cell.closest(".program-week-child-card"));

    const search = picker.querySelector(".js-program-slot-search");
    search?.focus();
    if (window.lucide) window.lucide.createIcons();
  }

  document.querySelectorAll(".js-program-slot-open").forEach((button) => {
    button.addEventListener("click", () => {
      const cell = button.closest(".program-day-cell");
      button.closest(".program-day-cell__menu")?.removeAttribute("open");
      openPickerForCell(cell);
    });
  });

  document.addEventListener("click", (event) => {
    const button = event.target.closest(".js-program-slot-open-from-card");
    if (!button) return;

    const weekRow = button.closest(".program-week-child-card");
    const weekNumber = button.dataset.weekNumber;
    const dayNumber = button.dataset.dayNumber;
    const selector = `.program-day-cell[data-week-number="${CSS.escape(weekNumber || "")}"][data-day-number="${CSS.escape(dayNumber || "")}"]`;
    const cell = weekRow?.querySelector(selector);
    openPickerForCell(cell);
  });

  document.querySelectorAll(".js-program-slot-close").forEach((button) => {
    button.addEventListener("click", closePicker);
  });

  function openInitialMondayCards() {
    document.querySelectorAll(".program-week-child-card").forEach((weekRow) => {
      const mondayCell = weekRow.querySelector('.program-day-cell[data-day-number="1"]');
      if (mondayCell) toggleSlotCard(mondayCell, true);
    });
  }

  openInitialMondayCards();

  if (picker) {
    const search = picker.querySelector(".js-program-slot-search");
    if (search) {
      search.addEventListener("input", syncSearch);
    }
  }
});
