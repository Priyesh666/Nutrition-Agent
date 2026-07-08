/**
 * NutriGuide — Main JavaScript
 * Common utilities, toast system, auth helpers
 */

// ── Toast Notification System ─────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    document.body.appendChild(container);
  }

  const icons = {
    success: 'bi-check-circle-fill text-success',
    danger: 'bi-exclamation-circle-fill text-danger',
    warning: 'bi-exclamation-triangle-fill text-warning',
    info: 'bi-info-circle-fill text-info',
  };

  const toast = document.createElement('div');
  toast.className = `ng-toast ${type}`;
  toast.innerHTML = `
    <i class="bi ${icons[type] || icons.info} fs-5"></i>
    <span class="flex-grow-1">${escapeHtml(message)}</span>
    <button style="background:none;border:none;padding:0;cursor:pointer;color:#9ca3af;font-size:1rem;"
            onclick="this.closest('.ng-toast').remove()">×</button>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'toastIn .25s ease-out reverse';
    setTimeout(() => toast.remove(), 250);
  }, duration);
}

// ── Escape HTML ───────────────────────────────────────────────────
function escapeHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// ── Password visibility toggle ────────────────────────────────────
function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  const icon = btn.querySelector('i');
  if (input.type === 'password') {
    input.type = 'text';
    icon.className = 'bi bi-eye-slash text-muted';
  } else {
    input.type = 'password';
    icon.className = 'bi bi-eye text-muted';
  }
}

// ── Password strength checker ─────────────────────────────────────
function checkPasswordStrength(password) {
  const bar = document.getElementById('pwStrengthBar');
  const text = document.getElementById('pwStrengthText');
  if (!bar || !text) return;

  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  const levels = [
    { label: '', color: '#e5e7eb', width: '0%' },
    { label: 'Very weak', color: '#ef4444', width: '20%' },
    { label: 'Weak', color: '#f97316', width: '40%' },
    { label: 'Fair', color: '#f59e0b', width: '60%' },
    { label: 'Strong', color: '#22c55e', width: '80%' },
    { label: 'Very strong', color: '#16a34a', width: '100%' },
  ];

  const level = levels[Math.min(score, 5)];
  bar.style.width = level.width;
  bar.style.background = level.color;
  text.textContent = level.label;
  text.style.color = level.color;
}

// ── Auto-dismiss flash messages ───────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const alerts = document.querySelectorAll('.alert.alert-dismissible');
  alerts.forEach(alert => {
    setTimeout(() => {
      const btn = alert.querySelector('.btn-close');
      if (btn) btn.click();
    }, 5000);
  });

  // Render markdown content in existing messages
  document.querySelectorAll('.markdown-content').forEach(el => {
    if (el.dataset.rendered) return;
    el.innerHTML = renderMarkdown(el.textContent || el.innerText);
    el.dataset.rendered = 'true';
  });
});

// ── Markdown renderer ─────────────────────────────────────────────
function renderMarkdown(text) {
  if (typeof marked !== 'undefined') {
    return marked.parse(text, { breaks: true, gfm: true });
  }
  // Minimal fallback
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br/>');
}

// ── Water amount shortcut ─────────────────────────────────────────
function setWaterAmount(ml) {
  const input = document.getElementById('waterAmount');
  if (input) input.value = ml;
}

// ── Dashboard: Log food ───────────────────────────────────────────
async function logFood() {
  const name = document.getElementById('foodName').value.trim();
  if (!name) { showToast('Please enter a food name', 'warning'); return; }

  const payload = {
    food_name: name,
    meal_type: document.getElementById('mealType').value,
    quantity: document.getElementById('foodQuantity').value || '1 serving',
    calories: parseFloat(document.getElementById('foodCalories').value) || 0,
    protein: parseFloat(document.getElementById('foodProtein').value) || 0,
    carbs: parseFloat(document.getElementById('foodCarbs').value) || 0,
    fat: parseFloat(document.getElementById('foodFat').value) || 0,
  };

  try {
    const res = await fetch('/api/calorie-log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (res.ok) {
      showToast(`✅ ${name} logged! Today: ${data.daily_total} kcal`, 'success');
      // Close modal
      const modal = bootstrap.Modal.getInstance(document.getElementById('addFoodModal'));
      if (modal) modal.hide();
      // Clear inputs
      ['foodName', 'foodQuantity', 'foodCalories', 'foodProtein', 'foodCarbs', 'foodFat'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
      setTimeout(() => location.reload(), 800);
    } else {
      showToast(data.error || 'Failed to log food', 'danger');
    }
  } catch (e) {
    showToast('Network error. Please try again.', 'danger');
  }
}

// ── Dashboard: Delete calorie log ─────────────────────────────────
async function deleteCalorieLog(logId) {
  if (!confirm('Remove this food entry?')) return;
  try {
    const res = await fetch(`/api/calorie-log/${logId}`, { method: 'DELETE' });
    if (res.ok) {
      const row = document.getElementById(`log-row-${logId}`);
      if (row) row.remove();
      showToast('Entry removed', 'info');
    }
  } catch (e) {
    showToast('Failed to delete entry', 'danger');
  }
}

// ── Dashboard: Log water ──────────────────────────────────────────
async function logWater() {
  const amount = parseFloat(document.getElementById('waterAmount').value) || 0;
  if (amount <= 0) { showToast('Please enter a valid amount', 'warning'); return; }

  try {
    const res = await fetch('/api/water-log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount_ml: amount }),
    });
    const data = await res.json();
    if (res.ok) {
      showToast(`💧 ${amount}ml logged! Total: ${data.total_ml}ml (${data.percentage}%)`, 'success');
      const waterEl = document.getElementById('waterDisplayMl');
      if (waterEl) waterEl.textContent = data.total_ml;
      const modal = bootstrap.Modal.getInstance(document.getElementById('waterModal'));
      if (modal) modal.hide();
    }
  } catch (e) {
    showToast('Failed to log water', 'danger');
  }
}

// ── Dashboard: Daily tip ───────────────────────────────────────────
async function loadDailyTip() {
  const tipEl = document.getElementById('dailyTipText');
  if (!tipEl) return;
  tipEl.textContent = 'Loading...';
  try {
    const res = await fetch('/api/nutrition-tip');
    const data = await res.json();
    tipEl.textContent = data.tip || 'Stay hydrated and eat mindfully!';
  } catch {
    tipEl.textContent = 'Eat a rainbow of colourful vegetables every day for a full spectrum of micronutrients.';
  }
}

// Auto-load tip on dashboard
if (document.getElementById('dailyTipText')) {
  loadDailyTip();
}

// ── Dashboard: Recipe Generator ────────────────────────────────────
async function generateRecipe() {
  const ingredients = document.getElementById('recipeIngredients').value.trim();
  if (!ingredients) { showToast('Please enter some ingredients', 'warning'); return; }

  const resultEl = document.getElementById('recipeResult');
  resultEl.style.display = 'block';
  resultEl.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-success"></div><p class="mt-2 text-muted small">Generating recipe with AI...</p></div>';

  try {
    const res = await fetch('/api/generate-recipe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ingredients }),
    });
    const data = await res.json();
    resultEl.innerHTML = renderMarkdown(data.recipe || data.error || 'Failed to generate recipe.');
  } catch (e) {
    resultEl.innerHTML = '<p class="text-danger">Failed to generate recipe. Please try again.</p>';
  }
}

// ── Dashboard: Grocery List ────────────────────────────────────────
async function generateGroceryList() {
  const days = document.getElementById('groceryDays').value;
  const resultEl = document.getElementById('groceryResult');
  resultEl.style.display = 'block';
  resultEl.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-warning"></div><p class="mt-2 text-muted small">Generating grocery list...</p></div>';

  try {
    const res = await fetch('/api/generate-grocery-list', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ days: parseInt(days) }),
    });
    const data = await res.json();
    resultEl.innerHTML = renderMarkdown(data.grocery_list || 'Failed to generate list.');
  } catch (e) {
    resultEl.innerHTML = '<p class="text-danger">Failed to generate grocery list.</p>';
  }
}

// ── Image upload: preview and analyze ─────────────────────────────
async function previewAndUpload(input) {
  const file = input.files[0];
  if (!file) return;

  // Preview
  const preview = document.getElementById('imagePreview');
  if (preview) {
    preview.src = URL.createObjectURL(file);
    preview.style.display = 'block';
  }

  const resultEl = document.getElementById('imageAnalysisResult');
  if (!resultEl) return;
  resultEl.style.display = 'block';
  resultEl.innerHTML = '<div class="text-center py-2"><div class="spinner-border text-danger spinner-border-sm"></div> Analyzing image...</div>';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/analyze-food-image', { method: 'POST', body: formData });
    const data = await res.json();
    resultEl.innerHTML = renderMarkdown(data.analysis || data.error || 'Analysis complete.');
  } catch (e) {
    resultEl.innerHTML = '<p class="text-danger">Upload failed.</p>';
  }
}

async function analyzeFromChat(input) {
  previewAndUpload(input);
}
