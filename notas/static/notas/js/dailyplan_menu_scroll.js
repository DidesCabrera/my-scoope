(function () {
  function bootDailyPlanMenuScroll() {
    document.addEventListener("click", function (event) {
      const trigger = event.target.closest("[data-dailyplan-meal-target]");
      if (!trigger) return;

      const targetId = trigger.dataset.dailyplanMealTarget;
      if (!targetId) return;

      const target = document.getElementById(targetId);
      if (!target) return;

      event.preventDefault();
      target.scrollIntoView({
        behavior: "smooth",
        block: "start",
        inline: "nearest",
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootDailyPlanMenuScroll);
  } else {
    bootDailyPlanMenuScroll();
  }
})();
