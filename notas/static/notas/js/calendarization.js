(function () {
  const root = document.querySelector("[data-calendarization]");
  if (!root) return;

  const detectedTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  root.querySelectorAll("[data-detect-timezone]").forEach(function (input) {
    input.value = detectedTimezone;
  });

  const activationForm = root.querySelector("[data-activation-form]");
  if (activationForm) {
    const program = activationForm.querySelector("[data-program-select]");
    const start = activationForm.querySelector("[data-start-date]");
    const preview = activationForm.querySelector("[data-date-preview]");
    const previewProgram = activationForm.querySelector("[data-preview-program]");
    const previewDuration = activationForm.querySelector("[data-preview-duration]");
    const previewStart = activationForm.querySelector("[data-preview-start]");
    const previewEnd = activationForm.querySelector("[data-preview-end]");
    const warning = activationForm.querySelector("[data-incomplete-warning]");
    const incompleteConfirmation = warning && warning.querySelector("input[name='confirm_incomplete']");
    const continueButton = warning && warning.querySelector("[data-confirm-incomplete]");
    const today = new Date();
    const localToday = [today.getFullYear(), String(today.getMonth() + 1).padStart(2, "0"), String(today.getDate()).padStart(2, "0")].join("-");
    start.min = localToday;

    function refreshPreview() {
      const option = program.options[program.selectedIndex];
      const weeks = Number(option && option.dataset.weeks || 0);
      if (warning) warning.hidden = true;
      if (incompleteConfirmation) incompleteConfirmation.value = "";
      if (!weeks || !start.value) { preview.hidden = true; return; }
      const end = new Date(start.value + "T12:00:00");
      end.setDate(end.getDate() + weeks * 7 - 1);
      const startDate = new Date(start.value + "T12:00:00");
      previewProgram.textContent = option.textContent.split(" · ")[0];
      previewDuration.textContent = weeks + " semana" + (weeks === 1 ? "" : "s");
      previewStart.textContent = startDate.toLocaleDateString("es");
      previewEnd.textContent = end.toLocaleDateString("es");
      preview.hidden = false;
    }
    program.addEventListener("change", refreshPreview);
    start.addEventListener("change", refreshPreview);
    refreshPreview();

    function requestIncompleteConfirmation(event) {
      const option = program.options[program.selectedIndex];
      const hasEmptyDays = Number(option && option.dataset.emptyDays || 0) > 0;
      if (hasEmptyDays && incompleteConfirmation && !incompleteConfirmation.value) {
        event.preventDefault();
        warning.hidden = false;
        warning.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
    activationForm.addEventListener("submit", requestIncompleteConfirmation);
    if (continueButton) continueButton.addEventListener("click", function () {
      incompleteConfirmation.value = "on";
      warning.hidden = true;
      activationForm.requestSubmit();
    });
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
