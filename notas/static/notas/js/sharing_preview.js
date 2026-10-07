(() => {
  const button = document.querySelector("[data-deep-link]");
  if (!button) return;

  button.addEventListener("click", (event) => {
    event.preventDefault();
    const isAndroid = /Android/i.test(navigator.userAgent);
    const storeUrl = isAndroid ? button.dataset.playStoreUrl : button.dataset.appStoreUrl;
    const startedAt = Date.now();
    let fallbackTimer;

    const cancelFallback = () => {
      if (document.visibilityState === "hidden") window.clearTimeout(fallbackTimer);
    };
    document.addEventListener("visibilitychange", cancelFallback, { once: true });
    window.addEventListener("pagehide", cancelFallback, { once: true });

    window.location.href = button.dataset.deepLink;
    fallbackTimer = window.setTimeout(() => {
      if (document.visibilityState === "visible" && Date.now() - startedAt < 2500) {
        window.location.href = storeUrl;
      }
    }, 1400);
  });
})();
