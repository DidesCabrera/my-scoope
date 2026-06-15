(function () {
  const isStandalone = window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;

  document.documentElement.classList.toggle("pwa-standalone", isStandalone);

  function markPwaReady() {
    document.documentElement.classList.add("pwa-ready");

    const splash = document.querySelector(".js-pwa-splash");
    if (!splash) {
      return;
    }

    window.setTimeout(function () {
      splash.remove();
    }, 280);
  }

  if (document.readyState === "complete") {
    markPwaReady();
  } else {
    window.addEventListener("load", markPwaReady, { once: true });
  }

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
