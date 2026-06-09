document.addEventListener("DOMContentLoaded", () => {
    const grids = Array.from(document.querySelectorAll(".js-mealfood-sortable"));
  
    function getCookie(name) {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length !== 2) return "";
      return parts.pop().split(";").shift();
    }
  
    function getRows(grid) {
      return Array.from(grid.querySelectorAll(".js-mealfood-sortable-row"));
    }

    function getActions(grid) {
      return grid.querySelector(".js-sortable-actions");
    }

    function getStatus(grid) {
      return grid.querySelector(".js-sortable-status");
    }

    function getSaveButton(grid) {
      return grid.querySelector(".js-mealfood-sortable-save");
    }

    function getCancelButton(grid) {
      return grid.querySelector(".js-mealfood-sortable-cancel");
    }

    function setEditPanelUrl() {
      const url = new URL(window.location.href);
      url.searchParams.set("panel", "edit");
      return url.toString();
    }

    function reloadEditPanel() {
      window.location.href = setEditPanelUrl();
    }

    function setDirtyState(grid, isDirty) {
      const actions = getActions(grid);
      const saveButton = getSaveButton(grid);
      const cancelButton = getCancelButton(grid);
      const status = getStatus(grid);

      if (actions) {
        actions.dataset.state = isDirty ? "dirty" : "clean";
      }

      if (saveButton) {
        saveButton.disabled = !isDirty;
      }

      if (cancelButton) {
        cancelButton.disabled = !isDirty;
      }

      if (status) {
        status.textContent = isDirty
          ? "Orden modificado. Guarda para aplicar los cambios."
          : "Arrastra los alimentos para definir el orden.";
      }
    }
  

    function moveRowToEnd(grid, row) {
      const actions = getActions(grid);

      if (actions) {
        grid.insertBefore(row, actions);
        return;
      }

      grid.appendChild(row);
    }

    function getRowAfterPointer(grid, y, draggingRow) {
      const rows = getRows(grid).filter((row) => row !== draggingRow);
  
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
  
    async function persistOrder(grid) {
      const reorderUrl = grid.dataset.reorderUrl;
      if (!reorderUrl) return false;
  
      const formData = new FormData();
  
      getRows(grid).forEach((row) => {
        formData.append("mealfood_order[]", row.dataset.mealfoodId);
      });
  
      const response = await fetch(reorderUrl, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: formData,
      });
  
      if (!response.ok) {
        console.error("No se pudo guardar el nuevo orden de alimentos.");
        return false;
      }

      return true;
    }
  
    grids.forEach((grid) => {
      let draggingRow = null;
      let pointerId = null;
      let startY = 0;
      let hasMoved = false;

      setDirtyState(grid, false);

      const saveButton = getSaveButton(grid);
      const cancelButton = getCancelButton(grid);

      if (saveButton) {
        saveButton.addEventListener("click", async () => {
          if (saveButton.disabled) return;

          saveButton.disabled = true;
          const status = getStatus(grid);

          if (status) {
            status.textContent = "Guardando orden...";
          }

          const saved = await persistOrder(grid);

          if (saved) {
            reloadEditPanel();
            return;
          }

          saveButton.disabled = false;

          if (status) {
            status.textContent = "No se pudo guardar. Intenta nuevamente.";
          }
        });
      }

      if (cancelButton) {
        cancelButton.addEventListener("click", () => {
          if (cancelButton.disabled) return;
          reloadEditPanel();
        });
      }
  
      grid.addEventListener("pointerdown", (event) => {
        const handle = event.target.closest(".mealfood-drag-handle");
        if (!handle) return;
  
        const row = handle.closest(".js-mealfood-sortable-row");
        if (!row) return;
  
        draggingRow = row;
        pointerId = event.pointerId;
        startY = event.clientY;
        hasMoved = false;
  
        handle.setPointerCapture(pointerId);
  
        draggingRow.classList.add("is-dragging");
        document.body.classList.add("is-mealfood-sorting");
  
        event.preventDefault();
      });
  
      grid.addEventListener("pointermove", (event) => {
        if (!draggingRow || event.pointerId !== pointerId) return;
  
        const deltaY = Math.abs(event.clientY - startY);
        if (deltaY > 3) {
          hasMoved = true;
        }
  
        const afterElement = getRowAfterPointer(grid, event.clientY, draggingRow);
  
        if (afterElement == null) {
          moveRowToEnd(grid, draggingRow);
        } else {
          grid.insertBefore(draggingRow, afterElement);
        }
  
        event.preventDefault();
      });
  
      grid.addEventListener("pointerup", (event) => {
        if (!draggingRow || event.pointerId !== pointerId) return;
  
        const finishedRow = draggingRow;
        const handle = finishedRow.querySelector(".mealfood-drag-handle");
  
        if (handle && handle.hasPointerCapture(pointerId)) {
          handle.releasePointerCapture(pointerId);
        }
  
        finishedRow.classList.remove("is-dragging");
        document.body.classList.remove("is-mealfood-sorting");
  
        draggingRow = null;
        pointerId = null;
  
        if (hasMoved) {
          setDirtyState(grid, true);
        }
      });
  
      grid.addEventListener("pointercancel", (event) => {
        if (!draggingRow || event.pointerId !== pointerId) return;
  
        draggingRow.classList.remove("is-dragging");
        document.body.classList.remove("is-mealfood-sorting");
  
        draggingRow = null;
        pointerId = null;
        hasMoved = false;
      });
    });
  });
