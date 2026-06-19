document.addEventListener("DOMContentLoaded", () => {
  const panel = document.querySelector(".js-program-week-reorder-panel");
  if (!panel) return;

  const saveButton = panel.querySelector(".js-program-week-reorder-save");
  const cancelButton = panel.querySelector(".js-program-week-reorder-cancel");
  const actions = panel.querySelector(".js-program-week-reorder-actions");
  let initialOrder = getRows().map((row) => row.dataset.weekNumber);
  let draggingRow = null;
  let pointerId = null;
  let startY = 0;
  let hasMoved = false;
  let isDirty = false;

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length !== 2) return "";
    return parts.pop().split(";").shift();
  }

  function getRows() {
    return Array.from(panel.querySelectorAll(".js-program-week-reorder-row"));
  }

  function getRowAfterPointer(y, dragging) {
    const rows = getRows().filter((row) => row !== dragging);
    return rows.reduce(
      (closest, row) => {
        const box = row.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
          return { offset, element: row };
        }
        return closest;
      },
      { offset: Number.NEGATIVE_INFINITY, element: null }
    ).element;
  }

  function setDirty(nextDirty) {
    isDirty = nextDirty;
    if (actions) actions.dataset.state = isDirty ? "dirty" : "clean";
    [saveButton, cancelButton].forEach((button) => {
      if (button) button.disabled = !isDirty;
    });
  }

  function restoreInitialOrder() {
    const rowsByWeek = new Map(getRows().map((row) => [row.dataset.weekNumber, row]));
    initialOrder.forEach((weekNumber) => {
      const row = rowsByWeek.get(weekNumber);
      if (row) panel.insertBefore(row, actions || null);
    });
    setDirty(false);
  }

  async function persistOrder() {
    const reorderUrl = panel.dataset.reorderUrl;
    if (!reorderUrl) return false;

    const formData = new FormData();
    getRows().forEach((row) => formData.append("order[]", row.dataset.weekNumber));

    const response = await fetch(reorderUrl, {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") },
      body: formData,
    });

    return response.ok;
  }

  if (cancelButton) {
    cancelButton.addEventListener("click", restoreInitialOrder);
  }

  if (saveButton) {
    saveButton.addEventListener("click", async () => {
      saveButton.disabled = true;
      if (cancelButton) cancelButton.disabled = true;

      const saved = await persistOrder();
      if (saved) {
        const returnUrl = panel.dataset.returnUrl || `${window.location.pathname}#program-weeks-panel`;
        const nextUrl = new URL(returnUrl, window.location.href);
        nextUrl.searchParams.set("_week_order", String(Date.now()));
        window.location.href = nextUrl.toString();
        return;
      }

      setDirty(true);
    });
  }

  panel.addEventListener("pointerdown", (event) => {
    const handle = event.target.closest(".program-week-drag-handle");
    if (!handle) return;

    const row = handle.closest(".js-program-week-reorder-row");
    if (!row) return;

    draggingRow = row;
    pointerId = event.pointerId;
    startY = event.clientY;
    hasMoved = false;

    handle.setPointerCapture(pointerId);
    draggingRow.classList.add("is-dragging");
    document.body.classList.add("is-program-week-sorting");
    event.preventDefault();
  });

  panel.addEventListener("pointermove", (event) => {
    if (!draggingRow || event.pointerId !== pointerId) return;

    if (Math.abs(event.clientY - startY) > 3) {
      hasMoved = true;
    }

    const afterElement = getRowAfterPointer(event.clientY, draggingRow);
    panel.insertBefore(draggingRow, afterElement || actions || null);
    event.preventDefault();
  });

  function stopDragging(event) {
    if (!draggingRow) return;
    const handle = draggingRow.querySelector(".program-week-drag-handle");
    if (event && handle && pointerId !== null && handle.hasPointerCapture(pointerId)) {
      handle.releasePointerCapture(pointerId);
    }

    draggingRow.classList.remove("is-dragging");
    document.body.classList.remove("is-program-week-sorting");
    draggingRow = null;
    pointerId = null;

    if (hasMoved) setDirty(true);
    hasMoved = false;
  }

  panel.addEventListener("pointerup", stopDragging);
  panel.addEventListener("pointercancel", stopDragging);
});
