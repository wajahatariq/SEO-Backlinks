/**
 * app.js — SEO Agent frontend
 * Handles tab switching, API calls, result rendering, and CSV export.
 */

const API_BASE = '';

// ── Tab Switching ─────────────────────────────────────────────────────────

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

// ── Helpers ───────────────────────────────────────────────────────────────

function esc(str) {
  if (typeof str !== 'string') return String(str ?? '');
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
            .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function fmt(n) {
  if (n == null) return '—';
  return Number(n).toLocaleString();
}

function priorityPill(p) {
  if (!p) return '';
  const map = { High: 'pill-red', Medium: 'pill-yellow', Low: 'pill-green' };
  return `<span class="pill ${map[p] || 'pill-gray'}">${esc(p)}</span>`;
}

function typePill(t) {
  return t ? `<span class="pill pill-blue">${esc(t)}</span>` : '';
}

function setLoading(btnId, spinId, labelId, on, label = null) {
  const btn = document.getElementById(btnId);
  const spin = btn.querySelector('.btn-spin');
  const lbl  = btn.querySelector('.btn-label');
  btn.disabled = on;
  spin.classList.toggle('hidden', !on);
  if (label) lbl.textContent = on ? 'Running…' : label;
}

function showError(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.classList.remove('hidden');
}

function clearError(id) {
  const el = document.getElementById(id);
  el.textContent = '';
  el.classList.add('hidden');
}

// ── CSV Export ────────────────────────────────────────────────────────────

function exportCSV(data, filename) {
  if (!data || !data.length) return;
  const headers = Object.keys(data[0]);
  const rows = data.map(row =>
    headers.map(h => {
      const val = String(row[h] ?? '').replace(/"/g, '""');
      return `"${val}"`;
    }).join(',')
  );
  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
}

// ── Pipeline Animation (Module 1) ─────────────────────────────────────────

let pipelineTimer = null;

function startPipeline() {
  const steps = ['pip-1','pip-2','pip-3'];
  steps.forEach(id => document.getElementById(id).className = 'pip-step');
  document.getElementById('pipeline-backlinks').classList.remove('hidden');
  document.getElementById('results-backlinks').classList.add('hidden');

  let i = 0;
  document.getElementById(steps[i]).classList.add('active');
  pipelineTimer = setInterval(() => {
    if (i < steps.length - 1) {
      document.getElementById(steps[i]).classList.replace('active','done');
      i++;
      document.getElementById(steps[i]).classList.add('active');
    }
  }, 3500);
}

function finishPipeline() {
  clearInterval(pipelineTimer);
  ['pip-1','pip-2','pip-3'].forEach(id => {
    const el = document.getElementById(id);
    el.classList.remove('active');
    el.classList.add('done');
  });
}

function resetPipeline() {
  clearInterval(pipelineTimer);
  document.getElementById('pipeline-backlinks').classList.add('hidden');
  ['pip-1','pip-2','pip-3'].forEach(id =>
    document.getElementById(id).className = 'pip-step'
  );
}

// ════════════════════════════════════════════════════════════════════════════
// MODULE 1 — Backlink Finder
// ════════════════════════════════════════════════════════════════════════════

document.getElementById('form-backlinks').addEventListener('submit', async e => {
  e.preventDefault();
  clearError('err-backlinks');

  const domain = document.getElementById('input-domain').value.trim();
  if (!domain) { showError('err-backlinks', 'Please enter a domain.'); return; }

  setLoading('btn-backlinks', null, null, true, 'Find Opportunities');
  resetPipeline();
  startPipeline();

  try {
    const res = await fetch(`${API_BASE}/api/find-links`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_domain: domain }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);

    finishPipeline();

    // Competitors
    document.getElementById('competitors-list').innerHTML =
      (data.competitors || []).map(c => `<span class="tag">${esc(c)}</span>`).join('');

    // Opportunities table
    const opps = data.opportunities || [];
    document.getElementById('count-backlinks').textContent = `${opps.length} found`;
    document.getElementById('tbody-backlinks').innerHTML = opps.length
      ? opps.map(o => `<tr>
          <td class="cell-domain"><a href="https://${esc(o.domain)}" target="_blank" rel="noopener">${esc(o.domain)}</a></td>
          <td class="cell-num">${fmt(o.rank)}</td>
          <td class="cell-num">${fmt(o.backlinks_num)}</td>
          <td><span class="pill pill-gray">${esc(o.source_competitor||'—')}</span></td>
          <td class="cell-muted">${esc(o.reason||'—')}</td>
        </tr>`).join('')
      : `<tr><td colspan="5" style="text-align:center;padding:28px;color:var(--text-3)">No opportunities found.</td></tr>`;

    const exportBtn = document.getElementById('export-backlinks');
    exportBtn.classList.remove('hidden');
    exportBtn.onclick = () => exportCSV(opps, `backlinks-${domain}.csv`);

    document.getElementById('results-backlinks').classList.remove('hidden');
    document.getElementById('results-backlinks').scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    resetPipeline();
    showError('err-backlinks', err.message);
  } finally {
    setLoading('btn-backlinks', null, null, false, 'Find Opportunities');
  }
});

// ════════════════════════════════════════════════════════════════════════════
// MODULE 2 — Niche Outreach Finder
// ════════════════════════════════════════════════════════════════════════════

document.getElementById('form-niche').addEventListener('submit', async e => {
  e.preventDefault();
  clearError('err-niche');

  const query    = document.getElementById('input-niche-query').value.trim();
  const location = document.getElementById('input-niche-location').value;
  if (!query) { showError('err-niche', 'Please enter a search query.'); return; }

  setLoading('btn-niche', null, null, true, 'Find Sites');

  try {
    const res = await fetch(`${API_BASE}/api/niche-finder`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, location }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);

    const sites = data.sites || [];
    document.getElementById('count-niche').textContent = `${sites.length} found`;

    document.getElementById('tbody-niche').innerHTML = sites.length
      ? sites.map(s => `<tr>
          <td class="cell-domain"><a href="${esc(s.url||'#')}" target="_blank" rel="noopener">${esc(s.domain||'—')}</a></td>
          <td class="cell-num">${fmt(s.da_estimate)}</td>
          <td>${typePill(s.type)}</td>
          <td>${s.dofollow ? '<span class="pill pill-green">Dofollow</span>' : '<span class="pill pill-gray">Nofollow</span>'}</td>
          <td class="cell-url"><a href="${esc(s.write_for_us_url||'#')}" target="_blank" rel="noopener">View Page</a></td>
          <td class="cell-muted">${s.contact_email ? `<a href="mailto:${esc(s.contact_email)}">${esc(s.contact_email)}</a>` : '—'}</td>
          <td class="cell-muted">${esc(s.reason||'—')}</td>
        </tr>`).join('')
      : `<tr><td colspan="7" style="text-align:center;padding:28px;color:var(--text-3)">No results found.</td></tr>`;

    const exportBtn = document.getElementById('export-niche');
    exportBtn.classList.remove('hidden');
    exportBtn.onclick = () => exportCSV(sites, `niche-outreach-${Date.now()}.csv`);

    document.getElementById('results-niche').classList.remove('hidden');
    document.getElementById('results-niche').scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    showError('err-niche', err.message);
  } finally {
    setLoading('btn-niche', null, null, false, 'Find Sites');
  }
});

// ════════════════════════════════════════════════════════════════════════════
// MODULE 3 — SERP Analyzer
// ════════════════════════════════════════════════════════════════════════════

document.getElementById('form-serp').addEventListener('submit', async e => {
  e.preventDefault();
  clearError('err-serp');

  const keyword = document.getElementById('input-keyword').value.trim();
  if (!keyword) { showError('err-serp', 'Please enter a keyword.'); return; }

  setLoading('btn-serp', null, null, true, 'Analyse SERP');

  try {
    const res = await fetch(`${API_BASE}/api/serp-analyzer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keyword }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);

    document.getElementById('serp-insights-text').textContent = data.insights || '';

    const comps = data.competitors || [];
    document.getElementById('tbody-serp').innerHTML = comps.length
      ? comps.map(c => `<tr>
          <td class="cell-num" style="font-weight:700;color:var(--text-1)">${c.rank||'—'}</td>
          <td class="cell-domain"><a href="${esc(c.url||'#')}" target="_blank" rel="noopener">${esc(c.domain||'—')}</a></td>
          <td class="cell-num">${fmt(c.da_estimate)}</td>
          <td>${typePill(c.content_type)}</td>
          <td class="cell-muted">${esc(c.why_ranking||'—')}</td>
          <td class="cell-url"><a href="${esc(c.url||'#')}" target="_blank" rel="noopener">Visit</a></td>
        </tr>`).join('')
      : `<tr><td colspan="6" style="text-align:center;padding:28px;color:var(--text-3)">No results.</td></tr>`;

    const exportBtn = document.getElementById('export-serp');
    exportBtn.classList.remove('hidden');
    exportBtn.onclick = () => exportCSV(comps, `serp-${keyword.replace(/\s+/g,'-')}.csv`);

    document.getElementById('results-serp').classList.remove('hidden');
    document.getElementById('results-serp').scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    showError('err-serp', err.message);
  } finally {
    setLoading('btn-serp', null, null, false, 'Analyse SERP');
  }
});

// ════════════════════════════════════════════════════════════════════════════
// MODULE 4 — Gap Analysis
// ════════════════════════════════════════════════════════════════════════════

document.getElementById('form-gap').addEventListener('submit', async e => {
  e.preventDefault();
  clearError('err-gap');

  const yourDomain = document.getElementById('input-your-domain').value.trim();
  const compDomain = document.getElementById('input-competitor-domain').value.trim();
  if (!yourDomain || !compDomain) {
    showError('err-gap', 'Please enter both domains.');
    return;
  }

  setLoading('btn-gap', null, null, true, 'Run Gap Analysis');

  try {
    const res = await fetch(`${API_BASE}/api/gap-analysis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ your_domain: yourDomain, competitor_domain: compDomain }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);

    // Authority Gap
    const ag = data.authority_gap || {};
    document.getElementById('authority-grid').innerHTML = `
      <div class="auth-stat">
        <div class="auth-stat-label">Your DA</div>
        <div class="auth-stat-value">${ag.your_estimated_da || '—'}</div>
        <div class="auth-stat-sub">${esc(yourDomain)}</div>
      </div>
      <div class="auth-stat">
        <div class="auth-stat-label">Competitor DA</div>
        <div class="auth-stat-value" style="color:#f87171">${ag.competitor_estimated_da || '—'}</div>
        <div class="auth-stat-sub">${esc(compDomain)}</div>
      </div>
      <div class="auth-stat">
        <div class="auth-stat-label">Links Needed</div>
        <div class="auth-stat-value" style="color:#fbbf24">${fmt(ag.links_needed)}</div>
        <div class="auth-stat-sub">to close the gap</div>
      </div>
      <div class="auth-stat" style="grid-column:1/-1">
        <div class="auth-stat-label">Summary</div>
        <div style="font-size:0.88rem;color:var(--text-2);margin-top:4px">${esc(ag.summary||'')}</div>
      </div>`;

    // Link Gaps
    const linkGaps = data.link_gaps || [];
    document.getElementById('tbody-link-gaps').innerHTML = linkGaps.length
      ? linkGaps.map(g => `<tr>
          <td class="cell-domain">${esc(g.domain||'—')}</td>
          <td class="cell-num">${fmt(g.da_estimate)}</td>
          <td>${typePill(g.type)}</td>
          <td class="cell-muted">${esc(g.how_to_get||'—')}</td>
        </tr>`).join('')
      : `<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--text-3)">No link gaps found.</td></tr>`;

    document.getElementById('export-link-gaps').classList.remove('hidden');
    document.getElementById('export-link-gaps').onclick = () => exportCSV(linkGaps, `link-gaps-${yourDomain}.csv`);

    // Content Gaps
    const contentGaps = data.content_gaps || [];
    document.getElementById('tbody-content-gaps').innerHTML = contentGaps.length
      ? contentGaps.map(g => `<tr>
          <td style="font-weight:600">${esc(g.topic||'—')}</td>
          <td>${typePill(g.content_type)}</td>
          <td>${priorityPill(g.priority)}</td>
          <td class="cell-muted">${esc(g.why_important||'—')}</td>
        </tr>`).join('')
      : `<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--text-3)">No content gaps found.</td></tr>`;

    document.getElementById('export-content-gaps').classList.remove('hidden');
    document.getElementById('export-content-gaps').onclick = () => exportCSV(contentGaps, `content-gaps-${yourDomain}.csv`);

    // Action Plan
    const plan = data.action_plan || [];
    document.getElementById('tbody-action-plan').innerHTML = plan.length
      ? plan.map(a => `<tr>
          <td style="font-weight:700;color:var(--accent);text-align:center">${a.step||'—'}</td>
          <td style="font-weight:500">${esc(a.action||'—')}</td>
          <td>${typePill(a.type)}</td>
          <td>${priorityPill(a.priority)}</td>
          <td><span class="pill pill-gray">${esc(a.timeline||'—')}</span></td>
        </tr>`).join('')
      : `<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--text-3)">No action plan generated.</td></tr>`;

    document.getElementById('export-action-plan').classList.remove('hidden');
    document.getElementById('export-action-plan').onclick = () => exportCSV(plan, `action-plan-${yourDomain}.csv`);

    document.getElementById('results-gap').classList.remove('hidden');
    document.getElementById('results-gap').scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    showError('err-gap', err.message);
  } finally {
    setLoading('btn-gap', null, null, false, 'Run Gap Analysis');
  }
});

// Auto-focus first input on load
document.getElementById('input-domain').focus();
