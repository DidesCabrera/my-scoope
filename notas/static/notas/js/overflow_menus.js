document.addEventListener("DOMContentLoaded", () => {
  const menus = Array.from(document.querySelectorAll(".overflow-menu"));

  if (!menus.length) return;

  function closeMenu(menu) {
    menu.classList.remove("is-open");
    const button = menu.querySelector(".overflow-btn");
    if (button) {
      button.setAttribute("aria-expanded", "false");
    }
  }

  function closeOtherMenus(currentMenu) {
    menus.forEach((menu) => {
      if (menu !== currentMenu) {
        closeMenu(menu);
      }
    });
  }

  function toggleMenu(menu) {
    const isOpen = menu.classList.contains("is-open");
    closeOtherMenus(menu);

    if (isOpen) {
      closeMenu(menu);
      return;
    }

    menu.classList.add("is-open");
    const button = menu.querySelector(".overflow-btn");
    if (button) {
      button.setAttribute("aria-expanded", "true");
    }
  }

  menus.forEach((menu) => {
    const button = menu.querySelector(".overflow-btn");
    if (!button) return;

    button.setAttribute("aria-haspopup", "true");
    button.setAttribute("aria-expanded", "false");

    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleMenu(menu);
    });

    menu.addEventListener("click", (event) => {
      const action = event.target.closest(".overflow-action");
      if (action) {
        closeMenu(menu);
        return;
      }

      event.stopPropagation();
    });
  });

  document.addEventListener("click", () => {
    menus.forEach(closeMenu);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      menus.forEach(closeMenu);
    }
  });
});
