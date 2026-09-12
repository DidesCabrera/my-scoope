(() => {
  const parseConfig = (id) => {
    const element = document.getElementById(id);
    return element ? JSON.parse(element.textContent) : "";
  };

  const environment = parseConfig("paddle-environment");
  const token = parseConfig("paddle-client-token");
  const successUrl = parseConfig("paddle-success-url");
  const checkoutButtons = document.querySelectorAll("[data-paddle-checkout]");

  if (!window.Paddle || !token || !successUrl || checkoutButtons.length === 0) {
    checkoutButtons.forEach((button) => {
      button.disabled = true;
    });
    return;
  }

  if (environment === "sandbox") {
    window.Paddle.Environment.set("sandbox");
  }
  window.Paddle.Initialize({
    token,
    checkout: {
      settings: {
        displayMode: "overlay",
        locale: "es",
        theme: "light",
        successUrl,
      },
    },
  });

  checkoutButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (button.disabled) return;
      window.Paddle.Checkout.open({
        items: [{ priceId: button.dataset.priceId, quantity: 1 }],
        customer: { email: button.dataset.customerEmail },
        customData: {
          myscoope_checkout_reference: button.dataset.checkoutReference,
        },
      });
    });
  });
})();
