(function () {
  const root = document.documentElement;
  const isStandalone = window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;
  const navigationPlaceholderClasses = [
    "pwa-navigation-placeholder--dailyplan",
    "pwa-navigation-placeholder--meal",
    "pwa-navigation-placeholder--food",
    "pwa-navigation-placeholder--proposal",
    "pwa-navigation-placeholder--profile",
    "pwa-navigation-placeholder--home",
    "pwa-navigation-placeholder--generic",
  ];

  root.classList.toggle("pwa-standalone", isStandalone);

  function markPwaReady() {
    root.classList.add("pwa-ready");

    const splash = document.querySelector(".js-pwa-splash");
    if (!splash) {
      return;
    }

    window.setTimeout(function () {
      splash.remove();
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
    const path = url.pathname;

    if (path === "/app/" || path === "/app") {
      return "home";
    }

    if (path.startsWith("/app/dailyplans/")) {
      return "dailyplan";
    }

    if (path.startsWith("/app/meals/")) {
      return "meal";
    }

    if (path.startsWith("/app/foods/")) {
      return "food";
    }

    if (path.startsWith("/app/proposals/") || path.startsWith("/app/ai-tools/")) {
      return "proposal";
    }

    if (path.startsWith("/app/profile/") || path.startsWith("/app/authors/")) {
      return "profile";
    }

    return "generic";
  }

  function showNavigationPlaceholder(variant) {
    navigationPlaceholderClasses.forEach(function (className) {
      root.classList.remove(className);
    });

    root.classList.add("pwa-is-navigating");
    root.classList.add("pwa-navigation-placeholder--" + variant);
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

    window.addEventListener("pageshow", function () {
      root.classList.remove("pwa-is-navigating");
      navigationPlaceholderClasses.forEach(function (className) {
        root.classList.remove(className);
      });
    });
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
