/* ============================================================
   Emotional Journaling Assistant — Frontend Logic
   ============================================================ */

const API = '';  // same-origin

// ── DOM refs ────────────────────────────────────────────────
const textarea     = document.getElementById('journalTextarea');
const charCount    = document.getElementById('charCount');
const btnSubmit    = document.getElementById('btnSubmit');
const resultPanel  = document.getElementById('resultPanel');
const highRiskBanner = document.getElementById('highRiskBanner');
const gaugeFill    = document.getElementById('gaugeFill');
const tempNumber   = document.getElementById('tempNumber');
const tempSummary  = document.getElementById('tempSummary');
const keywordChips = document.getElementById('keywordChips');
const insightText  = document.getElementById('insightText');
const reframeText  = document.getElementById('reframeText');
const habitText    = document.getElementById('habitText');
const historyList  = document.getElementById('historyList');
const statTotal    = document.getElementById('statTotal');
const statTemp     = document.getElementById('statTemp');
const statEmotion  = document.getElementById('statEmotion');
const toastContainer = document.getElementById('toastContainer');

// ── Textarea counter ─────────────────────────────────────────
textarea.addEventListener('input', () => {
  const len = textarea.value.length;
  charCount.textContent = len;
  btnSubmit.disabled = len < 10;
});

// ── Toast ─────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const t = document.createElement('div');
  t.className = `toast${type === 'error' ? ' error' : ''}`;
  t.textContent = msg;
  toastContainer.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Gauge animation ───────────────────────────────────────────
// Circle circumference for r=35: 2π×35 ≈ 219.9
const CIRC = 2 * Math.PI * 35;

function animateGauge(score) {
  const pct = Math.max(0, Math.min(score / 10, 1));
  const offset = CIRC * (1 - pct);

  // Color: cool blue (low) → rose (mid) → warm green (high)
  const hue = Math.round(pct * 120);  // 0=red, 120=green
  gaugeFill.style.stroke = `hsl(${hue}, 60%, 55%)`;
  gaugeFill.style.strokeDashoffset = offset;

  // Number counter
  let current = 0;
  const target = parseFloat(score.toFixed(1));
  const step = target / 30;
  const timer = setInterval(() => {
    current = Math.min(current + step, target);
    tempNumber.textContent = current.toFixed(1);
    if (current >= target) clearInterval(timer);
  }, 30);
}

// ── Render counseling result ──────────────────────────────────
function renderResult(data) {
  const c = data.counseling;
  const temp = c['오늘의 감정 온도'];
  const isHighRisk = c.is_high_risk;

  // High-risk
  highRiskBanner.style.display = isHighRisk ? 'flex' : 'none';

  // Gauge
  animateGauge(temp.score);
  tempSummary.textContent = temp.summary;

  // Keywords
  keywordChips.innerHTML = temp.keywords
    .map(kw => `<span class="keyword-chip">${kw}</span>`)
    .join('');

  // Counseling cards — render markdown-like bold
  function renderMd(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  }

  insightText.innerHTML = renderMd(c['마음 들여다보기']);
  reframeText.innerHTML = renderMd(c['빛나는 관점']);
  habitText.innerHTML   = renderMd(c['작은 발걸음']);

  // Show result
  resultPanel.classList.add('visible');
  resultPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Submit journal ────────────────────────────────────────────
btnSubmit.addEventListener('click', async () => {
  const content = textarea.value.trim();
  if (content.length < 10) return;

  btnSubmit.classList.add('loading');
  btnSubmit.disabled = true;

  try {
    const res = await fetch(`${API}/journals/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
    const json = await res.json();

    renderResult(json.data);
    textarea.value = '';
    charCount.textContent = '0';
    showToast('일기가 저장되었어요 🌿');

    // Refresh sidebar
    loadHistory();
    loadStats();
  } catch (err) {
    showToast(err.message || '오류가 발생했어요. 잠시 후 다시 시도해 주세요.', 'error');
  } finally {
    btnSubmit.classList.remove('loading');
    btnSubmit.disabled = false;
  }
});

// ── Load history ──────────────────────────────────────────────
async function loadHistory() {
  try {
    const res = await fetch(`${API}/journals/?limit=20`);
    const list = await res.json();

    if (!list.length) {
      historyList.innerHTML = `
        <div class="empty-state" style="padding:30px 0">
          <div class="empty-icon">📖</div>
          <p>아직 작성된 일기가 없어요</p>
        </div>`;
      return;
    }

    historyList.innerHTML = list.map(item => {
      const date = new Date(item.created_at).toLocaleDateString('ko-KR', {
        month: 'short', day: 'numeric', weekday: 'short'
      });
      const temp = item.emotion_temperature != null
        ? `🌡 ${item.emotion_temperature.toFixed(1)}`
        : '';
      const emotion = item.primary_emotion || '';
      return `
        <div class="history-item" data-id="${item.id}">
          <div class="h-date">${date} &nbsp; ${temp}</div>
          <div class="h-emotion">${emotion}</div>
          <div class="h-preview">${item.content_preview}</div>
        </div>`;
    }).join('');

    // Click to load detail
    historyList.querySelectorAll('.history-item').forEach(el => {
      el.addEventListener('click', () => loadJournal(el.dataset.id, el));
    });
  } catch (e) {
    // silent
  }
}

// ── Load journal detail ───────────────────────────────────────
async function loadJournal(id, el) {
  historyList.querySelectorAll('.history-item').forEach(i => i.classList.remove('active'));
  if (el) el.classList.add('active');

  try {
    const res = await fetch(`${API}/journals/${id}`);
    const data = await res.json();
    if (!data.counseling) return;

    textarea.value = data.content;
    charCount.textContent = data.content.length;
    renderResult(data);
  } catch (e) {
    showToast('일기를 불러오는 데 실패했어요.', 'error');
  }
}

// ── Load stats ────────────────────────────────────────────────
async function loadStats() {
  try {
    const res = await fetch(`${API}/analysis/stats`);
    const s = await res.json();
    if (s.message) return; // empty

    statTotal.textContent   = s.total_journals;
    statTemp.innerHTML      = `${s.average_emotion_temperature}<span class="unit"> / 10</span>`;
    statEmotion.textContent = s.most_frequent_emotion;
  } catch (e) {
    // silent
  }
}

// ── Init ──────────────────────────────────────────────────────
(function init() {
  // Init gauge stroke-dasharray
  gaugeFill.style.strokeDasharray = CIRC;
  gaugeFill.style.strokeDashoffset = CIRC;

  loadHistory();
  loadStats();
})();
