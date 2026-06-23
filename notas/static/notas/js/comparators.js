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

  document.querySelectorAll("[data-comparator-selector]").forEach(setupSelector);
})();
