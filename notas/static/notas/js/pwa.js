(function () {
  const root = document.documentElement;
  const isStandalone = window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;
  const navigationPlaceholderClasses = [
    "pwa-navigation-placeholder--list",
    "pwa-navigation-placeholder--detail",
    "pwa-navigation-placeholder--home",
    "pwa-navigation-placeholder--profile",
    "pwa-navigation-placeholder--form",
  ];

  root.classList.toggle("pwa-standalone", isStandalone);

  function rememberInternalNavigation() {
    try {
      sessionStorage.setItem("myscoope.pwa.internalNavigation", "1");
    } catch (error) {
      // The placeholder should still be shown even if storage is unavailable.
    }
  }

  function markPwaReady() {
    root.classList.add("pwa-ready");
  }

  function getInternalUrlFromAnchor(anchor) {
    if (!anchor || !anchor.href) {
      return null;
    }

    if (anchor.target && anchor.target !== "_self") {
      return null;
    }

    if (anchor.hasAttribute("download")) {
      return null;
    }

    const url = new URL(anchor.href, window.location.href);
    const current = new URL(window.location.href);

    if (url.origin !== current.origin) {
      return null;
    }

    if (url.pathname === current.pathname && url.search === current.search) {
      return null;
    }

    if (!url.pathname.startsWith("/app/")) {
      return null;
    }

    return url;
  }

  function getPlaceholderVariant(url) {
    const path = url.pathname.replace(/\/+$/, "");

    if (path === "/app") {
      return "home";
    }

    if (path.startsWith("/app/profile") || path.startsWith("/app/authors")) {
      return "profile";
    }

    const formPathPattern = /\/(create|rename|configure|edit|import)$/;

    if (formPathPattern.test(path)) {
      return "form";
    }

    const listPaths = new Set([
      "/app/dailyplans",
      "/app/dailyplans/explore",
      "/app/dailyplans/draft",
      "/app/meals",
      "/app/meals/explore",
      "/app/meals/draft",
      "/app/foods",
      "/app/proposals",
      "/app/inbox",
      "/app/ai-tools",
    ]);

    if (listPaths.has(path)) {
      return "list";
    }

    return "detail";
  }

  function showNavigationPlaceholder(variant) {
    rememberInternalNavigation();

    navigationPlaceholderClasses.forEach(function (className) {
      root.classList.remove(className);
    });

    root.classList.add("pwa-is-navigating");
    root.classList.add("pwa-navigation-placeholder--" + variant);
  }

  function resetNavigationPlaceholder() {
    root.classList.remove("pwa-is-navigating");
    root.classList.remove("pwa-internal-navigation-boot");
    navigationPlaceholderClasses.forEach(function (className) {
      root.classList.remove(className);
    });

    try {
      sessionStorage.removeItem("myscoope.pwa.internalNavigation");
    } catch (error) {
      // No-op.
    }
  }

  function setupNavigationPlaceholders() {
    if (!isStandalone) {
      return;
    }

    document.addEventListener("click", function (event) {
      if (event.defaultPrevented) {
        return;
      }

      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }

      const anchor = event.target.closest("a[href]");
      const url = getInternalUrlFromAnchor(anchor);

      if (!url) {
        return;
      }

      event.preventDefault();
      showNavigationPlaceholder(getPlaceholderVariant(url));

      const navigate = function () {
        window.location.assign(url.href);
      };

      if (window.requestAnimationFrame) {
        window.requestAnimationFrame(function () {
          window.setTimeout(navigate, 45);
        });
      } else {
        window.setTimeout(navigate, 45);
      }
    }, true);

    window.addEventListener("pageshow", resetNavigationPlaceholder);
  }

  if (document.readyState === "complete") {
    markPwaReady();
  } else {
    window.addEventListener("load", markPwaReady, { once: true });
  }

  setupNavigationPlaceholders();

  if (!("serviceWorker" in navigator)) {
    return;
  }

  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/app/service-worker.js", { scope: "/app/" })
      .catch(function (error) {
        console.warn("MyScoope PWA service worker registration failed:", error);
      });
  });
})();
