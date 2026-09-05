import { numeric, projectProgramWeekRows } from "./program_slot_projection.js";

document.addEventListener("DOMContentLoaded", () => {
  const page = document.querySelector("[data-program-dailyplans]");
  const picker = document.querySelector(".js-program-slot-picker-global");
  const form = picker?.querySelector(".js-program-slot-picker-form");
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

  function dispatchPickerEvent(name, step = null) {
    document.dispatchEvent(new CustomEvent(name, {
      detail: {
        sectionId: "program-slot-picker-section",
        ...(step ? { step } : {}),
      },
    }));
  }

  function showImpactStep() {
    dispatchPickerEvent("picker:step", "impact");
  }

  function syncPickerHeader(cell) {
    const replacing = cell?.classList.contains("has-plan");
    const title = picker?.querySelector("#program-slot-picker-title");
    const addIcon = picker?.querySelector('[data-program-slot-header-icon="add"]');
    const replaceIcon = picker?.querySelector('[data-program-slot-header-icon="replace"]');

    if (title) title.textContent = replacing ? "Reemplaza el Plan Diario" : "Agrega un Plan Diario";
    if (addIcon) addIcon.hidden = replacing;
    if (replaceIcon) replaceIcon.hidden = !replacing;
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
    form?.querySelectorAll('input[name="day_numbers"]').forEach((input) => input.remove());
    const selectedDays = getSelectedDayNumbers();

    selectedDays.forEach((dayNumber) => {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "day_numbers";
      input.value = dayNumber;
      form?.appendChild(input);
    });

    return selectedDays;
  }

  function selectedDaysHaveOccupiedSlots() {
    if (!picker) return false;
    return Array.from(picker.querySelectorAll('.js-program-slot-day-checkbox:checked'))
      .some((checkbox) => checkbox.dataset.occupied === "true");
  }


  function hasSelectedDailyplan() {
    return Boolean(picker?.querySelector('input[name="dailyplan_id"]:checked'));
  }

  function syncReturnToInput() {
    const input = picker?.querySelector(".js-program-slot-return-to");
    if (!input) return;
    input.value = "";
  }

  function preselectDailyplan(dailyplanId) {
    if (!picker || !dailyplanId) return false;
    const radio = Array.from(picker.querySelectorAll('input[name="dailyplan_id"]'))
      .find((input) => String(input.value) === String(dailyplanId));
    if (!radio) return false;

    radio.checked = true;
    syncPreview(radio);
    syncDaySelector(activeCell);
    hideOverwriteWarning();
    overwriteConfirmed = false;
    hideSearchResults();
    renderWeekProjection();
    showImpactStep();
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
      <div class="program-slot-picker__days-title">
        <i data-lucide="calendar-days" aria-hidden="true"></i>
        <span>Asignar este plan en</span>
      </div>
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

  function renderKpiRow(label, grams, allocValue, kind, ppk = null) {
    return `
      <div class="picker-result-kpi__row">
        <div class="picker-result-kpi__label">${label}</div>
        <div class="picker-result-kpi__ppk${ppk === null ? " is-empty" : ""}"${ppk === null ? ' aria-hidden="true"' : ""}>${ppk === null ? "" : `${Number(ppk).toFixed(1)}g/kg`}</div>
        <div class="picker-result-kpi__grams">${grams}g</div>
        <div class="picker-result-kpi__alloc">
          ${renderAllocBar(allocValue, kind)}
        </div>
      </div>
    `;
  }

  function renderDailyplanPickerCard({ name, kcal, protein, carbs, fat, ppk, proteinAlloc, carbsAlloc, fatAlloc }) {
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
          ${renderKpiRow("Protein", protein, proteinAlloc, "protein", ppk)}
          ${renderKpiRow("Carbs", carbs, carbsAlloc, "carbs")}
          ${renderKpiRow("Fat", fat, fatAlloc, "fat")}
        </div>
      </div>
    `;
  }

  function renderSelectedKpiRow(label, grams, allocation, kind, ppk = null) {
    return `
      <div class="picker-summary-kpi__row">
        <div class="picker-summary-kpi__label">${label}</div>
        <div class="picker-summary-kpi__ppk${ppk === null ? " is-empty" : ""}">${ppk === null ? "" : `${numeric(ppk).toFixed(1)}g/kg`}</div>
        <div class="picker-summary-kpi__grams">${numeric(grams).toFixed(0)}g</div>
        <div class="picker-summary-kpi__alloc">
          ${renderAllocBar(allocation, kind)}
        </div>
      </div>
    `;
  }

  function renderSelectedDailyplanCard(dailyplan) {
    const allocation = dailyplan.alloc || {};
    return `
      <div class="picker-summary-card picker-summary-card--selected picker-summary-card--dailyplan">
        <div class="entity-card__main card-main">
          <div class="entity-card__title card-title">
            <div class="entity-heading card-title-comp">
              <div class="main-title">
                <p class="card-title-eyebrow">
                  <i data-lucide="clipboard-list" class="card-title-eyebrow__icon dailyplan" aria-hidden="true"></i>
                  <span>Plan diario seleccionado</span>
                </p>
                <h3>${escapeHtml(dailyplan.name || "Plan diario")}</h3>
              </div>
            </div>
          </div>

          <div class="entity-card__kpi card-kpi">
            <div class="picker-summary-kpi">
              <div class="picker-summary-kpi__total">
                <p>Calories</p>
                <strong>${numeric(dailyplan.total_kcal).toFixed(0)}</strong>
              </div>
              <div class="picker-summary-kpi__macros">
                ${renderSelectedKpiRow("Protein", dailyplan.protein, allocation.protein, "protein", dailyplan.ppk)}
                ${renderSelectedKpiRow("Carbs", dailyplan.carbs, allocation.carbs, "carbs")}
                ${renderSelectedKpiRow("Fat", dailyplan.fat, allocation.fat, "fat")}
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function getSelectedDailyplan() {
    const selectedId = picker?.querySelector('input[name="dailyplan_id"]:checked')?.value;
    if (!selectedId) return null;
    return getDailyplans().find((dailyplan) => String(dailyplan.id) === String(selectedId)) || null;
  }

  function getActiveWeekScope() {
    return activeCell?.closest(".js-program-week-scope") || null;
  }

  function getActiveWeekRows() {
    const scope = getActiveWeekScope();
    if (!scope) return [];

    try {
      return JSON.parse(scope.dataset.programWeekRows || "[]");
    } catch (error) {
      return [];
    }
  }

  function buildProjectedWeekRows() {
    const selectedPlan = getSelectedDailyplan();
    return projectProgramWeekRows(
      getActiveWeekRows(),
      selectedPlan,
      getSelectedDayNumbers(),
    );
  }

  function renderGridAllocation(value, kind) {
    const allocation = Math.max(0, Math.min(numeric(value), 100));
    return `
      <div class="alloc-cell alloc-cell--grid" style="--alloc: ${allocation};">
        <div class="alloc-bar alloc-bar--${kind}"></div>
        <span class="alloc-text${allocation > 0 ? " alloc-text--shadowed" : ""}">${allocation.toFixed(0)}%</span>
      </div>
    `;
  }

  function renderMacroDistribution(distribution = {}) {
    const values = {
      protein: numeric(distribution.protein),
      carbs: numeric(distribution.carbs),
      fat: numeric(distribution.fat),
    };
    const label = `Distribución calórica: proteínas ${values.protein.toFixed(0)}%, carbohidratos ${values.carbs.toFixed(0)}%, grasas ${values.fat.toFixed(0)}%`;
    const segments = Object.entries(values)
      .filter(([, value]) => value > 0)
      .map(([kind, value]) => `<div class="macro-kcal-distribution__segment macro-kcal-distribution__segment--${kind}" style="--macro-kcal-share: ${value};"></div>`)
      .join("");

    return `<div class="macro-kcal-distribution" role="img" aria-label="${escapeHtml(label)}" title="P ${values.protein.toFixed(0)}% · C ${values.carbs.toFixed(0)}% · G ${values.fat.toFixed(0)}%">${segments}</div>`;
  }

  function renderProjectedIdentity(row) {
    const badge = row.is_projected
      ? `<span class="program-slot-picker__projection-badge">${escapeHtml(row.projected_label)}</span>`
      : "";
    const icon = row.has_plan
      ? '<i data-lucide="clipboard-list" class="program-week-day-table__dailyplan-icon" aria-hidden="true"></i>'
      : '<span class="program-week-day-table__dailyplan-placeholder" aria-hidden="true">-</span>';

    return `
      <span class="program-week-day-table__identity">
        ${icon}
        <span class="program-week-day-table__identity-copy">
          <span class="program-week-day-table__day-name">${escapeHtml(row.day_name)}</span>
          <span class="program-slot-picker__projection-plan-line">
            <span class="program-week-day-table__plan-name">${escapeHtml(row.dailyplan_name)}</span>
            ${badge}
          </span>
        </span>
      </span>
    `;
  }

  function renderProjectionRow(rowElement, row) {
    const isEmpty = Boolean(row.is_empty);
    rowElement.classList.toggle("is-empty", isEmpty);
    rowElement.classList.toggle("is-projected", Boolean(row.is_projected));
    rowElement.querySelector(".data-grid-cell--program-day").innerHTML = renderProjectedIdentity(row);

    const setText = (selector, value) => {
      const node = rowElement.querySelector(selector);
      if (node) node.textContent = isEmpty ? "-" : value;
    };

    setText(".data-grid-cell--kcal", numeric(row.total_kcal).toFixed(0));
    const ppkCell = rowElement.querySelector(".data-grid-cell--ppk");
    if (ppkCell) {
      ppkCell.innerHTML = isEmpty
        ? "-"
        : `<span class="program-week-day-table__ppk-value">${numeric(row.ppk).toFixed(1)}</span>`;
    }

    const macroCells = rowElement.querySelectorAll(".data-grid-cell--macro");
    [row.protein, row.carbs, row.fat].forEach((value, index) => {
      if (macroCells[index]) macroCells[index].textContent = isEmpty ? "-" : numeric(value).toFixed(0);
    });

    const kcalShare = rowElement.querySelector(".data-grid-cell--kcal-share");
    if (kcalShare) kcalShare.innerHTML = isEmpty ? "-" : renderGridAllocation(row.kcal_share, "kcal");

    const distribution = rowElement.querySelector(".data-grid-cell--kcal-distribution");
    if (distribution) distribution.innerHTML = isEmpty ? "-" : renderMacroDistribution(row.kcal_distribution);

    const allocationCells = rowElement.querySelectorAll(".data-grid-cell--alloc");
    ["protein", "carbs", "fat"].forEach((kind, index) => {
      if (allocationCells[index]) {
        allocationCells[index].innerHTML = isEmpty ? "-" : renderGridAllocation(row.alloc?.[kind], kind);
      }
    });
  }

  function cloneProjectionPanel() {
    const source = getActiveWeekScope()?.querySelector(".program-week-day-panels");
    if (!source) return null;

    const clone = source.cloneNode(true);
    clone.classList.add("program-slot-picker__projection-panel");
    clone.querySelectorAll('[data-target*="program-week-days-edit-"]').forEach((node) => node.remove());
    clone.querySelectorAll('[id^="program-week-days-edit-"]').forEach((node) => node.remove());

    const idMap = new Map();
    clone.querySelectorAll("[id]").forEach((node) => {
      const oldId = node.id;
      const newId = `${oldId}-picker-projection`;
      idMap.set(`#${oldId}`, `#${newId}`);
      node.id = newId;
    });

    clone.querySelectorAll("[data-target]").forEach((node) => {
      node.dataset.target = idMap.get(node.dataset.target) || node.dataset.target;
    });
    ["defaultDesktop", "defaultMobile"].forEach((key) => {
      clone.dataset[key] = idMap.get(clone.dataset[key]) || clone.dataset[key];
    });

    clone.removeAttribute("data-switching");
    return clone;
  }

  function renderWeekProjection() {
    const container = picker?.querySelector(".js-program-slot-projection");
    const title = picker?.querySelector(".js-program-slot-projection-title");
    const rows = buildProjectedWeekRows();
    const panel = cloneProjectionPanel();
    if (!container || !panel || !rows.length) return;

    const weekNumber = activeCell?.dataset.weekNumber || "";
    if (title) title.textContent = weekNumber ? `Semana ${weekNumber} resultante` : "Semana resultante";

    panel.querySelectorAll("[data-day-number]").forEach((rowElement) => {
      const row = rows.find((item) => Number(item.day_number) === Number(rowElement.dataset.dayNumber));
      if (row) renderProjectionRow(rowElement, row);
    });

    container.replaceChildren(panel);
    activateDefaultDetailBlock(container);
    window.lucide?.createIcons?.();
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
      const ppk = Number(dailyplan.ppk) || 0;
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
            data-ppk="${ppk}"
            data-kcal-protein="${Number(dailyplan.kcal_protein) || 0}"
            data-kcal-carbs="${Number(dailyplan.kcal_carbs) || 0}"
            data-kcal-fat="${Number(dailyplan.kcal_fat) || 0}"
            data-protein-alloc="${proteinAlloc}"
            data-carbs-alloc="${carbsAlloc}"
            data-fat-alloc="${fatAlloc}"
            required
          >

          ${renderDailyplanPickerCard({ name, kcal, protein, carbs, fat, ppk, proteinAlloc, carbsAlloc, fatAlloc })}
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
    const search = picker.querySelector(".js-program-slot-search");
    const preview = picker.querySelector(".js-program-slot-preview");
    const projection = picker.querySelector(".js-program-slot-projection");
    if (search) search.value = "";
    const returnTo = picker.querySelector(".js-program-slot-return-to");
    if (returnTo) returnTo.value = "";
    if (preview) {
      preview.hidden = true;
      preview.innerHTML = "";
    }
    if (projection) projection.innerHTML = "";
    const days = picker.querySelector(".js-program-slot-days");
    if (days) {
      days.hidden = true;
      days.innerHTML = "";
    }
    hideOverwriteWarning();
    overwriteConfirmed = false;
    form?.querySelectorAll('input[name="day_numbers"]').forEach((input) => input.remove());
    picker.querySelectorAll('input[name="dailyplan_id"]').forEach((radio) => {
      radio.checked = false;
    });
    syncSearch();
    showSearchResults();
    activeCell?.classList.remove("is-picking");
    activeCell = null;
    dispatchPickerEvent("picker:close");
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
    hideOverwriteWarning();
    overwriteConfirmed = false;
    renderWeekProjection();
    showImpactStep();
  }

  function syncPreview(radio) {
    if (!picker) return;
    const preview = picker.querySelector(".js-program-slot-preview");
    if (!preview) return;

    const dailyplan = getDailyplans()
      .find((item) => String(item.id) === String(radio.value));
    if (!dailyplan) return;

    preview.innerHTML = renderSelectedDailyplanCard(dailyplan);
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

    const shouldOpen = options.forceOpen || !picker.open || activeCell !== cell;
    closePicker();

    if (!shouldOpen) return;

    const weekInput = picker.querySelector('input[name="week_number"]');
    const dayInput = picker.querySelector('input[name="day_number"]');
    if (weekInput) weekInput.value = cell.dataset.weekNumber || "";
    if (dayInput) dayInput.value = cell.dataset.dayNumber || "";
    syncReturnToInput();

    activeCell = cell;
    syncPickerHeader(cell);
    cell.classList.add("is-picking");
    closeSlotCards(cell.closest(".js-program-week-scope"), options.keepSlotCardTarget || null);
    showSearchResults();
    hideOverwriteWarning();
    overwriteConfirmed = false;
    dispatchPickerEvent("picker:open", "selection");

    if (options.preselectDailyplanId) {
      preselectDailyplan(options.preselectDailyplanId);
    }

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

  if (picker && form) {
    picker.addEventListener("change", (event) => {
      if (event.target.matches(".js-program-slot-day-checkbox")) {
        hideOverwriteWarning();
        overwriteConfirmed = false;
        renderWeekProjection();
      }
    });

    form.addEventListener("submit", (event) => {
      if (!hasSelectedDailyplan()) {
        event.preventDefault();
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
      if (typeof form.requestSubmit === "function") {
        form.requestSubmit();
      } else {
        form.submit();
      }
    });

    picker.querySelector('[data-picker-go-to="selection"]')?.addEventListener("click", () => {
      showSearchResults();
    });

    document.addEventListener("picker:dismiss", (event) => {
      if (event.detail?.sectionId !== "program-slot-picker-section") return;
      event.preventDefault();
      closePicker();
    });
  }
});
