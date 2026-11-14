(() => {
  const manifestUrl = "/api/v1/foods/visual-assets/manifest";
  const imagePath = /^\/api\/v1\/foods\/visual-assets\/[0-9a-f-]{36}\/[0-9a-f]{64}\.png$/;
  const refreshMs = 60_000;
  let images = new Map();
  let loadedAt = 0;
  let pending = null;

  const normalizeName = (name) => String(name || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLocaleLowerCase("es")
    .replace(/\s+/g, " ");

  const parseManifest = (payload) => {
    const next = new Map();
    for (const [name, path] of Object.entries(payload?.images || {})) {
      if (imagePath.test(path)) next.set(`name:${normalizeName(name)}`, path);
    }
    for (const [id, path] of Object.entries(payload?.food_ids || {})) {
      if (/^[1-9]\d*$/.test(id) && imagePath.test(path)) next.set(`id:${id}`, path);
    }
    return next;
  };

  const render = () => {
    document.querySelectorAll("[data-food-visual]").forEach((icon) => {
      const id = icon.dataset.foodId;
      const key = /^[1-9]\d*$/.test(id || "")
        ? `id:${id}`
        : `name:${normalizeName(icon.dataset.foodName)}`;
      const path = images.get(key);
      const image = icon.querySelector(".food-visual-icon__image");
      const fallback = icon.querySelector(".food-visual-icon__fallback");
      if (!image || !fallback) return;

      if (!path || (icon.dataset.failedPath === path && Date.now() - Number(icon.dataset.failedAt) < refreshMs)) {
        image.hidden = true;
        fallback.hidden = false;
        return;
      }
      if (image.getAttribute("src") === path && !image.hidden) return;
      image.onload = () => {
        image.hidden = false;
        fallback.hidden = true;
      };
      image.onerror = () => {
        icon.dataset.failedPath = path;
        icon.dataset.failedAt = String(Date.now());
        image.hidden = true;
        fallback.hidden = false;
      };
      image.hidden = true;
      fallback.hidden = false;
      image.src = path;
    });
  };

  const refresh = () => {
    if (!document.querySelector("[data-food-visual]")) return Promise.resolve();
    if (pending) return pending;
    if (loadedAt && Date.now() - loadedAt < refreshMs) return Promise.resolve();
    pending = fetch(manifestUrl)
      .then((response) => {
        if (!response.ok) throw new Error(`Food visuals manifest: ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        images = parseManifest(payload);
        loadedAt = Date.now();
        render();
      })
      .catch(() => { loadedAt = Date.now(); })
      .finally(() => { pending = null; });
    return pending;
  };

  render();
  void refresh();
  setInterval(() => { void refresh(); render(); }, refreshMs);
  new MutationObserver(() => { render(); void refresh(); }).observe(document.body, { childList: true, subtree: true });
})();
