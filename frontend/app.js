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

// ════════════════════════════════════════════════════════════════════════════
// MODULE 6 — Comprehensive Backlink Search
// ════════════════════════════════════════════════════════════════════════════

const REL_COLOR = { High: 'pill-green', Medium: 'pill-yellow', Low: 'pill-gray' };
const SEARCH_PAGE = 100;

let searchAllResults  = [];
let searchActiveRel   = 'all';
let searchCurrentPage = 1;

function searchFiltered() {
  if (searchActiveRel === 'all') return searchAllResults;
  return searchAllResults.filter(r => r.relevance === searchActiveRel);
}

function renderSearchTable() {
  const filtered = searchFiltered();
  const total    = filtered.length;
  const start    = (searchCurrentPage - 1) * SEARCH_PAGE;
  const page     = filtered.slice(start, start + SEARCH_PAGE);

  document.getElementById('count-search').textContent =
    searchActiveRel === 'all' ? `${total} total` : `${total} in filter`;

  document.getElementById('tbody-search').innerHTML = page.length
    ? page.map((r, i) => `<tr>
        <td class="cell-num" style="color:var(--text-3)">${start + i + 1}</td>
        <td class="cell-domain"><a href="${esc(r.url || '#')}" target="_blank" rel="noopener">${esc(r.domain || '—')}</a></td>
        <td class="cell-num">${r.da_estimate ? fmt(r.da_estimate) : '—'}</td>
        <td>${typePill(r.type)}</td>
        <td><span class="pill ${REL_COLOR[r.relevance] || 'pill-gray'}">${esc(r.relevance || '—')}</span></td>
        <td class="cell-muted">${esc(r.how_to_get || '—')}</td>
        <td class="cell-url"><a href="${esc(r.url || '#')}" target="_blank" rel="noopener">Visit</a></td>
      </tr>`).join('')
    : `<tr><td colspan="7" style="text-align:center;padding:28px;color:var(--text-3)">No results in this filter.</td></tr>`;

  renderSearchPagination(total);
}

function renderSearchPagination(total) {
  const pages = Math.ceil(total / SEARCH_PAGE);
  const pag   = document.getElementById('search-pagination');
  if (pages <= 1) { pag.classList.add('hidden'); return; }
  pag.classList.remove('hidden');
  pag.innerHTML = `
    <button class="pag-btn" id="sp-prev" ${searchCurrentPage === 1 ? 'disabled' : ''}>← Prev</button>
    <span class="pag-info">Page ${searchCurrentPage} of ${pages} &nbsp;·&nbsp; ${total} items</span>
    <button class="pag-btn" id="sp-next" ${searchCurrentPage >= pages ? 'disabled' : ''}>Next →</button>`;
  document.getElementById('sp-prev').onclick = () => { if (searchCurrentPage > 1) { searchCurrentPage--; renderSearchTable(); } };
  document.getElementById('sp-next').onclick = () => { if (searchCurrentPage < pages) { searchCurrentPage++; renderSearchTable(); } };
}

// Relevance filter buttons
document.getElementById('search-filters').addEventListener('click', e => {
  const btn = e.target.closest('.cat-filter-btn');
  if (!btn) return;
  document.querySelectorAll('#search-filters .cat-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  searchActiveRel   = btn.dataset.rel;
  searchCurrentPage = 1;
  renderSearchTable();
});

document.getElementById('form-search').addEventListener('submit', async e => {
  e.preventDefault();
  clearError('err-search');

  const query = document.getElementById('input-search-query').value.trim();
  if (!query) { showError('err-search', 'Please enter a search query.'); return; }

  setLoading('btn-search', null, null, true, 'Search Backlinks');
  document.getElementById('results-search').classList.add('hidden');

  // Show progress bar
  const prog = document.getElementById('search-progress');
  prog.classList.remove('hidden');
  document.getElementById('search-status').textContent  = 'Running 45 searches across all angles…';
  document.getElementById('search-counter').textContent = '';
  document.getElementById('search-detail').textContent  = 'Generating query set → searching concurrently → extracting list pages → enriching results…';
  document.getElementById('search-bar').classList.add('indeterminate');

  searchAllResults  = [];
  searchActiveRel   = 'all';
  searchCurrentPage = 1;
  document.querySelectorAll('#search-filters .cat-filter-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('#search-filters .cat-filter-btn[data-rel="all"]').classList.add('active');

  try {
    const res = await fetch(`${API_BASE}/api/backlink-search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);

    searchAllResults = data.results || [];

    document.getElementById('search-status').textContent  = `Complete — ${searchAllResults.length} unique backlinks found`;
    document.getElementById('search-bar').classList.remove('indeterminate');
    document.getElementById('search-bar').style.width = '100%';
    document.getElementById('search-detail').textContent  = `Sorted by relevance and DA. Use filters or export all as CSV.`;

    const exportBtn = document.getElementById('export-search');
    exportBtn.classList.remove('hidden');
    exportBtn.onclick = () => exportCSV(searchAllResults, `backlink-search-${query.replace(/\s+/g, '-')}.csv`);

    renderSearchTable();
    document.getElementById('results-search').classList.remove('hidden');
    document.getElementById('results-search').scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    prog.classList.add('hidden');
    showError('err-search', err.message);
  } finally {
    setLoading('btn-search', null, null, false, 'Search Backlinks');
  }
});

// ════════════════════════════════════════════════════════════════════════════
// MODULE 5 — PDF Backlink Classifier
// ════════════════════════════════════════════════════════════════════════════

const CAT_COLORS = {
  'Guest Post':         'pill-blue',
  'Profile Creation':   'pill-purple',
  'Business Directory': 'pill-green',
  'Forum/Comment':      'pill-yellow',
  'Web 2.0':            'pill-orange',
};

function catPill(cat) {
  const cls = CAT_COLORS[cat] || 'pill-gray';
  return `<span class="pill ${cls}">${esc(cat)}</span>`;
}

function confPill(conf) {
  const map = { High: 'pill-green', Medium: 'pill-yellow', Low: 'pill-gray' };
  return `<span class="pill ${map[conf] || 'pill-gray'}">${esc(conf || '—')}</span>`;
}

// ── State ─────────────────────────────────────────────────────────────────
let pdfAllResults  = [];
let pdfActiveCat   = 'all';
let pdfCurrentPage = 1;
const PDF_PAGE     = 100;

function pdfFiltered() {
  if (pdfActiveCat === 'all') return pdfAllResults;
  return pdfAllResults.filter(r => r.category === pdfActiveCat);
}

function renderPdfTable() {
  const filtered = pdfFiltered();
  const total    = filtered.length;
  const start    = (pdfCurrentPage - 1) * PDF_PAGE;
  const page     = filtered.slice(start, start + PDF_PAGE);
  const offset   = start;

  document.getElementById('pdf-count').textContent =
    pdfActiveCat === 'all' ? `${total} total` : `${total} in category`;

  document.getElementById('tbody-pdf').innerHTML = page.length
    ? page.map((r, i) => `<tr>
        <td class="cell-num" style="color:var(--text-3)">${offset + i + 1}</td>
        <td class="cell-domain">${esc(r.domain || r.url || '—')}</td>
        <td>${catPill(r.category)}</td>
        <td>${confPill(r.confidence)}</td>
        <td class="cell-url"><a href="${esc(r.url || '#')}" target="_blank" rel="noopener" title="${esc(r.url || '')}">
          ${esc((r.url || '').length > 55 ? r.url.slice(0, 55) + '…' : r.url || '—')}
        </a></td>
      </tr>`).join('')
    : `<tr><td colspan="5" style="text-align:center;padding:28px;color:var(--text-3)">No results in this category.</td></tr>`;

  renderPdfPagination(total);
}

function renderPdfPagination(total) {
  const pages = Math.ceil(total / PDF_PAGE);
  const pag   = document.getElementById('pdf-pagination');
  if (pages <= 1) { pag.classList.add('hidden'); return; }

  pag.classList.remove('hidden');
  pag.innerHTML = `
    <button class="pag-btn" id="pag-prev" ${pdfCurrentPage === 1 ? 'disabled' : ''}>← Prev</button>
    <span class="pag-info">Page ${pdfCurrentPage} of ${pages} &nbsp;·&nbsp; ${total} items</span>
    <button class="pag-btn" id="pag-next" ${pdfCurrentPage >= pages ? 'disabled' : ''}>Next →</button>`;

  document.getElementById('pag-prev').onclick = () => {
    if (pdfCurrentPage > 1) { pdfCurrentPage--; renderPdfTable(); }
  };
  document.getElementById('pag-next').onclick = () => {
    if (pdfCurrentPage < pages) { pdfCurrentPage++; renderPdfTable(); }
  };
}

// ── Category filter buttons ───────────────────────────────────────────────
document.getElementById('cat-filters').addEventListener('click', e => {
  const btn = e.target.closest('.cat-filter-btn');
  if (!btn) return;
  document.querySelectorAll('.cat-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  pdfActiveCat   = btn.dataset.cat;
  pdfCurrentPage = 1;
  renderPdfTable();
});

// ── Upload zone ───────────────────────────────────────────────────────────
let selectedPdf = null;

function handleFileSelect(file) {
  if (!file || file.type !== 'application/pdf') {
    showError('err-pdf', 'Please select a valid PDF file.');
    return;
  }
  selectedPdf = file;
  document.getElementById('selected-filename').textContent = file.name;
  document.getElementById('selected-file').classList.remove('hidden');
  document.getElementById('btn-classify').disabled = false;
  clearError('err-pdf');
}

const uploadZone  = document.getElementById('upload-zone');
const pdfInput    = document.getElementById('input-pdf');

document.getElementById('browse-btn').addEventListener('click', e => {
  e.stopPropagation();
  pdfInput.click();
});
uploadZone.addEventListener('click', () => pdfInput.click());
pdfInput.addEventListener('change', () => {
  if (pdfInput.files[0]) handleFileSelect(pdfInput.files[0]);
});

uploadZone.addEventListener('dragover', e => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) { pdfInput.files = e.dataTransfer.files; handleFileSelect(f); }
});

// ── Progress helpers ──────────────────────────────────────────────────────
function showProgress(status, counter, detail, pct) {
  const sec = document.getElementById('pdf-progress');
  sec.classList.remove('hidden');
  document.getElementById('pdf-status').textContent  = status;
  document.getElementById('pdf-counter').textContent = counter;
  document.getElementById('pdf-detail').textContent  = detail;
  const bar = document.getElementById('pdf-bar');
  if (pct == null) {
    bar.classList.add('indeterminate');
    bar.style.width = '30%';
  } else {
    bar.classList.remove('indeterminate');
    bar.style.width = `${Math.min(100, Math.max(2, pct))}%`;
  }
}

// ── Main classify handler ─────────────────────────────────────────────────
document.getElementById('btn-classify').addEventListener('click', async () => {
  if (!selectedPdf) return;
  clearError('err-pdf');

  const btn = document.getElementById('btn-classify');
  btn.disabled = true;
  btn.querySelector('.btn-spin').classList.remove('hidden');
  btn.querySelector('.btn-label').textContent = 'Processing…';

  document.getElementById('results-pdf').classList.add('hidden');
  document.getElementById('pdf-progress').classList.remove('hidden');
  showProgress('Extracting URLs from PDF…', '', 'Reading pages…', null);

  pdfAllResults  = [];
  pdfActiveCat   = 'all';
  pdfCurrentPage = 1;

  // Reset category filters
  document.querySelectorAll('.cat-filter-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('.cat-filter-btn[data-cat="all"]').classList.add('active');

  try {
    const formData = new FormData();
    formData.append('file', selectedPdf);

    const response = await fetch(`${API_BASE}/api/classify-pdf`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }

    const reader  = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer    = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete trailing line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        let evt;
        try { evt = JSON.parse(line.slice(6)); } catch { continue; }

        if (evt.type === 'error') {
          throw new Error(evt.message);

        } else if (evt.type === 'start') {
          const ruleInfo = evt.rule_classified > 0
            ? ` · ${evt.rule_classified} instant · ${evt.llm_needed} via AI`
            : '';
          showProgress(
            'AI is working…',
            `0 / ${evt.chunks} chunks`,
            `Found ${evt.total} unique URLs${ruleInfo}`,
            evt.chunks === 0 ? 98 : 2,
          );

        } else if (evt.type === 'progress') {
          const pct = Math.round((evt.chunk / evt.total_chunks) * 100);
          showProgress(
            'AI is working…',
            `Chunk ${evt.chunk} / ${evt.total_chunks}`,
            `Classified ${evt.processed} / ${evt.total_llm} URLs via AI`,
            pct,
          );

        } else if (evt.type === 'done') {
          pdfAllResults = evt.results || [];
          showProgress('Complete!', '', `${pdfAllResults.length} URLs classified`, 100);

          // Summary cards
          const summary = evt.summary || {};
          const catColors = {
            'Guest Post': '#6c63ff', 'Profile Creation': '#c4b5fd',
            'Business Directory': '#4ade80', 'Forum/Comment': '#fbbf24', 'Web 2.0': '#fb923c',
          };
          document.getElementById('cat-summary').innerHTML =
            Object.entries(summary)
              .filter(([k]) => k !== 'total')
              .map(([cat, count]) => `
                <div class="cat-stat">
                  <div class="cat-stat-label">${esc(cat)}</div>
                  <div class="cat-stat-value" style="color:${catColors[cat]||'var(--accent)'}">
                    ${count}
                  </div>
                </div>`).join('');

          renderPdfTable();

          const exportBtn = document.getElementById('export-pdf');
          exportBtn.classList.remove('hidden');
          exportBtn.onclick = () => exportCSV(pdfAllResults, `backlinks-classified-${Date.now()}.csv`);

          document.getElementById('results-pdf').classList.remove('hidden');
          document.getElementById('results-pdf').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    }

  } catch (err) {
    document.getElementById('pdf-progress').classList.add('hidden');
    showError('err-pdf', err.message);
  } finally {
    btn.disabled = false;
    btn.querySelector('.btn-spin').classList.add('hidden');
    btn.querySelector('.btn-label').textContent = 'Classify Backlinks';
  }
});
