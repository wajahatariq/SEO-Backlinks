/**
 * app.js — SEO Backlink Opportunity Agent frontend
 *
 * Calls POST /api/find-links, animates the pipeline steps,
 * and renders competitors + opportunities into the UI.
 */

const API_BASE = '';

// ── DOM refs ──────────────────────────────────────────────────────────────
const form          = document.getElementById('search-form');
const domainInput   = document.getElementById('domain-input');
const submitBtn     = document.getElementById('submit-btn');
const btnText       = submitBtn.querySelector('.btn-text');
const btnSpinner    = submitBtn.querySelector('.btn-spinner');
const errorMsg      = document.getElementById('error-msg');
const pipelineEl    = document.getElementById('pipeline-status');
const resultsEl     = document.getElementById('results');
const competitorEl  = document.getElementById('competitors-list');
const oppTbody      = document.getElementById('opp-tbody');
const oppCount      = document.getElementById('opp-count');
const steps         = [
  document.getElementById('step-1'),
  document.getElementById('step-2'),
  document.getElementById('step-3'),
];

// ── State ─────────────────────────────────────────────────────────────────
let pipelineTimer = null;

// ── Helpers ───────────────────────────────────────────────────────────────

function setLoading(on) {
  submitBtn.disabled = on;
  btnText.textContent = on ? 'Running…' : 'Find Opportunities';
  btnSpinner.classList.toggle('hidden', !on);
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.classList.remove('hidden');
}

function clearError() {
  errorMsg.textContent = '';
  errorMsg.classList.add('hidden');
}

function resetPipeline() {
  steps.forEach(s => s.classList.remove('active', 'done'));
  pipelineEl.classList.add('hidden');
  clearInterval(pipelineTimer);
}

/**
 * Animate the three pipeline steps while the API call is in flight.
 * Each step lights up for ~3 s then marks as done before the next activates.
 */
function animatePipeline() {
  pipelineEl.classList.remove('hidden');
  resultsEl.classList.add('hidden');

  let current = 0;
  steps[current].classList.add('active');

  pipelineTimer = setInterval(() => {
    if (current < steps.length - 1) {
      steps[current].classList.remove('active');
      steps[current].classList.add('done');
      current++;
      steps[current].classList.add('active');
    }
  }, 3500);
}

function finishPipeline() {
  clearInterval(pipelineTimer);
  steps.forEach(s => { s.classList.remove('active'); s.classList.add('done'); });
}

function formatNumber(n) {
  if (n == null) return '—';
  return Number(n).toLocaleString();
}

// ── Render results ────────────────────────────────────────────────────────

function renderCompetitors(competitors) {
  competitorEl.innerHTML = competitors.map(c => `
    <span class="tag">${escapeHtml(c)}</span>
  `).join('');
}

function renderOpportunities(opportunities) {
  oppCount.textContent = `${opportunities.length} found`;

  if (opportunities.length === 0) {
    oppTbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align:center;padding:32px;color:var(--text-3)">
          No opportunities found. Try a different domain.
        </td>
      </tr>`;
    return;
  }

  oppTbody.innerHTML = opportunities.map(opp => `
    <tr>
      <td class="domain-cell">
        <a href="https://${escapeHtml(opp.domain)}" target="_blank" rel="noopener noreferrer">
          ${escapeHtml(opp.domain)}
        </a>
      </td>
      <td class="rank-cell">${formatNumber(opp.rank)}</td>
      <td class="backlinks-cell">${formatNumber(opp.backlinks_num)}</td>
      <td><span class="competitor-tag">${escapeHtml(opp.source_competitor ?? '—')}</span></td>
      <td class="reason-cell">${escapeHtml(opp.reason ?? '—')}</td>
    </tr>
  `).join('');
}

function escapeHtml(str) {
  if (typeof str !== 'string') return String(str ?? '');
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ── Main submit handler ───────────────────────────────────────────────────

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearError();

  const domain = domainInput.value.trim();
  if (!domain) {
    showError('Please enter a domain name.');
    return;
  }

  setLoading(true);
  resetPipeline();
  animatePipeline();

  try {
    const res = await fetch(`${API_BASE}/api/find-links`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_domain: domain }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail ?? `Server error: ${res.status}`);
    }

    finishPipeline();

    renderCompetitors(data.competitors ?? []);
    renderOpportunities(data.opportunities ?? []);
    resultsEl.classList.remove('hidden');

    // Smooth scroll to results
    resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    resetPipeline();
    showError(err.message || 'Something went wrong. Is the backend running?');
  } finally {
    setLoading(false);
  }
});

// Focus input on load
domainInput.focus();
