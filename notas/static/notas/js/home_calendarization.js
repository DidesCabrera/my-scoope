document.addEventListener("DOMContentLoaded", function () {
  const calendar = document.querySelector("[data-home-calendar]");

  if (!calendar) {
    return;
  }

  const dayButtons = Array.from(calendar.querySelectorAll("[data-home-calendar-day]"));
  const panels = Array.from(calendar.querySelectorAll('[role="tabpanel"]'));
  const planCards = Array.from(calendar.querySelectorAll("[data-home-calendar-plan-card]"));
  const weekViewport = calendar.querySelector("[data-home-calendar-week-viewport]");
  const weekTrack = calendar.querySelector("[data-home-calendar-week-track]");
  const weekNavs = Array.from(calendar.querySelectorAll("[data-home-calendar-week-nav]"));
  const weekSlides = Array.from(calendar.querySelectorAll("[data-home-calendar-week]"));
  const weekDayLinks = Array.from(calendar.querySelectorAll("[data-home-calendar-day-link]"));
  const mobileQuery = window.matchMedia("(max-width: 620px)");
  const scrollStorageKey = "myscoope.homeCalendar.scrollY";
  let activeWeekIndex = Math.max(0, weekSlides.findIndex(function (week) {
    return week.classList.contains("is-active");
  }));

  function restoreCalendarScroll() {
    let storedScrollY = null;

    try {
      storedScrollY = sessionStorage.getItem(scrollStorageKey);
      sessionStorage.removeItem(scrollStorageKey);
    } catch (error) {
      storedScrollY = null;
    }

    if (storedScrollY === null) {
      return;
    }

    const scrollY = Number(storedScrollY);
    if (!Number.isFinite(scrollY)) {
      return;
    }

    requestAnimationFrame(function () {
      window.scrollTo({ top: scrollY, left: 0, behavior: "auto" });
    });
  }

  function storeCalendarScroll() {
    try {
      sessionStorage.setItem(scrollStorageKey, String(window.scrollY));
    } catch (error) {
      // If storage is unavailable, the link keeps its normal navigation behavior.
    }
  }

  function selectDay(selectedButton) {
    dayButtons.forEach(function (button) {
      const isSelected = button === selectedButton;
      button.classList.toggle("is-selected", isSelected);
      button.setAttribute("aria-selected", isSelected ? "true" : "false");
    });

    panels.forEach(function (panel) {
      panel.hidden = panel.id !== selectedButton.getAttribute("aria-controls");
    });
  }

  function syncWeekSlider() {
    if (!weekTrack || !weekViewport) {
      return;
    }

    if (mobileQuery.matches) {
      weekTrack.style.transform = "";
      weekViewport.scrollLeft = activeWeekIndex * weekViewport.clientWidth;
      return;
    }

    weekTrack.style.transform = "translateX(-" + (activeWeekIndex * 100) + "%)";
  }

  function slideWeek(direction) {
    const nextIndex = activeWeekIndex + direction;

    if (nextIndex < 0 || nextIndex >= weekSlides.length) {
      return;
    }

    activeWeekIndex = nextIndex;
    syncWeekSlider();
  }

  function setPlanCardExpanded(card, isExpanded) {
    const preview = card.querySelector("[data-home-calendar-plan-preview]");

    if (!preview) {
      return;
    }

    card.classList.toggle("is-expanded", isExpanded);
    card.setAttribute("aria-expanded", isExpanded ? "true" : "false");
    preview.hidden = !isExpanded;
  }

  function togglePlanCard(card) {
    setPlanCardExpanded(card, !card.classList.contains("is-expanded"));
  }

  dayButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      selectDay(button);
    });
  });

  weekNavs.forEach(function (nav) {
    nav.addEventListener("click", function (event) {
      event.preventDefault();
      slideWeek(nav.dataset.homeCalendarWeekNav === "next" ? 1 : -1);
    });
  });

  weekDayLinks.forEach(function (link) {
    link.addEventListener("click", storeCalendarScroll);
  });

  planCards.forEach(function (card) {
    card.addEventListener("click", function (event) {
      if (event.target.closest("a, button, input, textarea, select")) {
        return;
      }

      togglePlanCard(card);
    });

    card.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }

      event.preventDefault();
      togglePlanCard(card);
    });
  });

  syncWeekSlider();
  restoreCalendarScroll();
  window.addEventListener("resize", syncWeekSlider);
});
