document.addEventListener("DOMContentLoaded", () => {
  const toggles = document.querySelectorAll(".js-picker-toggle");
  let openModal = null;
  let restoreFocusTo = null;

  function isModal(section) {
    return section?.matches("dialog[data-picker-modal]");
  }

  function getToggle(sectionId) {
    return document.querySelector(
      `.js-picker-toggle[aria-controls="${sectionId}"]`
    );
  }

  function setStep(section, step) {
    if (!isModal(section)) return;

    const nextStep = step === "impact" ? "impact" : "selection";
    section.dataset.pickerStep = nextStep;

    section.querySelectorAll("[data-picker-step-panel]").forEach(panel => {
      panel.hidden = panel.dataset.pickerStepPanel !== nextStep;
    });

    section.querySelectorAll("[data-picker-step-indicator]").forEach(indicator => {
      const isCurrent = indicator.dataset.pickerStepIndicator === nextStep;
      if (isCurrent) {
        indicator.setAttribute("aria-current", "step");
      } else {
        indicator.removeAttribute("aria-current");
      }
    });

    window.requestAnimationFrame(() => {
      const focusTarget = nextStep === "selection"
        ? section.querySelector('input[type="search"]')
        : section.querySelector("#food-quantity, input[name='hour']");
      focusTarget?.focus({ preventScroll: true });
    });
  }

  function syncPageLock() {
    const hasOpenPicker = Boolean(document.querySelector("dialog[data-picker-modal][open]"));
    document.documentElement.classList.toggle("has-picker-modal-open", hasOpenPicker);
  }

  function showSection(toggle, section, step = "selection") {
    if (!section) return;

    if (!isModal(section)) {
      section.classList.remove("is-collapsed");
      toggle?.setAttribute("aria-expanded", "true");
      return;
    }

    if (openModal && openModal !== section && openModal.open) {
      openModal.close();
    }

    restoreFocusTo = toggle || document.activeElement;
    setStep(section, step);

    if (!section.open) {
      section.showModal();
    }

    openModal = section;
    toggle?.setAttribute("aria-expanded", "true");
    syncPageLock();
  }

  function hideSection(toggle, section) {
    if (!section) return;

    if (!isModal(section)) {
      section.classList.add("is-collapsed");
      toggle?.setAttribute("aria-expanded", "false");
      return;
    }

    if (section.open) {
      section.close();
    }

    toggle?.setAttribute("aria-expanded", "false");
    if (openModal === section) openModal = null;
    syncPageLock();

    const focusTarget = restoreFocusTo;
    restoreFocusTo = null;
    focusTarget?.focus?.({ preventScroll: true });
  }

  function requestDismiss(section) {
    if (!section) return;

    const dismissEvent = new CustomEvent("picker:dismiss", {
      bubbles: true,
      cancelable: true,
      detail: { sectionId: section.id },
    });

    section.dispatchEvent(dismissEvent);

    if (!dismissEvent.defaultPrevented) {
      hideSection(getToggle(section.id), section);
    }
  }

  toggles.forEach(toggle => {
    const targetId = toggle.getAttribute("aria-controls");
    const section = targetId ? document.getElementById(targetId) : null;

    if (!section) return;

    if (isModal(section)) {
      toggle.setAttribute("aria-expanded", section.open ? "true" : "false");
      toggle.addEventListener("click", () => showSection(toggle, section, "selection"));
      return;
    }

    const shouldStartExpanded =
      toggle.getAttribute("aria-expanded") === "true" ||
      !section.classList.contains("is-collapsed");

    if (shouldStartExpanded) {
      showSection(toggle, section);
    } else {
      hideSection(toggle, section);
    }

    toggle.addEventListener("click", () => {
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      if (expanded) hideSection(toggle, section);
      else showSection(toggle, section);
    });

    toggle.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        toggle.click();
      }
    });
  });

  document.querySelectorAll("dialog[data-picker-modal]").forEach(section => {
    section.addEventListener("cancel", event => {
      event.preventDefault();
      requestDismiss(section);
    });

    section.addEventListener("click", event => {
      if (event.target === section) requestDismiss(section);
    });

    section.addEventListener("close", () => {
      const toggle = getToggle(section.id);
      toggle?.setAttribute("aria-expanded", "false");
      if (openModal === section) openModal = null;
      syncPageLock();
    });

    section.querySelectorAll("[data-picker-dismiss]").forEach(button => {
      button.addEventListener("click", event => {
        if (event.defaultPrevented) return;
        requestDismiss(section);
      });
    });

    section.querySelectorAll("[data-picker-go-to]").forEach(button => {
      button.addEventListener("click", () => {
        setStep(section, button.dataset.pickerGoTo);
      });
    });
  });

  document.addEventListener("picker:open", event => {
    const sectionId = event.detail?.sectionId;
    if (!sectionId) return;

    const section = document.getElementById(sectionId);
    showSection(getToggle(sectionId), section, event.detail?.step);
  });

  document.addEventListener("picker:step", event => {
    const sectionId = event.detail?.sectionId;
    if (!sectionId) return;

    setStep(document.getElementById(sectionId), event.detail?.step);
  });

  document.addEventListener("picker:close", event => {
    const sectionId = event.detail?.sectionId;
    if (!sectionId) return;

    hideSection(getToggle(sectionId), document.getElementById(sectionId));
  });
});
