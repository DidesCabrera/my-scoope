(function () {
  const root = document.documentElement;
  const isStandalone = window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;
  const navigationPlaceholderClasses = [
    "pwa-navigation-placeholder--dailyplan-list",
    "pwa-navigation-placeholder--dailyplan-detail",
    "pwa-navigation-placeholder--meal-list",
    "pwa-navigation-placeholder--meal-detail",
    "pwa-navigation-placeholder--food-list",
    "pwa-navigation-placeholder--food-detail",
    "pwa-navigation-placeholder--proposal-list",
    "pwa-navigation-placeholder--proposal-detail",
    "pwa-navigation-placeholder--profile",
    "pwa-navigation-placeholder--home",
    "pwa-navigation-placeholder--generic",
  ];

  root.classList.toggle("pwa-standalone", isStandalone);

  function rememberLaunchSplashSeen() {
    try {
      sessionStorage.setItem("myscoope.pwa.launchSplashSeen", "1");
      sessionStorage.removeItem("myscoope.pwa.internalNavigation");
    } catch (error) {
      // sessionStorage can be unavailable in private/restricted contexts.
    }
  }

  function rememberInternalNavigation() {
    try {
      sessionStorage.setItem("myscoope.pwa.internalNavigation", "1");
    } catch (error) {
      // The placeholder should still be shown even if storage is unavailable.
    }
  }

  function markPwaReady() {
    root.classList.add("pwa-ready");
    rememberLaunchSplashSeen();

    const splash = document.querySelector(".js-pwa-splash");
    if (!splash) {
      return;
    }

    window.setTimeout(function () {
      splash.remove();
      root.classList.remove("pwa-splash-enabled");
    }, 280);
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

    if (path === "/app/dailyplans") {
      return "dailyplan-list";
    }

    if (path.startsWith("/app/dailyplans/")) {
      return "dailyplan-detail";
    }

    if (path === "/app/meals") {
      return "meal-list";
    }

    if (path.startsWith("/app/meals/")) {
      return "meal-detail";
    }

    if (path === "/app/foods") {
      return "food-list";
    }

    if (path.startsWith("/app/foods/")) {
      return "food-detail";
    }

    if (path === "/app/proposals" || path === "/app/ai-tools") {
      return "proposal-list";
    }

    if (path.startsWith("/app/proposals/") || path.startsWith("/app/ai-tools/")) {
      return "proposal-detail";
    }

    if (path.startsWith("/app/profile") || path.startsWith("/app/authors")) {
      return "profile";
    }

    return "generic";
  }

  function showNavigationPlaceholder(variant) {
    rememberInternalNavigation();

    navigationPlaceholderClasses.forEach(function (className) {
      root.classList.remove(className);
    });

    root.classList.remove("pwa-splash-enabled");
    root.classList.add("pwa-is-navigating");
    root.classList.add("pwa-navigation-placeholder--" + variant);
  }

  function resetNavigationPlaceholder() {
    root.classList.remove("pwa-is-navigating");
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

      showNavigationPlaceholder(getPlaceholderVariant(url));
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
