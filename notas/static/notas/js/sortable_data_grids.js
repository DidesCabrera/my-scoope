(function () {
  if (window.__myscoopeSortableDataGridsInitialized) {
    return;
  }

  window.__myscoopeSortableDataGridsInitialized = true;

  const GRID_SELECTOR = ".data-grid";
  const HEADER_SELECTOR = ".data-grid-header";
  const HEADER_CELL_SELECTOR = ".data-grid-col";
  const ROW_SELECTOR = ".data-grid-row";
  const EMPTY_SELECTOR = ".data-grid-empty";
  const SORT_ICON_CLASS = "data-grid-sort-icon";
  const SORT_CONTENT_CLASS = "data-grid-sort-content";

  const EXCLUDED_GRID_SELECTORS = [
    ".data-grid--menu",
    ".data-grid--list-panel",
    ".data-grid--foods-edit",
    ".data-grid--meals-edit",
    ".data-grid--mobile-foods-edit",
    ".data-grid--mobile-meals-edit",
    ".js-dpm-sortable",
    ".js-mealfood-sortable",
    ".js-list-reorder-panel",
    ".js-list-delete-panel",
  ];

  function isExcludedGrid(grid) {
    return EXCLUDED_GRID_SELECTORS.some((selector) => grid.matches(selector));
  }

  function getHeader(grid) {
    return grid.querySelector(HEADER_SELECTOR);
  }

  function getHeaderCells(grid) {
    const header = getHeader(grid);
    if (!header) return [];
    return Array.from(header.children).filter((child) =>
      child.matches(HEADER_CELL_SELECTOR)
    );
  }

  function getRows(grid) {
    return Array.from(grid.children).filter((child) =>
      child.matches(ROW_SELECTOR)
    );
  }

  function getSortableRows(grid) {
    return getRows(grid).filter((row) => !row.matches(EMPTY_SELECTOR));
  }

  function parseSortableValue(text) {
    const normalized = (text || "")
      .trim()
      .replace(/,/g, ".")
      .replace(/−/g, "-");

    const numberMatch = normalized.match(/-?\d+(?:\.\d+)?/);

    if (numberMatch) {
      return {
        type: "number",
        value: Number(numberMatch[0]),
      };
    }

    return {
      type: "text",
      value: normalized.toLocaleLowerCase(),
    };
  }

  function getCellValue(row, columnIndex) {
    const cell = row.children[columnIndex];
    return parseSortableValue(cell ? cell.textContent : "");
  }

  function compareValues(a, b) {
    if (a.type === "number" && b.type === "number") {
      return a.value - b.value;
    }

    return String(a.value).localeCompare(String(b.value), undefined, {
      numeric: true,
      sensitivity: "base",
    });
  }

  function refreshLucideIcons() {
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  }

  function getSortContent(headerCell) {
    return headerCell.querySelector(`.${SORT_CONTENT_CLASS}`) || headerCell;
  }

  function removeSortIcon(headerCell) {
    const existingIcon = headerCell.querySelector(`.${SORT_ICON_CLASS}`);

    if (existingIcon) {
      existingIcon.remove();
    }
  }

  function resetHeaderCells(grid) {
    getHeaderCells(grid).forEach((cell) => {
      cell.classList.remove(
        "is-grid-sorted",
        "is-grid-sorted-desc",
        "is-grid-sorted-asc"
      );
      cell.removeAttribute("aria-sort");
      removeSortIcon(cell);
    });
  }

  function markHeaderCell(headerCell, direction) {
    const iconName = direction === "desc" ? "chevron-down" : "chevron-up";
    const icon = document.createElement("i");

    icon.setAttribute("data-lucide", iconName);
    icon.setAttribute("aria-hidden", "true");
    icon.className = SORT_ICON_CLASS;

    headerCell.classList.add("is-grid-sorted", `is-grid-sorted-${direction}`);
    headerCell.setAttribute(
      "aria-sort",
      direction === "desc" ? "descending" : "ascending"
    );
    getSortContent(headerCell).appendChild(icon);
    refreshLucideIcons();
  }

  function restoreOriginalOrder(grid) {
    const rows = getSortableRows(grid).sort((a, b) => {
      return Number(a.dataset.originalIndex || 0) - Number(b.dataset.originalIndex || 0);
    });

    rows.forEach((row) => grid.appendChild(row));
    resetHeaderCells(grid);
    grid.dataset.sortColumn = "";
    grid.dataset.sortDirection = "";
  }

  function sortGrid(grid, columnIndex, direction) {
    const rows = getSortableRows(grid);

    rows.sort((rowA, rowB) => {
      const comparison = compareValues(
        getCellValue(rowA, columnIndex),
        getCellValue(rowB, columnIndex)
      );

      if (comparison === 0) {
        return Number(rowA.dataset.originalIndex || 0) - Number(rowB.dataset.originalIndex || 0);
      }

      return direction === "desc" ? comparison * -1 : comparison;
    });

    rows.forEach((row) => grid.appendChild(row));
  }

  function getNextDirection(grid, columnIndex) {
    const currentColumn = grid.dataset.sortColumn;
    const currentDirection = grid.dataset.sortDirection;

    if (currentColumn !== String(columnIndex)) {
      return "desc";
    }

    if (!currentDirection) {
      return "desc";
    }

    if (currentDirection === "desc") {
      return "asc";
    }

    return "original";
  }

  function applySort(grid, headerCell, columnIndex) {
    const nextDirection = getNextDirection(grid, columnIndex);

    if (nextDirection === "original") {
      restoreOriginalOrder(grid);
      return;
    }

    sortGrid(grid, columnIndex, nextDirection);
    resetHeaderCells(grid);
    markHeaderCell(headerCell, nextDirection);

    grid.dataset.sortColumn = String(columnIndex);
    grid.dataset.sortDirection = nextDirection;
  }

  function wrapHeaderContent(cell) {
    if (cell.querySelector(`.${SORT_CONTENT_CLASS}`)) {
      return;
    }

    const wrapper = document.createElement("span");
    wrapper.className = SORT_CONTENT_CLASS;

    while (cell.firstChild) {
      wrapper.appendChild(cell.firstChild);
    }

    cell.appendChild(wrapper);
  }

  function prepareGrid(grid) {
    if (!grid || grid.dataset.sortableReady === "true" || isExcludedGrid(grid)) {
      return;
    }

    const headerCells = getHeaderCells(grid);
    const rows = getSortableRows(grid);

    if (!headerCells.length || rows.length < 2) {
      return;
    }

    rows.forEach((row, index) => {
      row.dataset.originalIndex = String(index);
    });

    headerCells.forEach((cell, columnIndex) => {
      wrapHeaderContent(cell);
      cell.classList.add("is-grid-sortable");
      cell.setAttribute("role", "button");
      cell.setAttribute("tabindex", "0");

      cell.addEventListener("click", function () {
        applySort(grid, cell, columnIndex);
      });

      cell.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" && event.key !== " ") {
          return;
        }

        event.preventDefault();
        applySort(grid, cell, columnIndex);
      });
    });

    grid.dataset.sortableReady = "true";
  }

  function bootSortableDataGrids() {
    document.querySelectorAll(GRID_SELECTOR).forEach(prepareGrid);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootSortableDataGrids);
  } else {
    bootSortableDataGrids();
  }
})();
