document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('select.col-map').forEach((sel) => {
    sel.addEventListener('change', () => {
      const target = document.getElementById(sel.dataset.target);
      if (target) {
        target.textContent = sel.value || target.dataset.original;
      }
    });
  });
});
