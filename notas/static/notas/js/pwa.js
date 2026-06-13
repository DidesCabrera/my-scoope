(function () {
  const isStandalone = window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;

  document.documentElement.classList.toggle("pwa-standalone", isStandalone);

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
