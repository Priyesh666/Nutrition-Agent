/**
 * NutriGuide — Charts.js
 * Dashboard chart initialization using Chart.js
 */

document.addEventListener('DOMContentLoaded', () => {
  initWeeklyCalorieChart();
  initMealBreakdownChart();
});

function getMetaContent(name) {
  const el = document.querySelector(`meta[name="${name}"]`);
  if (!el) return null;
  try { return JSON.parse(el.getAttribute('content')); }
  catch { return null; }
}

// ── Weekly Calorie Bar Chart ──────────────────────────────────────
function initWeeklyCalorieChart() {
  const canvas = document.getElementById('weeklyCalorieChart');
  if (!canvas) return;

  const weekData = getMetaContent('week-data') || [];

  const labels = weekData.map(d => d.date);
  const values = weekData.map(d => d.calories);

  // Get calorie target from page
  const targetEl = document.querySelector('[data-calorie-target]');
  const target = targetEl ? parseInt(targetEl.dataset.calorieTarget) : null;

  const datasets = [{
    label: 'Calories',
    data: values,
    backgroundColor: values.map(v => v > 0 ? 'rgba(37,99,235,0.15)' : 'rgba(209,213,219,0.4)'),
    borderColor: values.map(v => v > 0 ? 'rgba(37,99,235,0.9)' : 'rgba(156,163,175,0.6)'),
    borderWidth: 2,
    borderRadius: 8,
    borderSkipped: false,
  }];

  if (target) {
    datasets.push({
      label: 'Target',
      data: Array(labels.length).fill(target),
      type: 'line',
      borderColor: 'rgba(22,163,74,0.7)',
      borderDash: [6, 3],
      borderWidth: 1.5,
      pointRadius: 0,
      fill: false,
      tension: 0,
    });
  }

  new Chart(canvas, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          display: target ? true : false,
          position: 'bottom',
          labels: { boxWidth: 12, font: { size: 11 }, padding: 12 },
        },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(0)} kcal`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { size: 11 }, color: '#6b7280' },
        },
        y: {
          grid: { color: 'rgba(0,0,0,.06)' },
          ticks: {
            font: { size: 11 },
            color: '#6b7280',
            callback: v => v === 0 ? '0' : `${v}`,
          },
          beginAtZero: true,
        },
      },
    },
  });
}

// ── Meal Breakdown Doughnut Chart ────────────────────────────────
function initMealBreakdownChart() {
  const canvas = document.getElementById('mealBreakdownChart');
  if (!canvas) return;

  const breakdown = getMetaContent('meal-breakdown') || {};
  const entries = Object.entries(breakdown).filter(([, v]) => v > 0);

  if (entries.length === 0) {
    canvas.parentElement.innerHTML =
      '<div class="text-center text-muted py-5"><i class="bi bi-pie-chart display-6 d-block mb-2 opacity-25"></i><small>No meals logged today</small></div>';
    return;
  }

  const labels = entries.map(([k]) => k.charAt(0).toUpperCase() + k.slice(1));
  const values = entries.map(([, v]) => Math.round(v));

  const COLORS = {
    breakfast: ['#3b82f6', '#bfdbfe'],
    lunch: ['#16a34a', '#bbf7d0'],
    dinner: ['#7c3aed', '#ede9fe'],
    snack: ['#d97706', '#fde68a'],
    other: ['#6b7280', '#e5e7eb'],
  };

  const bgs = entries.map(([k]) => (COLORS[k] || COLORS.other)[0]);
  const borders = entries.map(([k]) => (COLORS[k] || COLORS.other)[1]);

  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: bgs,
        borderColor: borders,
        borderWidth: 2,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { boxWidth: 10, font: { size: 11 }, padding: 10 },
        },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.label}: ${ctx.parsed} kcal`,
          },
        },
      },
    },
  });
}
