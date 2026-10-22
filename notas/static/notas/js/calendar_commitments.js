(() => {
  const page = document.querySelector(".calendar-commitments");
  if (!page) return;
  const today = page.dataset.today;
  const existing = new Set(JSON.parse(document.getElementById("calendar-commitments-existing").textContent));
  const selected = new Set();
  const grid = document.getElementById("calendar-commitments-grid");
  const title = document.getElementById("calendar-commitments-month-title");
  const previous = document.getElementById("calendar-commitments-previous");
  const next = document.getElementById("calendar-commitments-next");
  const count = document.getElementById("calendar-commitments-count");
  const summary = document.getElementById("calendar-commitments-selected");
  const inputs = document.getElementById("calendar-commitments-inputs");
  const submit = document.getElementById("calendar-commitments-submit");
  const error = document.getElementById("calendar-commitments-error");
  const form = document.getElementById("calendar-commitments-form");
  const foodFields = document.querySelector("[data-foods-url]");
  const foodAttachments = new Map();
  const foodPreviews = new Map();
  const notesByDate = new Map();
  const dayTitle = { shopping: "Día de compras", cooking: "Día de cocinar", training: "Día de entrenamiento" }[page.dataset.kind];
  let openFoodEditor = () => {};
  const weekdayLabels = ["L", "M", "M", "J", "V", "S", "D"];
  const todayDate = new Date(`${today}T12:00:00Z`);
  let year = todayDate.getUTCFullYear();
  let month = todayDate.getUTCMonth();
  const commitmentMonths = new Map();
  const commitmentRequests = new Set();
  const kindLabels = { shopping: "Hacer compras", cooking: "Cocinar", training: "Entrenar" };
  let refreshFoodCommitments = () => {};

  function monthKey(targetYear, targetMonth) { return `${targetYear}-${String(targetMonth + 1).padStart(2, "0")}`; }
  function kindsOn(value) {
    const monthData = commitmentMonths.get(value.slice(0, 7));
    return monthData ? monthData.commitments[value] ?? [] : existing.has(value) ? [page.dataset.kind] : [];
  }
  function hasPlan(value) { return commitmentMonths.get(value.slice(0, 7))?.plans.includes(value) ?? false; }
  function loadCommitmentMonth(targetYear, targetMonth) {
    const key = monthKey(targetYear, targetMonth);
    if (commitmentMonths.has(key) || commitmentRequests.has(key)) return;
    commitmentRequests.add(key);
    fetch(`${window.location.pathname}?month=${encodeURIComponent(key)}`, { headers: { Accept: "application/json" } })
      .then((response) => { if (!response.ok) throw new Error("commitments_unavailable"); return response.json(); })
      .then((data) => {
        commitmentMonths.set(key, data);
        if (monthKey(year, month) === key) render();
        refreshFoodCommitments(key);
      })
      .catch(() => {})
      .finally(() => commitmentRequests.delete(key));
  }
  function addCommitmentDots(button, value, draftShopping = false) {
    const kinds = [...new Set([...kindsOn(value), ...(draftShopping ? ["shopping"] : [])])];
    if (!kinds.length) return;
    const dots = document.createElement("span");
    dots.className = "calendar-commitments__dots";
    dots.setAttribute("aria-hidden", "true");
    for (const commitmentKind of kinds) {
      const dot = document.createElement("span");
      dot.className = `calendar-commitments__dot calendar-commitments__dot--${commitmentKind}`;
      dots.appendChild(dot);
    }
    button.appendChild(dots);
  }

  function iso(date) { return date.toISOString().slice(0, 10); }
  function dateLabel(value) {
    return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
      .format(new Date(`${value}T12:00:00Z`));
  }
  function updateSelection() {
    const dates = [...selected].sort();
    count.textContent = String(dates.length);
    submit.disabled = dates.length === 0;
    summary.replaceChildren();
    if (!dates.length) {
      summary.textContent = "Toca las fechas del calendario para seleccionarlas.";
      return;
    }
    for (const value of dates) {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "calendar-commitments__selected-row";
      row.setAttribute("aria-label", `Ver detalle: ${dayTitle} del ${dateLabel(value)}`);
      row.addEventListener("click", () => openFoodEditor(value));
      const symbol = document.createElement("i");
      symbol.setAttribute("data-lucide", { shopping: "shopping-basket", cooking: "cooking-pot", training: "dumbbell" }[page.dataset.kind]);
      symbol.setAttribute("aria-hidden", "true");
      row.appendChild(symbol);
      const details = document.createElement("div");
      const label = document.createElement("strong");
      label.textContent = `${dayTitle} · ${dateLabel(value)}`;
      details.appendChild(label);
      if (page.dataset.kind !== "training") {
        const attachment = foodAttachments.get(value);
        const status = document.createElement("small");
        status.textContent = attachment
          ? `Lista: ${dateLabel(attachment.start)} – ${dateLabel(attachment.end)}`
          : "Sin lista de alimentos adjunta";
        details.appendChild(status);
      }
      if (notesByDate.get(value)?.trim()) {
        const note = document.createElement("small");
        note.textContent = notesByDate.get(value).trim();
        details.appendChild(note);
      }
      row.appendChild(details);
      const chevron = document.createElement("i");
      chevron.setAttribute("data-lucide", "chevron-right");
      chevron.setAttribute("aria-hidden", "true");
      row.appendChild(chevron);
      summary.appendChild(row);
    }
    if (window.lucide) window.lucide.createIcons();
  }
  function render() {
    loadCommitmentMonth(year, month);
    title.textContent = new Intl.DateTimeFormat("es-CL", { month: "long", year: "numeric", timeZone: "UTC" })
      .format(new Date(Date.UTC(year, month, 1)));
    previous.disabled = year === todayDate.getUTCFullYear() && month === todayDate.getUTCMonth();
    grid.replaceChildren();
    for (const label of weekdayLabels) {
      const header = document.createElement("span");
      header.className = "calendar-commitments__weekday";
      header.textContent = label;
      grid.appendChild(header);
    }
    const first = new Date(Date.UTC(year, month, 1));
    const leading = (first.getUTCDay() + 6) % 7;
    const daysInMonth = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
    for (let position = 0; position < leading + daysInMonth; position += 1) {
      if (position < leading) {
        const blank = document.createElement("span");
        blank.setAttribute("aria-hidden", "true");
        grid.appendChild(blank);
        continue;
      }
      const day = position - leading + 1;
      const value = iso(new Date(Date.UTC(year, month, day)));
      const isExisting = existing.has(value);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "calendar-commitments__date";
      button.textContent = String(day);
      button.setAttribute("aria-label", `${dateLabel(value)}: ${isExisting ? "ya registrado" : selected.has(value) ? "seleccionado" : "sin seleccionar"}${kindsOn(value).length ? `; ${kindsOn(value).map((kind) => kindLabels[kind]).join(", ")}` : ""}`);
      button.setAttribute("aria-pressed", selected.has(value) ? "true" : "false");
      button.disabled = value < today || isExisting;
      addCommitmentDots(button, value);
      if (selected.has(value)) button.classList.add("is-selected");
      if (hasPlan(value)) button.classList.add("has-plan");
      button.addEventListener("click", () => {
        if (selected.has(value)) {
          selected.delete(value);
          foodAttachments.delete(value);
          foodPreviews.delete(value);
          notesByDate.delete(value);
        }
        else if (selected.size >= 62) {
          error.textContent = "Puedes elegir hasta 62 fechas por registro.";
          error.hidden = false;
          return;
        } else selected.add(value);
        error.hidden = true;
        render();
        updateSelection();
      });
      grid.appendChild(button);
    }
  }
  function changeMonth(delta) {
    const target = new Date(Date.UTC(year, month + delta, 1));
    year = target.getUTCFullYear();
    month = target.getUTCMonth();
    render();
  }
  previous.addEventListener("click", () => changeMonth(-1));
  next.addEventListener("click", () => changeMonth(1));
  form.addEventListener("submit", (event) => {
    if (!selected.size) { event.preventDefault(); return; }
    inputs.replaceChildren();
    for (const value of [...selected].sort()) {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "dates";
      input.value = value;
      inputs.appendChild(input);
    }
    const attachmentsInput = document.createElement("input");
    attachmentsInput.type = "hidden";
    attachmentsInput.name = "food_attachments";
    attachmentsInput.value = JSON.stringify([...foodAttachments]
      .filter(([day]) => selected.has(day))
      .map(([calendar_date, attachment]) => ({
        calendar_date,
        food_period_start: attachment.start,
        food_period_end: attachment.end,
      })));
    inputs.appendChild(attachmentsInput);
    const notesInput = document.createElement("input");
    notesInput.type = "hidden";
    notesInput.name = "notes_by_date";
    notesInput.value = JSON.stringify([...notesByDate]
      .filter(([day]) => selected.has(day))
      .map(([calendar_date, note]) => ({ calendar_date, note: note.trim() })));
    inputs.appendChild(notesInput);
  });
  if (foodFields) {
    const mainView = document.getElementById("calendar-commitments-main-view");
    const editorView = document.getElementById("calendar-commitments-editor-view");
    const pageTitle = document.getElementById("calendar-commitments-page-title");
    const dateChip = document.getElementById("calendar-commitments-date-chip");
    const registrationTitle = pageTitle.textContent;
    const headerBack = document.getElementById("calendar-commitments-editor-back");
    const dayNote = document.getElementById("calendar-commitments-day-note");
    const foodCalculate = document.getElementById("calendar-commitments-food-calculate");
    const startInput = document.getElementById("calendar-commitments-food-start");
    const endInput = document.getElementById("calendar-commitments-food-end");
    const foodMonthTitle = document.getElementById("calendar-commitments-food-month");
    const foodGrid = document.getElementById("calendar-commitments-food-grid");
    const foodSummaryCount = document.getElementById("calendar-commitments-food-summary-count");
    const foodError = document.getElementById("calendar-commitments-food-error");
    const foodLoading = document.getElementById("calendar-commitments-food-loading");
    const foodCount = document.getElementById("calendar-commitments-food-count");
    const foodList = document.getElementById("calendar-commitments-food-list");
    const quantityFormat = new Intl.NumberFormat("es-CL", { maximumFractionDigits: 1 });
    let activeRequest = null;
    let foodYear = todayDate.getUTCFullYear();
    let foodMonth = todayDate.getUTCMonth();
    let foodPending = false;
    let foodPreviewReady = false;
    let editingDate = null;
    refreshFoodCommitments = (key) => { if (editingDate && monthKey(foodYear, foodMonth) === key) renderFoodRange(); };

    function closeFoodEditor() {
      if (editingDate) notesByDate.set(editingDate, dayNote.value);
      activeRequest?.abort();
      activeRequest = null;
      foodPending = false;
      editingDate = null;
      mainView.hidden = false;
      editorView.hidden = true;
      pageTitle.textContent = registrationTitle;
      dateChip.hidden = true;
      headerBack.hidden = true;
      updateSelection();
      requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: "instant" }));
    }

    openFoodEditor = (day) => {
      editingDate = day;
      const attachment = foodAttachments.get(day);
      startInput.value = attachment?.start ?? "";
      endInput.value = attachment?.end ?? "";
      foodPreviewReady = Boolean(foodPreviews.get(day));
      foodPending = false;
      foodError.hidden = true;
      foodLoading.hidden = true;
      foodYear = Number((attachment?.start ?? day).slice(0, 4));
      foodMonth = Number((attachment?.start ?? day).slice(5, 7)) - 1;
      pageTitle.textContent = dayTitle;
      dateChip.textContent = dateLabel(day);
      dateChip.hidden = false;
      headerBack.hidden = false;
      dayNote.value = notesByDate.get(day) ?? "";
      mainView.hidden = true;
      editorView.hidden = false;
      renderFoodRange();
      if (foodPreviewReady) showFoods(foodPreviews.get(day));
      else {
        foodSummaryCount.hidden = true;
        foodCount.hidden = true;
        foodList.hidden = true;
      }
      requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: "instant" }));
    };

    function renderFoodRange() {
      loadCommitmentMonth(foodYear, foodMonth);
      const start = startInput.value;
      const end = endInput.value;
      foodMonthTitle.textContent = new Intl.DateTimeFormat("es-CL", { month: "long", year: "numeric", timeZone: "UTC" })
        .format(new Date(Date.UTC(foodYear, foodMonth, 1)));
      document.getElementById("calendar-commitments-food-previous").disabled = foodPending;
      document.getElementById("calendar-commitments-food-next").disabled = foodPending;
      foodCalculate.textContent = foodPreviewReady ? "Limpiar selección" : "Calcular lista de alimentos";
      foodCalculate.disabled = foodPending || (!foodPreviewReady && !(start && end));
      foodGrid.replaceChildren();
      for (const label of weekdayLabels) {
        const header = document.createElement("span");
        header.className = "calendar-commitments__weekday";
        header.textContent = label;
        foodGrid.appendChild(header);
      }
      const first = new Date(Date.UTC(foodYear, foodMonth, 1));
      const leading = (first.getUTCDay() + 6) % 7;
      const daysInMonth = new Date(Date.UTC(foodYear, foodMonth + 1, 0)).getUTCDate();
      for (let position = 0; position < leading + daysInMonth; position += 1) {
        if (position < leading) {
          const blank = document.createElement("span");
          blank.setAttribute("aria-hidden", "true");
          foodGrid.appendChild(blank);
          continue;
        }
        const value = iso(new Date(Date.UTC(foodYear, foodMonth, position - leading + 1)));
        const endpoint = value === start || value === end;
        const middle = Boolean(start && end && value > start && value < end);
        const role = value === start && value === end ? "inicio y término" : value === start ? "inicio" : value === end ? "término" : middle ? "dentro del periodo" : "fuera del periodo";
        const button = document.createElement("button");
        button.type = "button";
        button.className = "calendar-commitments__date";
        button.textContent = String(position - leading + 1);
        const shoppingDate = page.dataset.kind === "shopping" && value === editingDate;
        button.setAttribute("aria-label", `${dateLabel(value)}: ${shoppingDate ? "día para hacer compras, " : ""}${role}${kindsOn(value).length ? `; ${kindsOn(value).map((kind) => kindLabels[kind]).join(", ")}` : ""}`);
        button.setAttribute("aria-pressed", endpoint || middle ? "true" : "false");
        button.disabled = foodPending || foodPreviewReady;
        if (endpoint) button.classList.add("is-range-endpoint");
        if (middle) button.classList.add("is-range-middle");
        if (hasPlan(value)) button.classList.add("has-plan");
        addCommitmentDots(button, value, shoppingDate);
        button.addEventListener("click", () => {
          if (!start || end || value < start) {
            startInput.value = value;
            endInput.value = "";
          } else {
            const span = (Date.parse(`${value}T12:00:00Z`) - Date.parse(`${start}T12:00:00Z`)) / 86_400_000;
            if (span >= 366) {
              foodError.textContent = "Elige un periodo de hasta 366 días.";
              foodError.hidden = false;
              return;
            }
            endInput.value = value;
          }
          foodPending = false;
          renderFoodRange();
          foodError.hidden = true;
        });
        foodGrid.appendChild(button);
      }
    }

    function showFoods(result) {
      foodSummaryCount.textContent = `${result.plans_count} ${result.plans_count === 1 ? "plan" : "planes"} y ${result.meals_count} ${result.meals_count === 1 ? "comida programada" : "comidas programadas"} en este periodo.`;
      foodCount.textContent = `${result.foods.length} ${result.foods.length === 1 ? "alimento" : "alimentos"}`;
      foodList.replaceChildren();
      if (!result.foods.length) {
        foodList.textContent = "No hay alimentos programados para este periodo.";
      } else for (const food of result.foods) {
        const row = document.createElement("div");
        row.className = "calendar-commitments__food-row";
        const label = document.createElement("label");
        label.className = "calendar-commitments__food-check";
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        const name = document.createElement("span");
        name.textContent = food.name;
        label.append(checkbox, name);
        const quantity = document.createElement("strong");
        quantity.textContent = `${quantityFormat.format(food.quantity)} ${food.quantity_unit}`;
        row.append(label, quantity);
        foodList.appendChild(row);
      }
      foodSummaryCount.hidden = false;
      foodCount.hidden = false;
      foodList.hidden = false;
    }

    async function refreshFoods() {
      activeRequest?.abort();
      activeRequest = null;
      foodLoading.hidden = true;
      foodError.hidden = true;
      const start = startInput.value;
      const end = endInput.value;
      if (!start || !end) {
        foodPending = false;
        renderFoodRange();
        return;
      }
      const span = (Date.parse(`${end}T12:00:00Z`) - Date.parse(`${start}T12:00:00Z`)) / 86_400_000;
      if (span < 0 || span >= 366) {
        foodError.textContent = "Elige un periodo válido de hasta 366 días.";
        foodError.hidden = false;
        foodPending = false;
        renderFoodRange();
        return;
      }
      const controller = new AbortController();
      activeRequest = controller;
      foodPending = true;
      foodLoading.hidden = false;
      renderFoodRange();
      try {
        const params = new URLSearchParams({ start_date: start, end_date: end });
        const response = await fetch(`${foodFields.dataset.foodsUrl}?${params}`, { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error("No pudimos calcular los alimentos de este periodo.");
        const result = await response.json();
        if (controller.signal.aborted) return;
        foodPending = false;
        foodPreviewReady = true;
        foodAttachments.set(editingDate, { start, end });
        foodPreviews.set(editingDate, result);
        renderFoodRange();
        showFoods(result);
      } catch (error) {
        if (controller.signal.aborted) return;
        foodError.textContent = error.message;
        foodError.hidden = false;
        foodPending = false;
        renderFoodRange();
      } finally {
        if (activeRequest === controller) {
          activeRequest = null;
          foodLoading.hidden = true;
        }
      }
    }
    document.getElementById("calendar-commitments-food-previous").addEventListener("click", () => {
      const target = new Date(Date.UTC(foodYear, foodMonth - 1, 1));
      foodYear = target.getUTCFullYear();
      foodMonth = target.getUTCMonth();
      renderFoodRange();
    });
    document.getElementById("calendar-commitments-food-next").addEventListener("click", () => {
      const target = new Date(Date.UTC(foodYear, foodMonth + 1, 1));
      foodYear = target.getUTCFullYear();
      foodMonth = target.getUTCMonth();
      renderFoodRange();
    });
    document.getElementById("calendar-commitments-editor-back").addEventListener("click", closeFoodEditor);
    foodCalculate.addEventListener("click", () => {
      if (!editingDate || foodPending) return;
      if (foodPreviewReady) {
        foodAttachments.delete(editingDate);
        foodPreviews.delete(editingDate);
        startInput.value = "";
        endInput.value = "";
        foodPreviewReady = false;
        foodSummaryCount.hidden = true;
        foodCount.hidden = true;
        foodList.hidden = true;
        renderFoodRange();
      } else if (startInput.value && endInput.value) void refreshFoods();
    });
    renderFoodRange();
  }
  render();
  updateSelection();
})();
