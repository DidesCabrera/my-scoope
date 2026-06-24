(function () {
  function setupSelector(selector) {
    const select = selector.querySelector("[data-comparator-select]");
    const quantity = selector.querySelector("[data-comparator-quantity]");

    if (!select || !quantity) {
      return;
    }

    function syncQuantityVisibility() {
      quantity.classList.toggle("is-hidden", !select.value);
    }

    select.addEventListener("change", syncQuantityVisibility);
    syncQuantityVisibility();
  }

  function comparableFormState(form) {
    const fields = Array.from(form.querySelectorAll("select[name^='item_'], input[name^='qty_']"));

    return fields
      .map(function (field) {
        return field.name + "=" + field.value;
      })
      .join("&");
  }

  function syncRemoveButtons(form) {
    const selectors = Array.from(form.querySelectorAll("[data-comparator-selector]"));
    const canRemove = selectors.length > 2 && !form.classList.contains("is-read-mode");

    selectors.forEach(function (selector) {
      const removeButton = selector.querySelector("[data-comparator-remove]");

      if (!removeButton) {
        return;
      }

      removeButton.classList.toggle("is-hidden", !canRemove);
      removeButton.disabled = !canRemove;
    });
  }

  function setupSaveChanges(form) {
    const saveChangesButton = form.querySelector("[data-comparator-save-changes]");

    if (!saveChangesButton) {
      return;
    }

    const initialState = comparableFormState(form);

    function syncSaveChangesState() {
      if (comparableFormState(form) !== initialState) {
        saveChangesButton.disabled = false;
      }
    }

    form.addEventListener("change", syncSaveChangesState);
    form.addEventListener("input", syncSaveChangesState);
  }

  function setupSavedDetailEditMode(form) {
    const editButton = form.querySelector("[data-comparator-edit-toggle]");
    let editModeInput = form.querySelector("[data-comparator-edit-mode-input]");

    if (!editButton) {
      return;
    }

    function ensureEditModeInput() {
      if (!editModeInput) {
        editModeInput = document.createElement("input");
        editModeInput.type = "hidden";
        editModeInput.name = "edit";
        editModeInput.setAttribute("data-comparator-edit-mode-input", "");
        form.appendChild(editModeInput);
      }

      editModeInput.value = "1";
    }

    editButton.addEventListener("click", function () {
      form.classList.remove("is-read-mode");
      ensureEditModeInput();
      syncRemoveButtons(form);

      const firstField = form.querySelector("select, input:not([type='hidden'])");
      if (firstField) {
        firstField.focus({ preventScroll: true });
      }
    });
  }

  document.querySelectorAll("[data-comparator-selector]").forEach(setupSelector);
  document.querySelectorAll("[data-comparator-form]").forEach(function (form) {
    setupSaveChanges(form);
    syncRemoveButtons(form);
  });
  document.querySelectorAll("[data-comparator-saved-detail-form]").forEach(setupSavedDetailEditMode);
})();
