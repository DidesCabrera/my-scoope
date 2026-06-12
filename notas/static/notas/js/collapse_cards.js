(function () {
  if (window.__myscoopeCollapseCardsInitialized) {
    return;
  }

  window.__myscoopeCollapseCardsInitialized = true;

  function bootCollapseCards() {
    const FADE_OUT_DURATION = 100;
    const FADE_IN_DURATION = 180;
    const MOBILE_BREAKPOINT = 980;
    const PANEL_PAGE_SELECTOR = ".page--detail.has-collapsible-panels";

    const TAB_SELECTOR = [
      ".card-detail-tabs--desktop [data-target]",
      ".card-detail-tabs-mobile [data-target]",
    ].join(", ");

    function isMobileViewport() {
      return window.innerWidth <= MOBILE_BREAKPOINT;
    }

    function getButtonKey(button) {
      return button.dataset.target || null;
    }

    function getButtons(detailBlock) {
      return Array.from(detailBlock.querySelectorAll(TAB_SELECTOR));
    }

    function getButtonsForViewport(detailBlock) {
      if (isMobileViewport()) {
        return Array.from(
          detailBlock.querySelectorAll(".card-detail-tabs-mobile [data-target]")
        );
      }

      return Array.from(
        detailBlock.querySelectorAll(".card-detail-tabs--desktop [data-target]")
      );
    }

    function getPanels(detailBlock) {
      const selectors = getButtons(detailBlock)
        .map((button) => button.dataset.target)
        .filter(Boolean);

      const uniqueSelectors = [...new Set(selectors)];

      return uniqueSelectors
        .map((selector) => detailBlock.querySelector(selector))
        .filter(Boolean);
    }

    function getVisiblePanel(detailBlock) {
      return getPanels(detailBlock).find((panel) =>
        panel.classList.contains("is-visible")
      );
    }

    function resetPanel(panel) {
      panel.classList.remove("is-visible", "is-fading-in", "is-fading-out");
    }

    function hideImmediately(panel) {
      resetPanel(panel);
      panel.style.display = "none";
      panel.style.opacity = "0";
    }

    function showPanel(panel) {
      resetPanel(panel);
      panel.style.display = "block";
      panel.style.opacity = "0";

      requestAnimationFrame(() => {
        panel.classList.add("is-visible", "is-fading-in");
        panel.style.opacity = "1";
      });

      window.setTimeout(() => {
        panel.classList.remove("is-fading-in");
      }, FADE_IN_DURATION);
    }

    function hidePanel(panel, callback) {
      if (!panel) {
        if (callback) callback();
        return;
      }

      resetPanel(panel);
      panel.classList.add("is-visible", "is-fading-out");
      panel.style.display = "block";
      panel.style.opacity = "1";

      requestAnimationFrame(() => {
        panel.style.opacity = "0";
      });

      window.setTimeout(() => {
        hideImmediately(panel);
        if (callback) callback();
      }, FADE_OUT_DURATION);
    }

    function syncButtons(detailBlock, activeKey) {
      getButtons(detailBlock).forEach((button) => {
        button.classList.toggle("is-active", getButtonKey(button) === activeKey);
      });
    }

    function activatePanel(detailBlock, selector) {
      if (!detailBlock || !selector) return;
      if (detailBlock.dataset.switching === "true") return;

      const nextPanel = detailBlock.querySelector(selector);
      if (!nextPanel) return;

      const currentPanel = getVisiblePanel(detailBlock);

      if (currentPanel === nextPanel) {
        syncButtons(detailBlock, null);
        detailBlock.dataset.switching = "true";

        hidePanel(currentPanel, () => {
          detailBlock.dataset.switching = "false";
        });
        return;
      }

      syncButtons(detailBlock, selector);
      detailBlock.dataset.switching = "true";

      hidePanel(currentPanel, () => {
        showPanel(nextPanel);

        window.setTimeout(() => {
          detailBlock.dataset.switching = "false";
        }, FADE_IN_DURATION);
      });
    }

    function getRequestedSelector(detailBlock) {
      const params = new URLSearchParams(window.location.search);
      const requestedPanel = params.get("panel");

      if (!requestedPanel) return null;

      const buttons = getButtonsForViewport(detailBlock);

      if (requestedPanel === "edit") {
        const editButton = buttons.find((btn) =>
          (btn.dataset.target || "").includes("edit")
        );
        return editButton ? editButton.dataset.target : null;
      }

      if (requestedPanel === "nutrition") {
        const nutritionButton = buttons.find((btn) => {
          const target = btn.dataset.target || "";
          return target.includes("grid-foods") || target.includes("grid-meals");
        });

        return nutritionButton ? nutritionButton.dataset.target : null;
      }

      if (requestedPanel === "menu") {
        const menuButton = buttons.find((btn) =>
          (btn.dataset.target || "").includes("menu")
        );

        return menuButton ? menuButton.dataset.target : null;
      }

      return null;
    }

    function getConfiguredDefaultSelector(detailBlock) {
      if (isMobileViewport()) {
        return detailBlock.dataset.defaultMobile || null;
      }

      return detailBlock.dataset.defaultDesktop || null;
    }

    function getDefaultKey(detailBlock) {
      const viewportButtons = getButtonsForViewport(detailBlock);
      if (!viewportButtons.length) return null;

      const requestedSelector = getRequestedSelector(detailBlock);
      if (requestedSelector) return requestedSelector;

      const configuredDefaultSelector = getConfiguredDefaultSelector(detailBlock);
      const configuredDefaultButton = configuredDefaultSelector
        ? viewportButtons.find(
            (button) => button.dataset.target === configuredDefaultSelector
          )
        : null;

      if (configuredDefaultButton) {
        return getButtonKey(configuredDefaultButton);
      }

      const activeButton = viewportButtons.find((button) =>
        button.classList.contains("is-active")
      );

      return activeButton ? getButtonKey(activeButton) : null;
    }

    function initDetailBlock(detailBlock) {
      const buttons = getButtons(detailBlock);
      if (!buttons.length) return;

      getPanels(detailBlock).forEach((panel) => {
        hideImmediately(panel);
      });

      const defaultKey = getDefaultKey(detailBlock);

      if (!defaultKey) {
        syncButtons(detailBlock, null);
        detailBlock.dataset.switching = "false";
        return;
      }

      syncButtons(detailBlock, defaultKey);

      const defaultPanel = detailBlock.querySelector(defaultKey);

      if (defaultPanel) {
        defaultPanel.style.display = "block";
        defaultPanel.style.opacity = "1";
        defaultPanel.classList.add("is-visible");
      }

      detailBlock.dataset.switching = "false";
    }

    function getDetailBlocks() {
      return Array.from(document.querySelectorAll(".card-detail-block"));
    }

    function getPanelPages() {
      return Array.from(document.querySelectorAll(PANEL_PAGE_SELECTOR));
    }

    function markPanelPagesReady() {
      getPanelPages().forEach((page) => {
        page.classList.add("is-panels-ready");
      });
    }

    function reinitAllDetailBlocks() {
      getDetailBlocks().forEach((detailBlock) => {
        initDetailBlock(detailBlock);
      });

      markPanelPagesReady();
    }

    reinitAllDetailBlocks();

    document.addEventListener("click", function (event) {
      const button = event.target.closest(TAB_SELECTOR);
      if (!button) return;

      const detailBlock = button.closest(".card-detail-block");
      if (!detailBlock) return;

      activatePanel(detailBlock, button.dataset.target);
    });

    let lastIsMobile = isMobileViewport();

    window.addEventListener("resize", function () {
      const currentIsMobile = isMobileViewport();
      if (currentIsMobile === lastIsMobile) return;

      lastIsMobile = currentIsMobile;
      reinitAllDetailBlocks();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootCollapseCards);
  } else {
    bootCollapseCards();
  }
})();