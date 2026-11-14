document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-repeat-form]').forEach((form) => {
    const add = form.querySelector('[data-repeat-add]');
    const list = form.querySelector('[data-repeat-list]');
    if (!add || !list) return;
    add.addEventListener('click', () => {
      const first = list.querySelector('.web-parity__repeat-row');
      if (!first || list.children.length >= 30) return;
      const row = first.cloneNode(true);
      row.querySelectorAll('input').forEach((input) => { input.value = ''; });
      row.querySelectorAll('select').forEach((select) => { select.selectedIndex = 0; });
      list.append(row);
      row.querySelector('input, select')?.focus();
    });
    list.addEventListener('click', (event) => {
      const remove = event.target.closest('[data-repeat-remove]');
      if (remove && list.querySelectorAll('.web-parity__repeat-row').length > 1) {
        remove.closest('.web-parity__repeat-row')?.remove();
      }
    });
  });
});
