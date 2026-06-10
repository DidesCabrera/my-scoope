document.addEventListener("DOMContentLoaded", () => {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length !== 2) return "";
    return parts.pop().split(";").shift();
  }

  function getReorderRows(panel) {
    return Array.from(panel.querySelectorAll(".js-list-reorder-row"));
  }

  function moveRowToEnd(panel, row) {
    panel.appendChild(row);
  }

  function getRowAfterPointer(panel, y, draggingRow) {
    const rows = getReorderRows(panel).filter((row) => row !== draggingRow);

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

  function initReorderPanel() {
    const panel = document.querySelector(".js-list-reorder-panel");
    const saveButtons = Array.from(document.querySelectorAll(".js-list-reorder-save"));
    if (!panel || !saveButtons.length) return;

    let draggingRow = null;
    let pointerId = null;
    let startY = 0;
    let hasMoved = false;
    let isDirty = false;

    function setDirtyState(nextDirty) {
      isDirty = nextDirty;
      saveButtons.forEach((button) => {
        button.disabled = false;
        button.dataset.dirty = isDirty ? "true" : "false";
      });
    }

    async function persistOrder() {
      const reorderUrl = panel.dataset.reorderUrl;
      if (!reorderUrl) return false;

      const formData = new FormData();
      getReorderRows(panel).forEach((row) => {
        formData.append("order[]", row.dataset.itemId);
      });

      const response = await fetch(reorderUrl, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: formData,
      });

      return response.ok;
    }

    setDirtyState(false);

    saveButtons.forEach((button) => {
      button.addEventListener("click", async () => {
        const returnUrl = panel.dataset.returnUrl || window.location.pathname;

        if (!isDirty) {
          window.location.href = returnUrl;
          return;
        }

        saveButtons.forEach((btn) => {
          btn.disabled = true;
        });

        const saved = await persistOrder();

        if (saved) {
          window.location.href = returnUrl;
          return;
        }

        setDirtyState(true);
      });
    });

    panel.addEventListener("pointerdown", (event) => {
      const handle = event.target.closest(".list-panel-drag-handle");
      if (!handle) return;

      const row = handle.closest(".js-list-reorder-row");
      if (!row) return;

      draggingRow = row;
      pointerId = event.pointerId;
      startY = event.clientY;
      hasMoved = false;

      handle.setPointerCapture(pointerId);
      draggingRow.classList.add("is-dragging");
      document.body.classList.add("is-list-panel-sorting");

      event.preventDefault();
    });

    panel.addEventListener("pointermove", (event) => {
      if (!draggingRow || event.pointerId !== pointerId) return;

      const deltaY = Math.abs(event.clientY - startY);
      if (deltaY > 3) {
        hasMoved = true;
      }

      const afterElement = getRowAfterPointer(panel, event.clientY, draggingRow);

      if (afterElement == null) {
        moveRowToEnd(panel, draggingRow);
      } else {
        panel.insertBefore(draggingRow, afterElement);
      }

      event.preventDefault();
    });

    panel.addEventListener("pointerup", (event) => {
      if (!draggingRow || event.pointerId !== pointerId) return;

      const finishedRow = draggingRow;
      const handle = finishedRow.querySelector(".list-panel-drag-handle");

      if (handle && handle.hasPointerCapture(pointerId)) {
        handle.releasePointerCapture(pointerId);
      }

      finishedRow.classList.remove("is-dragging");
      document.body.classList.remove("is-list-panel-sorting");

      draggingRow = null;
      pointerId = null;

      if (hasMoved) {
        setDirtyState(true);
      }
    });

    panel.addEventListener("pointercancel", () => {
      if (draggingRow) {
        draggingRow.classList.remove("is-dragging");
      }

      document.body.classList.remove("is-list-panel-sorting");
      draggingRow = null;
      pointerId = null;
      hasMoved = false;
    });
  }

  function initDeletePanel() {
    const panel = document.querySelector(".js-list-delete-panel");
    const checkboxes = Array.from(document.querySelectorAll(".js-list-delete-checkbox"));
    const bulkButtons = Array.from(document.querySelectorAll(".js-list-bulk-delete-submit"));
    const bulkForms = bulkButtons
      .map((button) => button.closest("form"))
      .filter(Boolean);

    if (!panel || !checkboxes.length || !bulkButtons.length) return;

    function selectedIds() {
      return checkboxes
        .filter((checkbox) => checkbox.checked)
        .map((checkbox) => checkbox.value);
    }

    function syncState() {
      const hasSelection = selectedIds().length > 0;
      bulkButtons.forEach((button) => {
        button.disabled = !hasSelection;
      });
    }

    checkboxes.forEach((checkbox) => {
      checkbox.addEventListener("change", syncState);
    });

    bulkForms.forEach((form) => {
      form.addEventListener("submit", () => {
        form.querySelectorAll('input[name="selected_ids[]"]').forEach((input) => {
          input.remove();
        });

        selectedIds().forEach((id) => {
          const input = document.createElement("input");
          input.type = "hidden";
          input.name = "selected_ids[]";
          input.value = id;
          form.appendChild(input);
        });
      });
    });

    syncState();
  }

  initReorderPanel();
  initDeletePanel();
});
