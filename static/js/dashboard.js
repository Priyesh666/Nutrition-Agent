/**
 * NutriGuide — Dashboard JS
 * Dashboard-specific functionality
 */
document.addEventListener('DOMContentLoaded', () => {
  // Scroll food log table to bottom
  const tableWrapper = document.querySelector('#foodLogContainer .table-responsive');
  if (tableWrapper) {
    tableWrapper.scrollTop = tableWrapper.scrollHeight;
  }
});
