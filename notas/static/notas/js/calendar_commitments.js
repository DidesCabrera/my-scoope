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
  const weekdayLabels = ["L", "M", "M", "J", "V", "S", "D"];
  const todayDate = new Date(`${today}T12:00:00Z`);
  let year = todayDate.getUTCFullYear();
  let month = todayDate.getUTCMonth();
  let foodPeriodReady = true;

  function iso(date) { return date.toISOString().slice(0, 10); }
  function dateLabel(value) {
    return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
      .format(new Date(`${value}T12:00:00Z`));
  }
  function updateSelection() {
    const dates = [...selected].sort();
    count.textContent = String(dates.length);
    submit.disabled = dates.length === 0 || !foodPeriodReady;
    summary.replaceChildren();
    if (!dates.length) {
      summary.textContent = "Toca las fechas del calendario para seleccionarlas.";
      return;
    }
    for (const value of dates) {
      const chip = document.createElement("span");
      chip.textContent = dateLabel(value);
      summary.appendChild(chip);
    }
  }
  function render() {
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
      button.setAttribute("aria-label", `${dateLabel(value)}: ${isExisting ? "ya registrado" : selected.has(value) ? "seleccionado" : "sin seleccionar"}`);
      button.setAttribute("aria-pressed", selected.has(value) ? "true" : "false");
      button.disabled = value < today || isExisting;
      if (isExisting) button.classList.add("is-existing");
      if (selected.has(value)) button.classList.add("is-selected");
      button.addEventListener("click", () => {
        if (selected.has(value)) selected.delete(value);
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
    if (!selected.size || !foodPeriodReady) { event.preventDefault(); return; }
    inputs.replaceChildren();
    for (const value of [...selected].sort()) {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "dates";
      input.value = value;
      inputs.appendChild(input);
    }
  });
  const foodFields = document.querySelector("[data-foods-url]");
  if (foodFields) {
    const startInput = document.getElementById("calendar-commitments-food-start");
    const endInput = document.getElementById("calendar-commitments-food-end");
    const foodError = document.getElementById("calendar-commitments-food-error");
    const foodLoading = document.getElementById("calendar-commitments-food-loading");
    const foodCard = document.getElementById("calendar-commitments-food-card");
    const foodCount = document.getElementById("calendar-commitments-food-count");
    const foodList = document.getElementById("calendar-commitments-food-list");
    const quantityFormat = new Intl.NumberFormat("es-CL", { maximumFractionDigits: 1 });
    let activeRequest = null;

    async function refreshFoods() {
      activeRequest?.abort();
      activeRequest = null;
      foodCard.hidden = true;
      foodLoading.hidden = true;
      foodError.hidden = true;
      const start = startInput.value;
      const end = endInput.value;
      foodPeriodReady = !start && !end;
      updateSelection();
      if (!start && !end) return;
      if (!start || !end) {
        foodError.textContent = "Elige ambas fechas del periodo o deja ambas vacías.";
        foodError.hidden = false;
        return;
      }
      const span = (Date.parse(`${end}T12:00:00Z`) - Date.parse(`${start}T12:00:00Z`)) / 86_400_000;
      if (span < 0 || span >= 366) {
        foodError.textContent = "Elige un periodo válido de hasta 366 días.";
        foodError.hidden = false;
        return;
      }
      const controller = new AbortController();
      activeRequest = controller;
      foodLoading.hidden = false;
      try {
        const params = new URLSearchParams({ start_date: start, end_date: end });
        const response = await fetch(`${foodFields.dataset.foodsUrl}?${params}`, { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error("No pudimos calcular los alimentos de este periodo.");
        const result = await response.json();
        if (controller.signal.aborted) return;
        foodCount.textContent = `${result.plans_count} ${result.plans_count === 1 ? "plan programado" : "planes programados"} · ${result.foods.length} ${result.foods.length === 1 ? "alimento" : "alimentos"}`;
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
        foodCard.hidden = false;
        foodPeriodReady = true;
        updateSelection();
      } catch (error) {
        if (controller.signal.aborted) return;
        foodError.textContent = error.message;
        foodError.hidden = false;
      } finally {
        if (activeRequest === controller) {
          activeRequest = null;
          foodLoading.hidden = true;
        }
      }
    }
    startInput.addEventListener("change", refreshFoods);
    endInput.addEventListener("change", refreshFoods);
  }
  render();
  updateSelection();
})();
