/**
 * NutriGuide — Chat Interface JavaScript
 * Handles AI chat, voice input, message rendering, export
 */

let isStreaming = false;
let recognition = null;
let voiceActive = false;
const MAX_CHARS = 2000;

// ── Initialization ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('chatInput');
  const charCount = document.getElementById('charCount');

  // Auto-scroll to bottom of messages
  scrollToBottom();

  // Render existing messages as markdown
  document.querySelectorAll('.msg-content').forEach(el => {
    if (!el.dataset.rendered) {
      el.innerHTML = renderMarkdown(el.textContent || el.innerText);
      el.dataset.rendered = 'true';
    }
  });

  // Character counter
  if (input && charCount) {
    input.addEventListener('input', () => {
      const len = input.value.length;
      charCount.textContent = `${len}/${MAX_CHARS}`;
      charCount.style.color = len > MAX_CHARS * 0.9 ? '#ef4444' : '#9ca3af';
    });
  }

  // Check for pre-filled query from URL
  const urlParams = new URLSearchParams(window.location.search);
  const prefill = urlParams.get('q');
  if (prefill && input) {
    input.value = prefill;
    input.dispatchEvent(new Event('input'));
    setTimeout(sendMessage, 400);
  }

  // Setup voice recognition if available
  setupVoiceRecognition();
});

// ── Send Message ──────────────────────────────────────────────────
async function sendMessage() {
  if (isStreaming) return;

  const input = document.getElementById('chatInput');
  const message = input.value.trim();

  if (!message) return;
  if (message.length > MAX_CHARS) {
    showToast(`Message too long (max ${MAX_CHARS} characters)`, 'warning');
    return;
  }

  // Hide welcome screen
  const welcome = document.getElementById('chatWelcome');
  if (welcome) welcome.remove();

  // Append user message
  appendMessage('user', message);
  input.value = '';
  input.style.height = 'auto';
  document.getElementById('charCount').textContent = `0/${MAX_CHARS}`;

  // Show typing indicator
  showTypingIndicator();
  setInputState(true);
  isStreaming = true;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });

    const data = await res.json();
    hideTypingIndicator();

    if (res.ok) {
      appendMessage('assistant', data.response, data.timestamp);
    } else {
      appendMessage('assistant', `⚠️ ${data.error || 'Something went wrong. Please try again.'}`, '');
    }
  } catch (err) {
    hideTypingIndicator();
    appendMessage('assistant', '⚠️ Network error. Please check your connection and try again.', '');
  } finally {
    setInputState(false);
    isStreaming = false;
  }
}

// ── Append Message to DOM ──────────────────────────────────────────
function appendMessage(role, content, timestamp = '') {
  const container = document.getElementById('chatMessages');
  const now = timestamp || new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false });

  const msgDiv = document.createElement('div');
  msgDiv.className = `message message-${role}`;

  const contentHtml = renderMarkdown(content);

  if (role === 'assistant') {
    msgDiv.innerHTML = `
      <div class="msg-avatar ai-avatar-sm"><span>🥗</span></div>
      <div class="msg-bubble">
        <div class="msg-content">${contentHtml}</div>
        <div class="msg-time">${now}</div>
      </div>`;
  } else {
    msgDiv.innerHTML = `
      <div class="msg-bubble">
        <div class="msg-content">${escapeHtml(content)}</div>
        <div class="msg-time">${now}</div>
      </div>
      <div class="msg-avatar user-avatar-sm"><i class="bi bi-person-fill"></i></div>`;
  }

  container.appendChild(msgDiv);
  scrollToBottom();
}

// ── Typing Indicator ──────────────────────────────────────────────
function showTypingIndicator() {
  const indicator = document.getElementById('typingIndicator');
  if (indicator) {
    indicator.classList.remove('d-none');
    scrollToBottom();
  }
}

function hideTypingIndicator() {
  const indicator = document.getElementById('typingIndicator');
  if (indicator) indicator.classList.add('d-none');
}

// ── Input state ────────────────────────────────────────────────────
function setInputState(disabled) {
  const sendBtn = document.getElementById('sendBtn');
  const input = document.getElementById('chatInput');
  if (sendBtn) sendBtn.disabled = disabled;
  if (input) input.disabled = disabled;
}

// ── Scroll to bottom ───────────────────────────────────────────────
function scrollToBottom() {
  const container = document.getElementById('chatMessages');
  if (container) {
    setTimeout(() => {
      container.scrollTop = container.scrollHeight;
    }, 50);
  }
}

// ── Keyboard handler ───────────────────────────────────────────────
function handleChatKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

// ── Auto-resize textarea ───────────────────────────────────────────
function autoResizeTextarea(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

// ── Quick Prompt ───────────────────────────────────────────────────
function sendQuickPrompt(prompt) {
  const input = document.getElementById('chatInput');
  if (input) {
    input.value = prompt;
    input.dispatchEvent(new Event('input'));
    sendMessage();
  }
}

// ── Clear Chat History ─────────────────────────────────────────────
async function clearChatHistory() {
  if (!confirm('Clear all chat history? This cannot be undone.')) return;
  try {
    const res = await fetch('/api/chat/clear', { method: 'POST' });
    if (res.ok) {
      const container = document.getElementById('chatMessages');
      container.innerHTML = `
        <div class="chat-welcome" id="chatWelcome">
          <div class="welcome-icon">🥗</div>
          <h5>Chat history cleared!</h5>
          <p class="text-muted">Start a fresh conversation with NutriGuide.</p>
        </div>`;
      showToast('Chat history cleared', 'info');
    }
  } catch (e) {
    showToast('Failed to clear history', 'danger');
  }
}

// ── Export Chat ────────────────────────────────────────────────────
function exportChat() {
  const messages = document.querySelectorAll('.message');
  if (messages.length === 0) { showToast('No messages to export', 'warning'); return; }

  let text = `NutriGuide Chat Export\n${'='.repeat(40)}\nExported: ${new Date().toLocaleString()}\n\n`;
  messages.forEach(msg => {
    const role = msg.classList.contains('message-user') ? 'You' : 'NutriGuide';
    const content = msg.querySelector('.msg-content')?.textContent?.trim() || '';
    const time = msg.querySelector('.msg-time')?.textContent?.trim() || '';
    text += `[${time}] ${role}:\n${content}\n\n`;
  });

  const blob = new Blob([text], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `nutriguide-chat-${new Date().toISOString().slice(0, 10)}.txt`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('Chat exported!', 'success');
}

// ── Voice Input (Web Speech API) ───────────────────────────────────
function setupVoiceRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const voiceBtn = document.getElementById('voiceBtn');

  if (!SpeechRecognition) {
    if (voiceBtn) {
      voiceBtn.title = 'Voice input not supported in this browser';
      voiceBtn.style.opacity = '0.4';
      voiceBtn.style.cursor = 'not-allowed';
    }
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = 'en-IN';

  recognition.onresult = (event) => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      transcript += event.results[i][0].transcript;
    }
    const input = document.getElementById('chatInput');
    if (input) {
      input.value = transcript;
      input.dispatchEvent(new Event('input'));
    }
  };

  recognition.onend = () => {
    voiceActive = false;
    updateVoiceUI(false);
    const input = document.getElementById('chatInput');
    if (input && input.value.trim()) {
      setTimeout(sendMessage, 300);
    }
  };

  recognition.onerror = (event) => {
    voiceActive = false;
    updateVoiceUI(false);
    if (event.error !== 'no-speech') {
      showToast(`Voice error: ${event.error}`, 'warning');
    }
  };
}

function toggleVoiceInput() {
  if (!recognition) {
    showToast('Voice input not supported in this browser', 'warning');
    return;
  }
  if (voiceActive) {
    stopVoiceInput();
  } else {
    startVoiceInput();
  }
}

function startVoiceInput() {
  if (!recognition) return;
  voiceActive = true;
  updateVoiceUI(true);
  recognition.start();
  showToast('Listening... speak now', 'info', 2000);
}

function stopVoiceInput() {
  if (recognition) recognition.stop();
  voiceActive = false;
  updateVoiceUI(false);
}

function updateVoiceUI(active) {
  const voiceStatus = document.getElementById('voiceStatus');
  const voiceBtn = document.getElementById('voiceBtn');
  const icon = voiceBtn?.querySelector('i');

  if (voiceStatus) voiceStatus.classList.toggle('d-none', !active);
  if (icon) {
    icon.className = active ? 'bi bi-mic-fill text-danger' : 'bi bi-mic';
  }
}

// ── Markdown renderer (uses global marked.js) ──────────────────────
function renderMarkdown(text) {
  if (typeof marked !== 'undefined') {
    return marked.parse(text, { breaks: true, gfm: true });
  }
  return escapeHtml(text).replace(/\n/g, '<br/>');
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(str));
  return d.innerHTML;
}

// ── Show Toast (fallback if main.js not loaded first) ─────────────
if (typeof showToast === 'undefined') {
  window.showToast = function(msg, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${msg}`);
  };
}
