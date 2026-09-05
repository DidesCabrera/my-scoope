document.addEventListener("DOMContentLoaded", () => {
  const page = document.querySelector("[data-program-dailyplans]");
  const picker = document.querySelector(".js-program-slot-picker-global");
  let activeCell = null;
  let optionsRendered = false;
  let overwriteConfirmed = false;

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

  function escapeCssIdentifier(value) {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(String(value ?? ""));
    }
    return String(value ?? "").replace(/[^a-zA-Z0-9_-]/g, "\\$&");
  }

  function resetDesktopPickerSpace() {
    const appContent = getAppContent();
    if (!appContent) return;

    if (appContent.dataset.programSlotPickerPreviousPaddingBottom !== undefined) {
      appContent.style.paddingBottom = appContent.dataset.programSlotPickerPreviousPaddingBottom;
      delete appContent.dataset.programSlotPickerPreviousPaddingBottom;
    }
    appContent.classList.remove("has-program-slot-picker-space");
  }

  function reserveDesktopPickerSpace() {
    if (!picker || picker.hidden || isMobileViewport()) {
      resetDesktopPickerSpace();
      return;
    }

    const appContent = getAppContent();
    if (!appContent) return;

    if (appContent.dataset.programSlotPickerPreviousPaddingBottom === undefined) {
      appContent.dataset.programSlotPickerPreviousPaddingBottom = appContent.style.paddingBottom || "";
    }

    window.requestAnimationFrame(() => {
      if (!picker || picker.hidden || isMobileViewport()) return;
      const currentPadding = appContent.dataset.programSlotPickerPreviousPaddingBottom || "0px";
      const space = Math.ceil(picker.getBoundingClientRect().height + 64);
      appContent.style.paddingBottom = `calc(${currentPadding || "0px"} + ${space}px)`;
      appContent.classList.add("has-program-slot-picker-space");
    });
  }

  function getWeekCells(cell = activeCell) {
    const weekGrid = cell?.closest(".program-week-child-card__days");
    return weekGrid ? Array.from(weekGrid.querySelectorAll(".program-day-cell")) : [];
  }

  function getSelectedDayNumbers() {
    if (!picker) return [];
    return Array.from(picker.querySelectorAll('.js-program-slot-day-checkbox:checked'))
      .map((checkbox) => checkbox.value)
      .filter(Boolean);
  }

  function syncDayNumberInputs() {
    if (!picker) return [];
    picker.querySelectorAll('input[name="day_numbers"]').forEach((input) => input.remove());
    const selectedDays = getSelectedDayNumbers();

    selectedDays.forEach((dayNumber) => {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "day_numbers";
      input.value = dayNumber;
      picker.appendChild(input);
    });

    return selectedDays;
  }

  function selectedDaysHaveOccupiedSlots() {
    if (!picker) return false;
    return Array.from(picker.querySelectorAll('.js-program-slot-day-checkbox:checked'))
      .some((checkbox) => checkbox.dataset.occupied === "true");
  }


  function setPickerActionsVisible(isVisible) {
    const actions = picker?.querySelector(".program-slot-picker__actions");
    if (actions) actions.hidden = !isVisible;
  }

  function hasSelectedDailyplan() {
    return Boolean(picker?.querySelector('input[name="dailyplan_id"]:checked'));
  }

  function syncReturnToInput() {
    const input = picker?.querySelector(".js-program-slot-return-to");
    if (!input) return;
    input.value = "";
  }

  function preselectDailyplan(dailyplanId, options = {}) {
    if (!picker || !dailyplanId) return false;
    const radio = Array.from(picker.querySelectorAll('input[name="dailyplan_id"]'))
      .find((input) => String(input.value) === String(dailyplanId));
    if (!radio) return false;

    radio.checked = true;
    syncPreview(radio);
    syncDaySelector(activeCell);
    setPickerActionsVisible(true);
    hideOverwriteWarning();
    overwriteConfirmed = false;

    if (options.keepSearchResults) {
      showSearchResults();
    } else {
      hideSearchResults();
    }
    return true;
  }

  function hideOverwriteWarning() {
    const warning = picker?.querySelector(".js-program-slot-overwrite-warning");
    if (warning) warning.hidden = true;
  }

  function showOverwriteWarning() {
    const warning = picker?.querySelector(".js-program-slot-overwrite-warning");
    if (warning) warning.hidden = false;
  }

  function syncDaySelector(cell = activeCell) {
    if (!picker || !cell) return;
    const container = picker.querySelector(".js-program-slot-days");
    if (!container) return;

    const activeDay = cell.dataset.dayNumber || "";
    const cells = getWeekCells(cell);
    if (!cells.length) {
      container.hidden = true;
      container.innerHTML = "";
      return;
    }

    container.innerHTML = `
      <div class="program-slot-picker__days-title">Usar también en</div>
      <div class="program-slot-picker__day-list" role="group" aria-label="Días para asignar este plan">
        ${cells.map((dayCell) => {
          const dayNumber = escapeHtml(dayCell.dataset.dayNumber || "");
          const dayLabel = escapeHtml(dayCell.dataset.dayLabel || `Día ${dayNumber}`);
          const isOccupied = dayCell.classList.contains("has-plan");
          const isChecked = String(dayCell.dataset.dayNumber || "") === String(activeDay);
          return `
            <label class="program-slot-picker__day-option${isOccupied ? " is-occupied" : ""}">
              <input
                type="checkbox"
                class="js-program-slot-day-checkbox"
                value="${dayNumber}"
                data-occupied="${isOccupied ? "true" : "false"}"
                ${isChecked ? "checked" : ""}
              >
              <span>${dayLabel.slice(0, 3)}</span>
            </label>
          `;
        }).join("")}
      </div>
    `;
    container.hidden = false;
  }

  function renderAllocBar(value, kind) {
    const pct = Math.max(0, Math.min(Math.round(Number(value) || 0), 100));
    return `
      <div class="picker-alloc-item alloc-bar-comp alloc-bar-comp--kpi" style="--alloc: ${pct};">
        <div class="alloc-bar-bg"></div>
        <div class="alloc-bar-fill alloc-bar-fill--${kind}"></div>
        <span class="alloc-bar-text">${pct}%</span>
      </div>
    `;
  }

  function renderKpiRow(label, grams, allocValue, kind) {
    return `
      <div class="picker-result-kpi__row">
        <div class="picker-result-kpi__label">${label}</div>
        <div class="picker-result-kpi__ppk is-empty" aria-hidden="true"></div>
        <div class="picker-result-kpi__grams">${grams}g</div>
        <div class="picker-result-kpi__alloc">
          ${renderAllocBar(allocValue, kind)}
        </div>
      </div>
    `;
  }

  function renderDailyplanPickerCard({ name, kcal, protein, carbs, fat, proteinAlloc, carbsAlloc, fatAlloc }) {
    return `
      <div class="picker-result-title">
        <div class="picker-result-title__main">
          <div class="picker-result-title__name-row">
            <i data-lucide="clipboard-list" class="picker-result-title__icon dailyplan"></i>
            <span class="picker-result-title__name">${name}</span>
          </div>
          <div class="picker-result-badges" aria-label="Características">
            <span class="picker-result-badge picker-result-badge--verified">Plan diario</span>
          </div>
        </div>
      </div>

      <div class="picker-result-kpi">
        <div class="picker-result-kpi__total">
          <p>Calories</p>
          <strong>${kcal}</strong>
        </div>

        <div class="picker-result-kpi__macros">
          ${renderKpiRow("Protein", protein, proteinAlloc, "protein")}
          ${renderKpiRow("Carbs", carbs, carbsAlloc, "carbs")}
          ${renderKpiRow("Fat", fat, fatAlloc, "fat")}
        </div>
      </div>
    `;
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
      const alloc = dailyplan.alloc || {};
      const proteinAlloc = Number(alloc.protein) || 0;
      const carbsAlloc = Number(alloc.carbs) || 0;
      const fatAlloc = Number(alloc.fat) || 0;

      return `
        <label class="program-slot-picker__option picker-item picker-result picker-result--dailyplan js-program-slot-option" data-search="${name.toLowerCase()}">
          <input
            type="radio"
            name="dailyplan_id"
            value="${escapeHtml(dailyplan.id)}"
            data-name="${name}"
            data-kcal="${kcal}"
            data-protein="${protein}"
            data-carbs="${carbs}"
            data-fat="${fat}"
            data-protein-alloc="${proteinAlloc}"
            data-carbs-alloc="${carbsAlloc}"
            data-fat-alloc="${fatAlloc}"
            required
          >

          ${renderDailyplanPickerCard({ name, kcal, protein, carbs, fat, proteinAlloc, carbsAlloc, fatAlloc })}
        </label>
      `;
    }).join("");

    results.querySelectorAll('input[name="dailyplan_id"]').forEach((radio) => {
      radio.addEventListener("change", () => syncSelectedPlanFlow(radio));
    });

    results.querySelectorAll(".js-program-slot-option").forEach((option) => {
      option.addEventListener("click", () => {
        const radio = option.querySelector('input[name="dailyplan_id"]');
        window.requestAnimationFrame(() => {
          if (radio?.checked) syncSelectedPlanFlow(radio);
        });
      });
    });
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
    optionsRendered = true;
  }

  function closePicker() {
    if (!picker) return;
    picker.hidden = true;
    const search = picker.querySelector(".js-program-slot-search");
    const preview = picker.querySelector(".js-program-slot-preview");
    if (search) search.value = "";
    const returnTo = picker.querySelector(".js-program-slot-return-to");
    if (returnTo) returnTo.value = "";
    if (preview) preview.hidden = true;
    setPickerActionsVisible(false);
    const days = picker.querySelector(".js-program-slot-days");
    if (days) {
      days.hidden = true;
      days.innerHTML = "";
    }
    hideOverwriteWarning();
    overwriteConfirmed = false;
    picker.querySelectorAll('input[name="day_numbers"]').forEach((input) => input.remove());
    picker.querySelectorAll('input[name="dailyplan_id"]').forEach((radio) => {
      radio.checked = false;
    });
    syncSearch();
    showSearchResults();
    activeCell?.classList.remove("is-picking");
    activeCell = null;
    resetDesktopPickerSpace();
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

  function getAppContent() {
    return document.querySelector(".app-content") || document.body;
  }

  function placePickerForCell(cell) {
    if (!picker || !cell) return;

    if (isMobileViewport()) {
      const planSection = cell.closest(".program-week-child-card__plan-section");
      const daysGrid = planSection?.querySelector(".program-week-child-card__days");
      if (planSection && daysGrid) {
        daysGrid.insertAdjacentElement("afterend", picker);
        return;
      }
    }

    getAppContent().appendChild(picker);
  }

  function positionDesktopPickerInAppContent(cell = activeCell) {
    if (!picker || isMobileViewport()) return;

    const appContent = getAppContent();
    const appRect = appContent.getBoundingClientRect();
    const appTop = appRect.top + window.scrollY;
    const daysGrid = cell?.closest(".program-week-child-card__plan-section")
      ?.querySelector(".program-week-child-card__days");
    const anchor = daysGrid || cell?.closest(".js-program-week-scope") || cell;

    if (!anchor) return;

    const anchorBottom = anchor.getBoundingClientRect().bottom + window.scrollY;
    const nextTop = Math.max(24, anchorBottom - appTop + 12);

    picker.style.setProperty("--program-slot-picker-top", `${Math.round(nextTop)}px`);
  }

  function scrollMobileWeekIntoView(cell) {
    if (!isMobileViewport() || !cell) return;

    const planSection = cell.closest(".program-week-child-card__plan-section");
    const daysGrid = planSection?.querySelector(".program-week-child-card__days");
    const target = daysGrid || planSection;
    if (!target) return;

    window.requestAnimationFrame(() => {
      target.scrollIntoView({ block: "start", behavior: "smooth" });
    });
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

  const FULL_DAY_LABELS = {
    1: "Lunes",
    2: "Martes",
    3: "Miércoles",
    4: "Jueves",
    5: "Viernes",
    6: "Sábado",
    7: "Domingo",
  };

  function getFullDayLabel(cell) {
    const dayNumber = Number(cell?.dataset.dayNumber || 0);
    return FULL_DAY_LABELS[dayNumber] || cell?.dataset.dayLabel || "Día seleccionado";
  }

  function getWeekDayTitle(cell) {
    const weekNumber = cell?.dataset.weekNumber || "";
    const dayLabel = getFullDayLabel(cell);
    return weekNumber ? `Semana ${weekNumber} ⋅ ${dayLabel}` : dayLabel;
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

    let card = weekRow.querySelector(`#${escapeCssIdentifier(targetId)}`);
    if (card) return card;

    const dayLabel = getFullDayLabel(cell);
    const dayTitle = getWeekDayTitle(cell);
    container.insertAdjacentHTML("beforeend", `
      <div id="${escapeHtml(targetId)}" class="program-day-empty-card js-program-slot-card" hidden>
        <h4 class="program-day-selected-card__day-title">${escapeHtml(dayTitle)}</h4>
        <div class="program-day-empty-card__content">
          <i data-lucide="clipboard-list" class="program-day-empty-card__icon" aria-hidden="true"></i>
          <div class="program-day-empty-card__body">
            <strong>${escapeHtml(dayLabel)} no tiene plan asignado.</strong>
            <span>Elije un plan para este día.</span>
          </div>
        </div>
      </div>
    `);
    return weekRow.querySelector(`#${escapeCssIdentifier(targetId)}`);
  }

  async function ensureSlotCard(cell, weekRow, targetId) {
    let card = weekRow?.querySelector(`#${escapeCssIdentifier(targetId)}`);
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
      card = weekRow.querySelector(`#${escapeCssIdentifier(targetId)}`);
      if (card) {
        card.hidden = true;
        activateDefaultDetailBlock(card);
      }
      return card;
    } finally {
      cell.classList.remove("is-loading-card");
    }
  }

  async function toggleSlotCard(cell, forceOpen = false, options = {}) {
    const targetId = getSlotCardTarget(cell);
    if (!targetId) return;

    const weekRow = cell.closest(".js-program-week-scope");
    const card = await ensureSlotCard(cell, weekRow, targetId);
    if (!card) return;

    const shouldOpen = forceOpen || card.hidden;
    if (!options.keepPicker) {
      closePicker();
    }
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

  function showSearchResults() {
    const results = picker?.querySelector(".js-program-slot-results");
    if (!results) return;
    results.hidden = false;
    results.classList.remove("is-hidden");
    syncSearch();
  }

  function hideSearchResults() {
    const results = picker?.querySelector(".js-program-slot-results");
    if (!results) return;
    results.hidden = true;
    results.classList.add("is-hidden");
  }

  function syncSelectedPlanFlow(radio) {
    syncPreview(radio);
    syncDaySelector(activeCell);
    hideSearchResults();
    setPickerActionsVisible(true);
    hideOverwriteWarning();
    overwriteConfirmed = false;
  }

  function syncPreview(radio) {
    if (!picker) return;
    const preview = picker.querySelector(".js-program-slot-preview");
    if (!preview) return;

    const name = escapeHtml(radio.dataset.name || "Plan seleccionado");
    const kcal = formatNumber(radio.dataset.kcal);
    const protein = formatNumber(radio.dataset.protein);
    const carbs = formatNumber(radio.dataset.carbs);
    const fat = formatNumber(radio.dataset.fat);
    const proteinAlloc = Number(radio.dataset.proteinAlloc) || 0;
    const carbsAlloc = Number(radio.dataset.carbsAlloc) || 0;
    const fatAlloc = Number(radio.dataset.fatAlloc) || 0;

    preview.classList.add("picker-result", "picker-result--dailyplan");
    preview.innerHTML = `
      <div class="program-slot-picker__preview-title">Plan seleccionado</div>
      ${renderDailyplanPickerCard({
        name,
        kcal,
        protein,
        carbs,
        fat,
        proteinAlloc,
        carbsAlloc,
        fatAlloc,
      })}
    `;
    preview.hidden = false;

    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  }

  document.querySelectorAll(".program-day-cell").forEach((cell) => {
    cell.addEventListener("click", (event) => {
      if (shouldIgnoreCellToggle(event)) return;
      if (cell.classList.contains("is-empty")) {
        openEmptySlotInteraction(cell);
        return;
      }
      toggleSlotCard(cell);
    });

    cell.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      if (shouldIgnoreCellToggle(event)) return;

      event.preventDefault();
      if (cell.classList.contains("is-empty")) {
        openEmptySlotInteraction(cell);
        return;
      }
      toggleSlotCard(cell);
    });
  });

  function openPickerForCell(cell, options = {}) {
    if (!picker || !cell) return;

    renderOptions();

    const shouldOpen = options.forceOpen || picker.hidden || activeCell !== cell;
    closePicker();

    if (!shouldOpen) return;

    const weekInput = picker.querySelector('input[name="week_number"]');
    const dayInput = picker.querySelector('input[name="day_number"]');
    if (weekInput) weekInput.value = cell.dataset.weekNumber || "";
    if (dayInput) dayInput.value = cell.dataset.dayNumber || "";
    syncReturnToInput();

    placePickerForCell(cell);
    picker.hidden = false;
    activeCell = cell;
    cell.classList.add("is-picking");
    closeSlotCards(cell.closest(".js-program-week-scope"), options.keepSlotCardTarget || null);
    showSearchResults();
    setPickerActionsVisible(false);
    hideOverwriteWarning();
    overwriteConfirmed = false;

    if (options.preselectDailyplanId) {
      preselectDailyplan(options.preselectDailyplanId, {
        keepSearchResults: Boolean(options.keepSearchResults),
      });
    }

    positionDesktopPickerInAppContent(cell);
    reserveDesktopPickerSpace();
    scrollMobileWeekIntoView(cell);

    const search = picker.querySelector(".js-program-slot-search");
    if (isMobileViewport()) {
      search?.blur();
    } else {
      search?.focus();
    }
    if (window.lucide) window.lucide.createIcons();
  }


  async function openEmptySlotInteraction(cell) {
    if (!cell) return;
    const targetId = getSlotCardTarget(cell);
    await toggleSlotCard(cell, true, { keepPicker: true });
    openPickerForCell(cell, { keepSlotCardTarget: targetId });
  }

  document.addEventListener("click", (event) => {
    const slotButton = event.target.closest(".js-program-slot-open");
    if (slotButton) {
      event.preventDefault();
      event.stopPropagation();
      const cell = slotButton.closest(".program-day-cell");
      slotButton.closest(".program-day-cell__menu")?.removeAttribute("open");
      if (cell?.classList.contains("is-empty")) {
        openEmptySlotInteraction(cell);
      } else {
        openPickerForCell(cell);
      }
      return;
    }

    const cardButton = event.target.closest(".js-program-slot-open-from-card");
    if (!cardButton) return;

    event.preventDefault();
    event.stopPropagation();
    const weekRow = cardButton.closest(".js-program-week-scope");
    const weekNumber = cardButton.dataset.weekNumber;
    const dayNumber = cardButton.dataset.dayNumber;
    const selector = `.program-day-cell[data-week-number="${escapeCssIdentifier(weekNumber || "")}"][data-day-number="${escapeCssIdentifier(dayNumber || "")}"]`;
    const cell = weekRow?.querySelector(selector);
    openPickerForCell(cell, { keepSlotCardTarget: getSlotCardTarget(cell) });
  });

  document.addEventListener("click", (event) => {
    const replaceButton = event.target.closest(".js-program-week-day-replace");
    if (!replaceButton) return;

    event.preventDefault();
    event.stopPropagation();

    const weekRow = replaceButton.closest(".js-program-week-scope") || document;
    const weekNumber = replaceButton.dataset.weekNumber;
    const dayNumber = replaceButton.dataset.dayNumber;
    const selector = `.program-day-cell[data-week-number="${escapeCssIdentifier(weekNumber || "")}"][data-day-number="${escapeCssIdentifier(dayNumber || "")}"]`;
    const cell = weekRow.querySelector(selector);
    if (!cell) return;

    openPickerForCell(cell, {
      keepSlotCardTarget: getSlotCardTarget(cell),
      preselectDailyplanId: replaceButton.dataset.dailyplanId,
      keepSearchResults: true,
      forceOpen: true,
    });
  });

  document.querySelectorAll(".js-program-slot-close").forEach((button) => {
    button.addEventListener("click", closePicker);
  });

  function openMondayCardInScope(scope) {
    const mondayCell = scope?.querySelector('.program-day-cell[data-day-number="1"]');
    if (mondayCell) toggleSlotCard(mondayCell, true);
  }

  document.addEventListener("program-week-tab:changed", (event) => {
    closePicker();
    const panel = event.detail?.targetId ? document.getElementById(event.detail.targetId) : null;
    openMondayCardInScope(panel);
  });

  function openInitialMondayCards() {
    const tabbedPanels = Array.from(document.querySelectorAll(".js-program-week-panel"));
    if (tabbedPanels.length) {
      tabbedPanels
        .filter((panel) => panel.classList.contains("is-active") && !panel.hidden)
        .forEach(openMondayCardInScope);
      return;
    }

    document.querySelectorAll(".js-program-week-scope").forEach(openMondayCardInScope);
  }

  openInitialMondayCards();

  if (picker) {
    const search = picker.querySelector(".js-program-slot-search");
    if (search) {
      search.addEventListener("input", () => {
        showSearchResults();
      });
      search.addEventListener("focus", showSearchResults);
      search.addEventListener("click", showSearchResults);
    }
  }

  window.addEventListener("resize", () => {
    if (!picker || picker.hidden || !activeCell) return;
    if (isMobileViewport()) {
      placePickerForCell(activeCell);
      return;
    }
    placePickerForCell(activeCell);
    positionDesktopPickerInAppContent(activeCell);
    reserveDesktopPickerSpace();
  });

  if (picker) {
    picker.addEventListener("change", (event) => {
      if (event.target.matches(".js-program-slot-day-checkbox")) {
        hideOverwriteWarning();
        overwriteConfirmed = false;
      }
    });

    picker.addEventListener("submit", (event) => {
      if (!hasSelectedDailyplan()) {
        event.preventDefault();
        setPickerActionsVisible(false);
        return;
      }

      const selectedDays = syncDayNumberInputs();
      if (!selectedDays.length) {
        event.preventDefault();
        return;
      }

      if (selectedDaysHaveOccupiedSlots() && !overwriteConfirmed) {
        event.preventDefault();
        showOverwriteWarning();
      }
    });

    picker.querySelector(".js-program-slot-overwrite-cancel")?.addEventListener("click", () => {
      overwriteConfirmed = false;
      hideOverwriteWarning();
    });

    picker.querySelector(".js-program-slot-overwrite-continue")?.addEventListener("click", () => {
      overwriteConfirmed = true;
      syncDayNumberInputs();
      if (typeof picker.requestSubmit === "function") {
        picker.requestSubmit();
      } else {
        picker.submit();
      }
    });
  }
});
