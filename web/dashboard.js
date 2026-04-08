// Bee Pagoda Benchmark — Dashboard JS
// Implements UI spec data mapping (UI_MVP_SPEC.md §5).
// No fabricated metrics: every displayed value maps to a JSON path.
// Missing/null values render as "N/A".

'use strict';

// ── Tab management ─────────────────────────────────────────────────────────
function showTab(id) {
  document.querySelectorAll('.tab').forEach(t => { t.style.display = 'none'; });
  const el = document.getElementById(id);
  if (el) el.style.display = 'block';
}

// ── Utilities ──────────────────────────────────────────────────────────────
function na(v, unit) {
  if (v === null || v === undefined || v === '' || v === 'null') return 'N/A';
  return unit ? `${v} ${unit}` : String(v);
}

function statusChip(status) {
  const s = (status || 'unknown').toLowerCase();
  const map = {
    ok: 'chip-ok', degraded: 'chip-degraded', skipped: 'chip-skipped',
    failed: 'chip-failed', missing: 'chip-missing', pending: 'chip-pending',
    running: 'chip-running',
  };
  return `<span class="status-chip ${map[s] || 'chip-missing'}">${s}</span>`;
}

function bandClass(band) {
  const map = { excellent: 'band-excellent', good: 'band-good', fair: 'band-fair', poor: 'band-poor' };
  return map[(band || '').toLowerCase()] || 'band-unknown';
}

const CAT_LABELS = {
  cpu: 'CPU', gpu_compute: 'GPU Compute', gpu_game: 'Gaming/Graphics',
  ai: 'AI', memory: 'Memory', disk: 'Storage', stress: 'Stress',
};

// ── Command preview (Launcher) ─────────────────────────────────────────────
function updateCmdPreview() {
  const profile = document.getElementById('sel-profile').value;
  const cats = [...document.querySelectorAll('#cat-checkboxes input:checked')].map(i => i.value).join(',');
  const skipPre = document.getElementById('chk-skip-preflight').checked;
  const runner = document.getElementById('inp-runner-path').value.trim() || './run_suite.sh';
  let cmd = `${runner} ${profile}`;
  if (cats) cmd += ` --categories ${cats}`;
  if (skipPre) cmd += ' --skip-preflight';
  document.getElementById('cmd-preview').textContent = cmd;
}

document.addEventListener('DOMContentLoaded', () => {
  ['sel-profile', 'chk-skip-preflight', 'inp-runner-path'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', updateCmdPreview);
  });
  document.querySelectorAll('#cat-checkboxes input').forEach(el => {
    el.addEventListener('change', updateCmdPreview);
  });
  updateCmdPreview();
  showTab('tab-launcher');
});

// ── Launcher ───────────────────────────────────────────────────────────────
let _pollInterval = null;
let _runStartTime = null;
let _elapsedTimer = null;
let _currentRunDir = null;

function launchRun() {
  const profile = document.getElementById('sel-profile').value;
  const cats = [...document.querySelectorAll('#cat-checkboxes input:checked')].map(i => i.value);
  if (!cats.length) { alert('Select at least one category.'); return; }

  const statusEl = document.getElementById('launch-status');
  statusEl.textContent = 'Starting…';

  // Build running-tab cards for the selected categories
  _initRunningCards(cats.flatMap(c => c === 'gpu' ? ['gpu_compute', 'gpu_game'] : [c]));
  showTab('tab-running');
  _setRunStatus('running');
  _runStartTime = Date.now();
  _startElapsedTimer();

  // Attempt to call the backend launcher (works when served from a local http server
  // that proxies run_suite.sh via /api/run).  Falls back to advisory message.
  const skipPre = document.getElementById('chk-skip-preflight').checked;
  fetch('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile, categories: cats.join(','), skip_preflight: skipPre }),
  }).then(r => r.json()).then(data => {
    _currentRunDir = data.run_dir || null;
    statusEl.textContent = `Run started. dir: ${_currentRunDir || 'unknown'}`;
    _startPolling();
  }).catch(() => {
    statusEl.textContent = 'ℹ️ No /api/run endpoint — run the command in a terminal.';
    _logAppend('No backend API found. Run the command shown in the Launcher tab in a terminal,\n' +
               'then open the generated summary.json in the Results tab.');
  });
}

function _startElapsedTimer() {
  clearInterval(_elapsedTimer);
  _elapsedTimer = setInterval(() => {
    if (!_runStartTime) return;
    const s = Math.floor((Date.now() - _runStartTime) / 1000);
    const m = Math.floor(s / 60), sec = s % 60;
    document.getElementById('run-elapsed').textContent = `Elapsed: ${m}:${String(sec).padStart(2,'0')}`;
  }, 1000);
}

function _setRunStatus(status) {
  document.getElementById('run-status-chip').innerHTML = statusChip(status);
}

function _logAppend(text) {
  const panel = document.getElementById('log-panel');
  panel.textContent += text + '\n';
  panel.scrollTop = panel.scrollHeight;
}

function _initRunningCards(cats) {
  const grid = document.getElementById('running-cards');
  grid.innerHTML = cats.map(cat => `
    <div class="domain-card" data-cat="${cat}" id="rcard-${cat}">
      <h3>${CAT_LABELS[cat] || cat}</h3>
      <div>${statusChip('pending')}</div>
      <div class="metric">—</div>
      <div class="metric-label">—</div>
    </div>
  `).join('');
}

function _updateRunningCard(cat, result) {
  const card = document.getElementById(`rcard-${cat}`);
  if (!card) return;
  const status = result.status || 'unknown';
  const score = result.score;
  const label = result.primary_metric || '';
  const notes = result.notes || '';
  card.innerHTML = `
    <h3>${CAT_LABELS[cat] || cat}</h3>
    <div>${statusChip(status)}</div>
    <div class="metric">${na(score)}</div>
    <div class="metric-label">${label || '—'}</div>
    ${notes ? `<div class="notes">${notes.split(';').slice(0, 2).join('; ')}</div>` : ''}
  `;
}

function _startPolling() {
  clearInterval(_pollInterval);
  _pollInterval = setInterval(() => {
    if (!_currentRunDir) return;
    fetch(`/api/status?run_dir=${encodeURIComponent(_currentRunDir)}`)
      .then(r => r.json())
      .then(data => {
        if (data.log) _logAppend(data.log);
        (data.results || []).forEach(r => _updateRunningCard(r.category, r));
        if (data.done) {
          clearInterval(_pollInterval);
          clearInterval(_elapsedTimer);
          _setRunStatus(data.exit_code === 0 ? 'ok' : 'failed');
          if (data.summary_path) {
            _logAppend(`\n✅ Run complete. Summary: ${data.summary_path}`);
            fetch(data.summary_path).then(r => r.json()).then(renderResults);
          }
        }
      }).catch(() => {});
  }, 2000);
}

// ── Results viewer ─────────────────────────────────────────────────────────
function loadFromFile(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    try {
      const data = JSON.parse(e.target.result);
      renderResults(data);
      showTab('tab-results');
    } catch (err) {
      alert('Invalid JSON: ' + err.message);
    }
  };
  reader.readAsText(file);
}

async function loadFromPath(path) {
  try {
    const res = await fetch(path);
    if (!res.ok) return null;
    return await res.json();
  } catch { return null; }
}

function renderResults(data) {
  if (!data) return;

  // Show meta card
  document.getElementById('results-meta').style.display = 'none';
  document.getElementById('results-run-meta').style.display = '';

  // Run metadata table (UI spec §5 Header block)
  const metaRows = [
    ['Profile', na(data.profile)],
    ['Generated at (UTC)', na(data.generated_at)],
    ['Run directory', na(data.run_dir)],
    ['Selected categories', na((data.selected_categories || []).join(', '))],
    ['Suite interpreter', na(data.suite_interpreter)],
  ];
  document.getElementById('run-meta-table').innerHTML = metaRows
    .map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('');

  // Export links
  const runDir = data.run_dir || '';
  const exports = [
    ['summary.md', `${runDir}/report/summary.md`],
    ['summary.json', `${runDir}/report/summary.json`],
    ['summary.csv', `${runDir}/report/summary.csv`],
  ];
  document.getElementById('export-links').innerHTML = exports
    .map(([label, path]) => `<a class="export-link" href="${path}" target="_blank">📄 ${label}</a>`).join('');

  // Environment fingerprint
  const fp = data.env_fingerprint;
  if (fp) {
    document.getElementById('results-env').style.display = '';
    const fpRows = [
      ['Kernel', fp.kernel], ['Distro', fp.distro], ['CPU', fp.cpu_model],
      ['RAM', fp.ram_mib ? `${fp.ram_mib} MiB` : null],
      ['GPU', fp.gpu_model], ['GPU Driver', fp.gpu_driver],
      ['GPU API', fp.gpu_api], ['Power Governor', fp.power_governor],
    ];
    document.getElementById('env-table').innerHTML = fpRows
      .map(([k, v]) => `<tr><td>${k}</td><td>${na(v)}</td></tr>`).join('');
  }

  // Preflight (UI spec §5 Preflight block)
  const pf = data.preflight;
  if (pf) {
    document.getElementById('results-preflight').style.display = '';
    const counts = pf.status_counts || {};
    document.getElementById('preflight-summary').innerHTML = `
      <p>${statusChip(pf.status)}
        &nbsp; present: <strong>${counts.present || 0}</strong>
        &nbsp; missing: <strong class="preflight-missing">${counts.missing || 0}</strong>
        &nbsp; optional-missing: <strong class="preflight-optional-missing">${counts['optional-missing'] || 0}</strong>
        &nbsp; version-mismatch: <strong>${counts['version-mismatch'] || 0}</strong>
      </p>
      ${pf.notes ? `<p style="color:#94a3b8;font-size:0.82rem">${pf.notes}</p>` : ''}
    `;
    const checks = pf.checks || [];
    if (checks.length) {
      document.getElementById('preflight-table').style.display = '';
      document.getElementById('preflight-tbody').innerHTML = checks.map(c => {
        const cls = c.status === 'present' ? 'preflight-present'
          : c.status === 'missing' ? 'preflight-missing'
          : c.status === 'optional-missing' ? 'preflight-optional-missing' : '';
        return `<tr>
          <td>${c.name || ''}</td>
          <td>${c.type || ''}</td>
          <td>${c.required ? 'yes' : 'no'}</td>
          <td class="${cls}">${c.status || ''}</td>
          <td>${na(c.version)}</td>
          <td style="font-size:0.75rem">${na(c.path)}</td>
          <td style="font-size:0.75rem">${na(c.notes)}</td>
        </tr>`;
      }).join('');
    }
  }

  // Domain cards (UI spec §5 domain result blocks)
  const results = data.results || {};
  const cats = data.selected_categories || Object.keys(results);
  const grid = document.getElementById('results-domain-cards');
  grid.innerHTML = '';

  cats.forEach(cat => {
    const r = results[cat] || { status: 'missing' };
    grid.insertAdjacentHTML('beforeend', renderDomainCard(cat, r));
  });

  // AI drilldown
  const ai = results.ai || {};
  const backendResults = ai.backend_results || [];
  if (backendResults.length) {
    document.getElementById('results-ai-detail').style.display = '';
    document.getElementById('ai-backend-tbody').innerHTML = backendResults.map(br => {
      const ds = br.data_source || (br.backend === 'llama.cpp' ? 'real_model' : 'synthetic_proxy');
      return `<tr>
        <td>${br.backend || ''}</td>
        <td>${statusChip(br.status)}</td>
        <td style="color:${ds === 'real_model' ? '#4ade80' : '#facc15'}">${ds}</td>
        <td>${na(br.score)}</td>
        <td>${na(br.prompt_tps)}</td>
        <td>${na(br.eval_tps)}</td>
        <td style="font-size:0.75rem;max-width:160px;overflow:hidden;text-overflow:ellipsis">${na(br.model)}</td>
        <td style="font-size:0.72rem">${na(br.notes)}</td>
      </tr>`;
    }).join('');
    const formula = (ai.composite || {}).formula;
    document.getElementById('ai-formula').textContent = formula ? `Formula: ${formula}` : '';
  }

  // Normalized metrics + health bands
  const norm = (data.normalized || {}).metrics;
  if (norm) {
    document.getElementById('results-normalized').style.display = '';
    let rows = '';
    Object.entries(norm).forEach(([cat, metrics]) => {
      Object.entries(metrics).forEach(([key, val]) => {
        if (key === 'status' || key.endsWith('_band')) return;
        const band = metrics[`${key}_band`] || 'unknown';
        const bc = bandClass(band);
        rows += `<tr>
          <td>${CAT_LABELS[cat] || cat}</td>
          <td>${key}</td>
          <td>${val !== null && val !== undefined ? val : 'N/A'}</td>
          <td class="${bc}">${band}</td>
        </tr>`;
      });
    });
    document.getElementById('normalized-tbody').innerHTML = rows;
  }
}

function renderDomainCard(cat, r) {
  const status = r.status || 'missing';

  // Primary metric (UI spec §5 mapping)
  let metricVal = 'N/A';
  let metricLabel = r.primary_metric || '—';

  if (cat === 'cpu') {
    const v = r.score || (r.subtests && r.subtests.baseline && r.subtests.baseline.score);
    metricVal = na(v);
    metricLabel = r.primary_metric || 'baseline_score';
  } else if (cat === 'gpu_compute') {
    metricVal = na(r.score);
    metricLabel = r.primary_metric || 'score';
  } else if (cat === 'gpu_game') {
    metricVal = na(r.fps);
    metricLabel = 'fps';
  } else if (cat === 'ai') {
    metricVal = na(r.score);
    metricLabel = r.primary_metric || 'composite_normalized';
  } else if (cat === 'memory') {
    metricVal = na(r.score);
    metricLabel = r.primary_metric || 'read_write_mib_per_sec';
  } else if (cat === 'disk') {
    const seq = r.subtests && r.subtests.fio_seq ? r.subtests.fio_seq.bw_kib_per_sec : r.score;
    metricVal = na(seq);
    metricLabel = 'seq_bw_kib_per_sec';
  } else if (cat === 'stress') {
    metricVal = na(r.throttling_detected);
    metricLabel = 'throttling_detected';
  } else {
    metricVal = na(r.score);
  }

  // Secondary metric
  let secondary = '';
  if (cat === 'gpu_game' && r.frametime_ms != null) {
    secondary = `<div class="metric-label">frametime: ${na(r.frametime_ms)} ms</div>`;
  } else if (cat === 'ai') {
    if (r.prompt_tps != null) secondary += `<div class="metric-label">prompt_tps: ${na(r.prompt_tps)}</div>`;
    if (r.eval_tps != null) secondary += `<div class="metric-label">eval_tps: ${na(r.eval_tps)}</div>`;
  } else if (cat === 'disk') {
    const rand = r.subtests && r.subtests.fio_rand4k ? r.subtests.fio_rand4k.iops : null;
    if (rand != null) secondary = `<div class="metric-label">rand_iops: ${na(rand)}</div>`;
  } else if (cat === 'stress' && r.thermal_trend) {
    secondary = `<div class="metric-label">thermal: ${r.thermal_trend}</div>`;
  }

  // Subtests summary
  let subtestHtml = '';
  if (r.subtests) {
    const entries = Object.entries(r.subtests).slice(0, 4);
    subtestHtml = entries.map(([k, v]) =>
      `<div class="metric-label">${k}: ${statusChip(v.status || 'unknown')} ${na(v.score || v.bw_kib_per_sec || v.iops || v.elapsed_sec)}</div>`
    ).join('');
  }

  const notesText = r.notes ? r.notes.split(';').slice(0, 2).join('; ') : '';

  // Vendor info for GPU
  const vendorInfo = (cat === 'gpu_compute' && r.vendor_detected && r.vendor_detected !== 'unknown')
    ? `<div class="metric-label">vendor: ${r.vendor_detected} (${r.provider_mode || ''})</div>` : '';

  return `
    <div class="domain-card" data-cat="${cat}">
      <h3>${CAT_LABELS[cat] || cat}</h3>
      <div>${statusChip(status)}</div>
      <div class="metric">${metricVal}</div>
      <div class="metric-label">${metricLabel}</div>
      ${secondary}
      ${subtestHtml}
      ${vendorInfo}
      ${notesText ? `<div class="notes">${notesText}</div>` : ''}
    </div>
  `;
}

// ── Auto-load latest summary.json on page load ─────────────────────────────
(async () => {
  const data = await loadFromPath('data.json') || await loadFromPath('../reports/latest/report/summary.json');
  if (data) {
    renderResults(data);
    showTab('tab-results');
  }
})();

