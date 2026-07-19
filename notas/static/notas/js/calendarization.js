(function () {
  const root = document.querySelector("[data-calendarization]");
  if (!root) return;

  const detectedTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  root.querySelectorAll("[data-detect-timezone]").forEach(function (input) {
    if (!input.value || input.value === "UTC") input.value = detectedTimezone;
  });

  const activationForm = root.querySelector("[data-activation-form]");
  if (activationForm) {
    const program = activationForm.querySelector("[data-program-select]");
    const start = activationForm.querySelector("[data-start-date]");
    const preview = activationForm.querySelector("[data-date-preview]");
    const warning = activationForm.querySelector("[data-incomplete-warning]");
    const incompleteCheckbox = warning && warning.querySelector("input[name='confirm_incomplete']");
    const today = new Date();
    const localToday = [today.getFullYear(), String(today.getMonth() + 1).padStart(2, "0"), String(today.getDate()).padStart(2, "0")].join("-");
    start.min = localToday;
    if (!start.value) start.value = localToday;

    function refreshPreview() {
      const option = program.options[program.selectedIndex];
      const weeks = Number(option && option.dataset.weeks || 0);
      const emptyDays = Number(option && option.dataset.emptyDays || 0);
      if (warning) warning.hidden = emptyDays === 0;
      if (incompleteCheckbox) incompleteCheckbox.required = emptyDays > 0;
      if (!weeks || !start.value) { preview.textContent = "Selecciona un programa y una fecha para ver el rango."; return; }
      const end = new Date(start.value + "T12:00:00");
      end.setDate(end.getDate() + weeks * 7 - 1);
      preview.textContent = "Semana 1 · Día 1 comienza el " + new Date(start.value + "T12:00:00").toLocaleDateString("es") + " y finaliza el " + end.toLocaleDateString("es") + "." + (emptyDays ? " Hay " + emptyDays + " día(s) vacío(s)." : "");
    }
    program.addEventListener("change", refreshPreview);
    start.addEventListener("change", refreshPreview);
    refreshPreview();
  }

  root.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  function csrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }
  function urlBase64ToUint8Array(value) {
    const padding = "=".repeat((4 - value.length % 4) % 4);
    const raw = atob((value + padding).replace(/-/g, "+").replace(/_/g, "/"));
    return Uint8Array.from(Array.from(raw).map(function (char) { return char.charCodeAt(0); }));
  }

  const pushButton = root.querySelector("[data-push-button]");
  const pushDisableButton = root.querySelector("[data-push-disable-button]");
  const pushStatus = root.querySelector("[data-push-status]");
  if (pushButton && "serviceWorker" in navigator && "PushManager" in window) {
    pushButton.hidden = false;
  } else if (pushStatus) {
    pushStatus.textContent = "Web Push no está disponible en este contexto. En iPhone o iPad, instala MyScoope en la pantalla de inicio.";
  }
  if (pushButton) pushButton.addEventListener("click", async function () {
    pushButton.disabled = true;
    try {
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) throw new Error("Este navegador no admite Web Push.");
      const permission = await Notification.requestPermission();
      if (permission !== "granted") throw new Error("No se concedió permiso para notificaciones.");
      const registration = await navigator.serviceWorker.ready;
      let subscription = await registration.pushManager.getSubscription();
      if (!subscription) subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(root.dataset.vapidPublicKey) });
      const response = await fetch("/app/calendarization/push/subscriptions/", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() }, body: JSON.stringify(subscription.toJSON()) });
      if (!response.ok) throw new Error("El servidor rechazó la suscripción.");
      pushStatus.textContent = "Notificaciones activadas en este dispositivo.";
      pushButton.textContent = "Autorización actualizada";
    } catch (error) {
      pushStatus.textContent = error.message || "No fue posible activar las notificaciones.";
    } finally { pushButton.disabled = false; }
  });
  if (pushDisableButton) pushDisableButton.addEventListener("click", async function () {
    pushDisableButton.disabled = true;
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (!subscription) throw new Error("No hay una suscripción activa en este dispositivo.");
      const response = await fetch("/app/calendarization/push/subscriptions/deactivate/", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() }, body: JSON.stringify({ endpoint: subscription.endpoint }) });
      if (!response.ok) throw new Error("No fue posible desactivar la suscripción.");
      await subscription.unsubscribe();
      pushStatus.textContent = "Notificaciones desactivadas en este dispositivo.";
      pushDisableButton.hidden = true;
    } catch (error) {
      pushStatus.textContent = error.message || "No fue posible desactivar las notificaciones.";
    } finally { pushDisableButton.disabled = false; }
  });
})();
