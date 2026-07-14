(() => {
  if (window.lucide && typeof window.lucide.createIcons === "function") {
    window.lucide.createIcons();
  }

  const header = document.querySelector("[data-landing-header]");
  const heroLogo = document.querySelector("#hero .hero-logo");

  if (header && heroLogo) {
    const syncHeaderVisibility = () => {
      const logoBounds = heroLogo.getBoundingClientRect();
      header.classList.toggle("is-visible", logoBounds.bottom <= 0);
    };

    syncHeaderVisibility();
    window.addEventListener("scroll", syncHeaderVisibility, { passive: true });
    window.addEventListener("resize", syncHeaderVisibility);
  }

  const slider = document.querySelector("[data-landing-slider]");
  const sliderTrack = slider?.querySelector("[data-slider-track]");
  const slides = sliderTrack ? [...sliderTrack.children] : [];
  const dotsContainer = slider?.querySelector("[data-slider-dots]");

  if (sliderTrack && dotsContainer && slides.length) {
    const dots = slides.map((slide, index) => {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.setAttribute("aria-label", `Mostrar imagen ${index + 1}`);
      dot.classList.toggle("is-active", index === 0);
      dot.addEventListener("click", () => {
        slide.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "start" });
      });
      dotsContainer.appendChild(dot);
      return dot;
    });

    const syncActiveDot = () => {
      const currentIndex = slides.reduce((closestIndex, slide, index) => {
        const currentDistance = Math.abs(slide.offsetLeft - sliderTrack.scrollLeft);
        const closestDistance = Math.abs(slides[closestIndex].offsetLeft - sliderTrack.scrollLeft);
        return currentDistance < closestDistance ? index : closestIndex;
      }, 0);

      dots.forEach((dot, index) => dot.classList.toggle("is-active", index === currentIndex));
    };

    sliderTrack.addEventListener("scroll", syncActiveDot, { passive: true });
  }

  const billingToggle = document.querySelector("[data-billing-toggle]");
  const billingButtons = billingToggle ? [...billingToggle.querySelectorAll("[data-billing-period]")] : [];
  const paidPlanCards = [...document.querySelectorAll("[data-plan-card]")];

  const setBillingPeriod = (period) => {
    billingButtons.forEach((button) => {
      const isActive = button.dataset.billingPeriod === period;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });

    paidPlanCards.forEach((card) => {
      const price = period === "yearly" ? card.dataset.yearlyPrice : card.dataset.monthlyPrice;
      const priceElement = card.querySelector("[data-plan-price]");
      const labelElement = card.querySelector("[data-billing-label]");

      if (priceElement) priceElement.textContent = price;
      if (labelElement) labelElement.textContent = period === "yearly" ? "Anual" : "Mensual";
    });
  };

  billingButtons.forEach((button) => {
    button.addEventListener("click", () => setBillingPeriod(button.dataset.billingPeriod));
  });

  setBillingPeriod("monthly");
})();
