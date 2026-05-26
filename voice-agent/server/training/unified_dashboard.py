"""
Unified validation dashboard — single HTML page serving all validation and
fix-validation runs at /validation/.

Features:
- Prev / Next navigation between runs (keyboard arrows supported)
- Header: Run N/M — name — code — started → finished
- Auto-detects run type (full 280 validation vs fix-validation bucket run)
- Auto-refreshes every 5 seconds while running
"""

import json
from pathlib import Path


RUNS_ROOT = Path("/tmp/validation_runs")
MANIFEST_FILE = RUNS_ROOT / "runs_manifest.json"


def load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text())
    return {"runs": []}


def save_manifest(manifest: dict) -> None:
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))


def register_run(
    run_dir: str,
    name: str,
    code: str,
    run_type: str,  # "validation" or "fix-validation"
    started_at: str = "",
) -> int:
    """Register a new run and return its index.

    Auto-finishes any prior runs still marked as 'running' (stale from crashes).
    """
    manifest = load_manifest()

    # Auto-finish stale "running" entries — when we register a new run,
    # any previous run still marked running must have finished or crashed.
    for prev in manifest["runs"]:
        if prev.get("status") == "running":
            prev["status"] = "finished"
            if not prev.get("finished_at"):
                prev["finished_at"] = started_at

    idx = len(manifest["runs"])
    manifest["runs"].append({
        "index": idx,
        "dir": run_dir,
        "name": name,
        "code": code,
        "type": run_type,
        "started_at": started_at,
        "finished_at": "",
        "status": "running",
    })
    save_manifest(manifest)
    return idx


def finish_run(idx: int, finished_at: str = "", status: str = "finished") -> None:
    manifest = load_manifest()
    if 0 <= idx < len(manifest["runs"]):
        manifest["runs"][idx]["finished_at"] = finished_at
        manifest["runs"][idx]["status"] = status
        save_manifest(manifest)


def build_unified_dashboard_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Validation Runs — Sailly</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {
  --bg: #0b0e14; --surface: #13171f; --border: #222736; --text: #d4d8e2;
  --muted: #8b9ab0; --pass: #4ade80; --fail: #f87171; --warn: #fde68a;
  --blue: #93c5fd; --purple: #c4b5fd; --orange: #fb923c;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; font-size: 14px; }

/* ── Top navigation bar ── */
.nav-bar {
  display: flex; align-items: center; gap: 12px; padding: 12px 20px;
  background: var(--surface); border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 100;
}
.nav-btn {
  background: #1e2433; border: 1px solid var(--border); border-radius: 6px;
  color: var(--text); padding: 6px 14px; cursor: pointer; font-size: 13px;
  transition: all .15s;
}
.nav-btn:hover { background: #2a3140; border-color: var(--blue); }
.nav-btn:disabled { opacity: .3; cursor: default; }
.nav-title {
  flex: 1; text-align: center; font-weight: 600; font-size: 1rem;
  color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.nav-meta { color: var(--muted); font-size: 12px; white-space: nowrap; }
.nav-step {
  background: #1e2433; border: 1px solid var(--border); border-radius: 20px;
  padding: 4px 12px; font-size: 12px; font-weight: 700; color: var(--blue);
}
.nav-status { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 20px; }
.nav-status.running { background: #2a2010; color: #fbbf24; }
.nav-status.finished { background: #14291f; color: #4ade80; }
.nav-status.failed { background: #2a1212; color: #f87171; }

/* ── Content area ── */
.content { padding: 20px 24px; }
.loading { text-align: center; padding: 60px; color: var(--muted); }

/* ── Shared: status-bar ── */
.status-bar {
  display: flex; flex-wrap: wrap; gap: 16px; align-items: center; margin-bottom: 18px;
  padding: 10px 16px; background: var(--surface); border-radius: 8px;
  border: 1px solid var(--border); font-size: .82rem;
}
.status-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.status-dot.running { background: #facc15; animation: pulse 1.4s infinite; }
.status-dot.done { background: var(--pass); }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.35} }
.sbar-item { display: flex; gap: 6px; align-items: center; }
.sbar-label { color: var(--muted); }
.sbar-val { color: #e2e8f0; font-weight: 600; font-variant-numeric: tabular-nums; }

/* ── KPI grid ── */
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 12px; margin-bottom: 18px; }
.kpi { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
.kpi-label { font-size: .68rem; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); margin-bottom: 6px; }
.kpi-val { font-size: 1.5rem; font-weight: 700; color: #fff; font-variant-numeric: tabular-nums; }
.kpi-sub { font-size: .72rem; color: #778; margin-top: 4px; }
.kpi-bar { height: 5px; background: #1e2433; border-radius: 3px; margin-top: 8px; overflow: hidden; }
.kpi-bar-fill { height: 100%; background: var(--pass); border-radius: 3px; transition: width .6s; }
.c-green { color: var(--pass); } .c-yellow { color: var(--warn); } .c-blue { color: var(--blue); }
.c-purple { color: var(--purple); } .c-orange { color: var(--orange); }

/* ── Two-col layout ── */
.two-col { display: grid; grid-template-columns: 1.6fr 1fr; gap: 14px; margin-bottom: 14px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
.card-title { font-size: .85rem; font-weight: 600; color: #c4cdd8; margin-bottom: 12px; }

/* ── Bucket rows ── */
.bucket-list { display: flex; flex-direction: column; gap: 7px; }
.bucket-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 10px;
  background: #0f131a; border-radius: 7px; border: 1px solid #1e2433; }
.bucket-reason { font-size: .8rem; color: #c4cdd8; }
.bucket-bar-wrap { flex: 1; margin: 0 12px; height: 5px; background: #1e2433; border-radius: 3px; overflow: hidden; }
.bucket-bar-fill { height: 100%; background: var(--fail); border-radius: 3px; }
.bucket-cnt { font-size: .78rem; font-variant-numeric: tabular-nums; min-width: 2.2rem; text-align: right; color: var(--fail); font-weight: 600; }

/* ── Phase boxes ── */
.phase-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.phase-box { background: #0f131a; border: 1px solid #1e2433; border-radius: 8px; padding: 10px 12px; }
.phase-box-title { font-size: .68rem; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin-bottom: 6px; }
.phase-box-rate { font-size: 1.1rem; font-weight: 700; color: var(--pass); }
.phase-box-sub { font-size: .7rem; color: #778; margin-top: 2px; }

/* ── Tables ── */
.tbl-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .78rem; }
th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #1a1e28; vertical-align: top; }
th { color: var(--muted); font-weight: 500; font-size: .68rem; text-transform: uppercase;
  letter-spacing: .05em; background: #10131a; position: sticky; top: 0; z-index: 1; }
tr:hover td { background: #0f1320; }
.pass { color: var(--pass); font-weight: 700; } .fail { color: var(--fail); font-weight: 700; }
.meta { color: var(--muted); font-size: .72rem; }
.latency { font-variant-numeric: tabular-nums; color: var(--blue); white-space: nowrap; }
.cost { font-variant-numeric: tabular-nums; color: var(--warn); }

/* Fix-validation specific */
.t1-row { border-left: 3px solid var(--pass); }
.t2-row { border-left: 3px solid var(--warn); }
.validated { color: var(--pass); font-weight: 600; }
.unresolved { color: var(--fail); font-weight: 600; }
.running-s { color: var(--blue); font-weight: 600; }
.pending-s { color: var(--muted); }
.bar-bg { background: #21262d; height: 14px; border-radius: 7px; width: 120px; display: inline-block;
  vertical-align: middle; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 7px; transition: width .3s; }
.bar-pass { background: var(--pass); } .bar-warn { background: var(--warn); } .bar-fail { background: var(--fail); }
.pass-tag { background: #238636; color: #fff; border-radius: 3px; padding: 1px 6px; font-size: 11px; }
.fail-tag { background: #da3633; color: #fff; border-radius: 3px; padding: 1px 6px; font-size: 11px; }
.detail-table td { font-size: 12px; padding: 6px 10px; }

.persona-tag { display: inline-block; padding: 2px 7px; border-radius: 999px; font-size: .68rem;
  font-weight: 600; background: #1e2433; color: var(--purple); white-space: nowrap; }
.phase-tag { display: inline-block; padding: 2px 6px; border-radius: 5px; font-size: .68rem;
  font-weight: 700; background: #1a2436; color: var(--blue); white-space: nowrap; }
.end-tag { font-size: .7rem; padding: 2px 6px; border-radius: 4px; }
.end-tag.ok { background: #14291f; color: var(--pass); }
.end-tag.warn { background: #2a2010; color: #fbbf24; }
.end-tag.err { background: #2a1212; color: var(--fail); }
.fail-reason { color: #fca5a5; font-size: .74rem; line-height: 1.35; }
.tools { color: #cbd5e1; font-size: .74rem; line-height: 1.4; }
.missing-tool { color: var(--fail); font-size: .72rem; }
.cost-bd { font-size: .68rem; color: #a78bfa; line-height: 1.5; margin-top: 2px; }
.cost-cum { font-variant-numeric: tabular-nums; color: #a3a3a3; font-size: .72rem; }
.score-val { font-variant-numeric: tabular-nums; font-weight: 700; }
.score-72p { color: var(--pass); } .score-50p { color: #fbbf24; } .score-lo { color: var(--fail); }
.ts { font-variant-numeric: tabular-nums; color: var(--muted); font-size: .7rem; white-space: nowrap; }
.cost-note { color: #445; font-size: .7rem; margin-top: 10px; line-height: 1.5; }

.empty-state { text-align: center; padding: 80px 20px; color: var(--muted); }
.empty-state h2 { color: #fff; margin-bottom: 8px; }

@media(max-width: 900px) {
  .kpi-grid { grid-template-columns: repeat(3, 1fr); }
  .two-col { grid-template-columns: 1fr; }
  .phase-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
</head>
<body>

<div class="nav-bar">
  <button class="nav-btn" id="btn-overview" onclick="goOverview()" title="Back to all sessions overview" style="font-weight:700">☰ All Sessions</button>
  <button class="nav-btn" id="btn-prev" onclick="navigate(-1)" title="Previous run (←)">◀ Prev</button>
  <span class="nav-step" id="nav-step">— / —</span>
  <span class="nav-title" id="nav-title">All Sessions</span>
  <span class="nav-status" id="nav-status"></span>
  <span class="nav-meta" id="nav-times"></span>
  <div style="display:flex;gap:6px;margin-left:auto;align-items:center">
    <button id="loop-btn-start" onclick="loopStart()" title="Start validation loop"
      style="display:none;padding:5px 12px;border-radius:5px;border:1px solid #166534;background:#14291f;color:#4ade80;font-size:12px;font-weight:700;cursor:pointer">▶ Start</button>
    <button id="loop-btn-pause" onclick="loopPause()" title="Pause / Resume loop"
      style="display:none;padding:5px 12px;border-radius:5px;border:1px solid #92400e;background:#1c1500;color:#fbbf24;font-size:12px;font-weight:700;cursor:pointer">⏸ Pause</button>
    <button id="loop-btn-stop" onclick="loopStop()" title="Stop validation loop"
      style="display:none;padding:5px 12px;border-radius:5px;border:1px solid #7f1d1d;background:#1c0a0a;color:#f87171;font-size:12px;font-weight:700;cursor:pointer">■ Stop</button>
  </div>
  <button class="nav-btn" id="btn-next" onclick="navigate(1)" title="Next run (→)">Next ▶</button>
</div>

<div id="status-banner" style="display:none;align-items:center;gap:10px;padding:8px 20px;font-size:13px;border-bottom:1px solid var(--border)"></div>

<div class="content" id="content">
  <div class="loading">Loading validation runs…</div>
</div>

<script>
let manifest = null;
let currentIdx = -1;
let refreshTimer = null;

function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

/** Map manifest dir to a URL path served under the validation dashboard root (/tmp/validation_runs). */
function normalizeRunDirForFetch(dir) {
  var d = String(dir || '').replace(/\\\\/g, '/');
  while (d.length > 1 && d.charAt(d.length - 1) === '/') d = d.slice(0, -1);
  if (!d) return '';
  if (d.indexOf('/tmp/validation_runs/') === 0) {
    d = d.slice('/tmp/validation_runs/'.length);
    while (d.length && d.charAt(0) === '/') d = d.slice(1);
    return d;
  }
  if (d.charAt(0) === '/') {
    var parts = d.split('/').filter(Boolean);
    return parts.length ? parts[parts.length - 1] : d;
  }
  while (d.length && d.charAt(0) === '/') d = d.slice(1);
  return d;
}
function pct(r) { return r != null ? (r * 100).toFixed(0) + '%' : '—'; }
function fmtMs(v) { if (v == null || v === '') return '<span class="meta">—</span>'; var n = Number(v); if (isNaN(n)) return '<span class="meta">—</span>'; return '<span class="latency">' + (n >= 60000 ? (n/60000).toFixed(1)+'m' : n >= 1000 ? (n/1000).toFixed(1)+'s' : n.toFixed(0)+'ms') + '</span>'; }
function fmtScore(v) { if (v == null) return '<span class="meta">—</span>'; var n = Number(v); if (isNaN(n)) return '<span class="meta">—</span>'; var c = n >= 72 ? 'score-72p' : n >= 50 ? 'score-50p' : 'score-lo'; return '<span class="score-val ' + c + '">' + n.toFixed(1) + '</span>'; }
function fmtUsd(v) { if (v == null || v === '') return '<span class="meta">—</span>'; var n = Number(v); if (isNaN(n)) return '<span class="meta">—</span>'; return '<span class="cost">$' + n.toFixed(4) + '</span>'; }
function fmtEndReason(v) { if (!v) return '<span class="meta">—</span>'; var s = esc(v); var c = (v === 'end_call_tool' || v === 'goodbye') ? 'ok' : (v === 'max_turns' || v === 'TIMEOUT') ? 'warn' : 'err'; return '<span class="end-tag ' + c + '">' + s + '</span>'; }
function fmtPersona(v) { if (!v) return '<span class="meta">—</span>'; return '<span class="persona-tag">' + esc(v) + '</span>'; }
function fmtPhaseTag(v, cat) { if (!v) return '<span class="meta">—</span>'; return '<span class="phase-tag">' + esc(v) + '</span>' + (cat ? '<div class="meta" style="margin-top:3px">' + esc(cat) + '</div>' : ''); }
function fmtTs(v) { if (!v) return '<span class="meta">—</span>'; try { var d = new Date(v); return '<span class="ts">' + d.toLocaleTimeString() + '</span>'; } catch(e) { return '<span class="meta">—</span>'; } }
function fmtMissing(arr) { if (!arr || !arr.length) return '<span class="c-green meta">✓ none</span>'; return '<span class="missing-tool">' + arr.map(esc).join('<br>') + '</span>'; }
function fmtTools(exp, got) { var e = exp && exp.length ? esc(exp.join(', ')) : '<span class="meta">—</span>'; var g = got && got.length ? esc(got.join(', ')) : '<span class="meta">—</span>'; return '<div class="tools"><span class="meta">exp:</span> ' + e + '<br><span class="meta">got:</span> ' + g + '</div>'; }
function fmtFail(arr) { if (!arr || !arr.length) return '<span class="c-green meta">—</span>'; return '<div class="fail-reason">' + arr.map(esc).join('<br>') + '</div>'; }
function fmtCostBd(bd) { if (!bd) return ''; var p = []; if (bd.gemini_calls) p.push('Gemini x' + bd.gemini_calls); if (bd.openai_calls) p.push('GPT x' + bd.openai_calls); if (bd.deepgram_requests) p.push('DG x' + bd.deepgram_requests); if (bd.bot_tts_chars) p.push('BotTTS ' + bd.bot_tts_chars + 'ch'); return '<div class="cost-bd">' + p.join('<br>') + '</div>'; }
function barCls(r, thr) { if (r == null) return 'bar-fail'; return r >= thr ? 'bar-pass' : (r >= thr * 0.6 ? 'bar-warn' : 'bar-fail'); }
function mkBar(r, thr) { if (r == null) return '<span style="color:#556">—</span>'; var w = Math.round(r * 100); var cls = barCls(r, thr); var pc = r>=thr?'#4ade80':(r>=thr*0.6?'#fbbf24':'#f87171'); return '<div class="bar-bg"><div class="bar-fill ' + cls + '" style="width:' + w + '%"></div></div> <span style="color:'+pc+';font-weight:600">' + pct(r) + '</span>'; }

// ── Session overview ─────────────────────────────────────────────────────────

function groupBySessions(runs) {
  var sessions = {};
  var order = [];
  for (var r of runs) {
    var m = (r.name || '').match(/^\[([^\]]+)\]/);
    var key = m ? m[1] : (r.type === 'noautofix_deep' ? '__noautofix__' : '__other__' + (r.index || ''));
    if (!sessions[key]) { sessions[key] = []; order.push(key); }
    sessions[key].push(r);
  }
  return order.map(function(k) { return { label: k, runs: sessions[k] }; });
}

function renderSessionCard(session) {
  var runs = session.runs;
  var label = session.label;
  var isNoAutoFix = label === '__noautofix__';
  var noAutoFixRun = runs.find(function(r) { return r.type === 'noautofix_deep'; });

  var phaseA  = runs.find(function(r) {
    var c = r.code || '';
    return c === 'PHASE-A' || c === 'PHASE-A-PATCHED' || c.indexOf('PHASE-A') === 0;
  });
  var phaseE  = runs.find(function(r) { return r.code === 'PHASE-E'; });
  var fixRuns = runs.filter(function(r) { return r.code && r.code.startsWith('FIX-'); });
  var cfvRuns = runs.filter(function(r) { return r.type === 'cfv'; });

  var runningRun = runs.find(function(r) { return r.status === 'running'; });
  var anyRunning = !!runningRun;
  var anyStopped = runs.some(function(r) { return r.status === 'stopped'; });
  var sessionStatus = anyRunning ? 'running' : (anyStopped ? 'stopped' : 'finished');

  var baselinePct = '—';
  if (phaseA) {
    var bm = (phaseA.name || '').match(/([\d.]+)%\)?/);
    if (bm) baselinePct = bm[1] + '%';
  }
  if (isNoAutoFix && noAutoFixRun) {
    var buckets = noAutoFixRun.buckets || [];
    var totalR = buckets.reduce(function(s,b){return s+(b.total_runs||0);},0);
    var totalP = buckets.reduce(function(s,b){return s+(b.pass_count||0);},0);
    if (totalR > 0) baselinePct = (totalP/totalR*100).toFixed(0) + '%';
  }

  var indices = runs.map(function(r) { return r.index; }).filter(function(i) { return i != null; });
  var indicesStr = indices.join(',');

  var startedAt = (phaseA||noAutoFixRun||runs[0]||{}).started_at || '';
  var startedStr = '';
  if (startedAt) { try { startedStr = new Date(startedAt).toLocaleString(); } catch(e) { startedStr = startedAt; } }

  var accentColor = isNoAutoFix ? '#c4b5fd' : (sessionStatus === 'running' ? '#fbbf24' : (sessionStatus === 'stopped' ? '#f87171' : '#4ade80'));
  var statusBg    = sessionStatus === 'running' ? '#2a2010' : (sessionStatus === 'stopped' ? '#1c0a0a' : '#14291f');
  var statusColor = sessionStatus === 'running' ? '#fbbf24' : (sessionStatus === 'stopped' ? '#f87171' : '#4ade80');

  var html = '<div style="background:var(--surface);border:1px solid var(--border);border-left:3px solid ' + accentColor + ';border-radius:10px;padding:14px 16px;margin-bottom:10px">';

  // ── Header row
  html += '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap">';
  html += '<span style="font-size:.95rem;font-weight:700;color:#fff">' + esc(isNoAutoFix ? '[NoAutoFix-Deep]' : ('[' + label + ']')) + '</span>';
  html += '<span style="background:' + statusBg + ';color:' + statusColor + ';border-radius:12px;padding:2px 9px;font-size:10px;font-weight:700">' + sessionStatus.toUpperCase() + '</span>';
  if (!isNoAutoFix && baselinePct !== '—') {
    html += '<span style="color:var(--muted);font-size:12px">Baseline: <b style="color:#e2e8f0">' + esc(baselinePct) + '</b></span>';
  }
  if (runningRun) {
    html += '<span style="color:#fbbf24;font-size:12px;font-style:italic">● ' + esc(runningRun.code || '') + '</span>';
  }
  html += '<span style="color:var(--muted);font-size:11px;margin-left:auto">' + esc(startedStr) + '</span>';
  html += '</div>';

  if (isNoAutoFix && noAutoFixRun) {
    // ── NoAutoFix bucket bar
    var buckets = noAutoFixRun.buckets || [];
    html += '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px">';
    for (var bkt of buckets) {
      var bc = bkt.pass_rate === 1.0 ? '#4ade80' : (bkt.pass_rate === 0.0 ? '#f87171' : (bkt.pass_rate == null ? '#6b7280' : '#fbbf24'));
      var bb = bkt.pass_rate === 1.0 ? '#14291f' : (bkt.pass_rate === 0.0 ? '#1c0a0a' : '#1a1a1a');
      html += '<span style="background:' + bb + ';color:' + bc + ';border-radius:5px;padding:2px 9px;font-size:11px;font-weight:600">';
      html += esc(bkt.name) + ': ' + (bkt.pass_rate != null ? (bkt.pass_rate * 100).toFixed(0) + '%' : 'skip');
      html += '</span>';
    }
    html += '</div>';
  } else {
    // ── Phase timeline chips
    html += '<div style="display:flex;gap:5px;flex-wrap:wrap;align-items:center;margin-bottom:10px">';
    if (phaseA) {
      var pc = phaseA.status === 'finished' ? '#4ade80' : (phaseA.status === 'running' ? '#fbbf24' : '#374151');
      html += '<span onclick="viewRun(' + phaseA.index + ')" style="background:#0f131a;border:1px solid ' + pc + ';color:' + pc + ';border-radius:4px;padding:2px 7px;font-size:10px;cursor:pointer;font-weight:600">PHASE-A</span>';
    }
    fixRuns.sort(function(a,b){ return (a.code||'').localeCompare(b.code||''); });
    for (var fx of fixRuns) {
      var fc = fx.status === 'finished' ? '#93c5fd' : (fx.status === 'running' ? '#fbbf24' : (fx.status === 'stopped' ? '#f87171' : '#374151'));
      html += '<span onclick="viewRun(' + fx.index + ')" style="background:#0f131a;border:1px solid ' + fc + ';color:' + fc + ';border-radius:4px;padding:2px 7px;font-size:10px;cursor:pointer;font-weight:600">' + esc(fx.code) + '</span>';
    }
    for (var cv of cfvRuns) {
      var cc = cv.status === 'finished' ? '#c4b5fd' : (cv.status === 'running' ? '#fbbf24' : (cv.status === 'stopped' ? '#f87171' : '#374151'));
      html += '<span onclick="viewRun(' + cv.index + ')" style="background:#0f131a;border:1px solid ' + cc + ';color:' + cc + ';border-radius:4px;padding:2px 7px;font-size:10px;cursor:pointer;font-weight:600">CFV</span>';
    }
    if (phaseE) {
      var ec = phaseE.status === 'finished' ? '#4ade80' : '#374151';
      html += '<span onclick="viewRun(' + phaseE.index + ')" style="background:#0f131a;border:1px solid ' + ec + ';color:' + ec + ';border-radius:4px;padding:2px 7px;font-size:10px;cursor:pointer;font-weight:600">PHASE-E</span>';
    }
    // Stats
    html += '<span style="color:var(--muted);font-size:11px;margin-left:8px">' + runs.length + ' runs</span>';
    if (fixRuns.length) html += '<span style="color:var(--muted);font-size:11px">' + fixRuns.length + ' fix iter</span>';
    html += '</div>';
  }

  // ── Action buttons
  html += '<div style="display:flex;gap:6px">';
  if (indicesStr) {
    html += '<button onclick="viewSession(\'' + indicesStr + '\')" style="padding:3px 11px;border-radius:5px;border:1px solid var(--blue);background:#0f1724;color:var(--blue);font-size:12px;font-weight:600;cursor:pointer">View ▶</button>';
  }
  if (anyRunning) {
    html += '<button onclick="loopPause()" style="padding:3px 11px;border-radius:5px;border:1px solid #92400e;background:#1c1500;color:#fbbf24;font-size:12px;cursor:pointer">⏸ Pause</button>';
    html += '<button onclick="loopStop()" style="padding:3px 11px;border-radius:5px;border:1px solid #7f1d1d;background:#1c0a0a;color:#f87171;font-size:12px;cursor:pointer">■ Stop</button>';
  } else {
    html += '<button onclick="loopStart()" style="padding:3px 11px;border-radius:5px;border:1px solid #166534;background:#14291f;color:#4ade80;font-size:12px;cursor:pointer">▶ Start</button>';
  }
  html += '</div>';

  html += '</div>';
  return html;
}

function renderOverview() {
  // Collapse nav bar to overview mode
  document.getElementById('btn-prev').style.display = 'none';
  document.getElementById('btn-next').style.display = 'none';
  document.getElementById('nav-step').style.display = 'none';
  document.getElementById('nav-status').textContent = '';
  document.getElementById('nav-times').textContent = '';
  document.getElementById('nav-title').innerHTML = '<span style="color:#fff">Validation Sessions Overview</span>';
  document.getElementById('btn-overview').style.display = 'none';
  _setLoopButtons(false, false);

  var sessions = groupBySessions(manifest.runs);
  // Newest first
  var reversed = sessions.slice().reverse();

  var html = '<div style="max-width:860px;margin:0 auto;padding-bottom:40px">';
  html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">';
  html += '<h2 style="color:#fff;font-size:1.1rem;font-weight:700">All Sessions <span style="color:var(--muted);font-size:.8rem;font-weight:400">(' + sessions.length + ')</span></h2>';
  // Legend
  html += '<div style="display:flex;gap:12px;font-size:11px;color:var(--muted)">';
  html += '<span><span style="color:#4ade80">■</span> Finished</span>';
  html += '<span><span style="color:#fbbf24">■</span> Running</span>';
  html += '<span><span style="color:#f87171">■</span> Stopped</span>';
  html += '<span><span style="color:#c4b5fd">■</span> NoAutoFix</span>';
  html += '</div></div>';

  for (var sess of reversed) {
    html += renderSessionCard(sess);
  }
  html += '</div>';
  document.getElementById('content').innerHTML = html;
}

function goOverview() {
  // Clear URL filter and return to overview
  var url = new URL(window.location.href);
  url.searchParams.delete('indices');
  url.searchParams.delete('runs');
  url.searchParams.delete('run');
  window.history.pushState({}, '', url.toString());
  currentIdx = -1;
  renderOverview();
}

function viewSession(indicesStr) {
  var url = new URL(window.location.href);
  url.searchParams.set('indices', indicesStr);
  url.searchParams.delete('run');
  window.history.pushState({}, '', url.toString());
  currentIdx = -1;
  // Show detail nav
  document.getElementById('btn-prev').style.display = '';
  document.getElementById('btn-next').style.display = '';
  document.getElementById('nav-step').style.display = '';
  document.getElementById('btn-overview').style.display = '';
  refresh();
}

function viewRun(idx) {
  if (idx == null) return;
  // Find run and its session indices
  var run = manifest.runs.find(function(r) { return r.index === idx; });
  if (!run) return;
  var m = (run.name || '').match(/^\[([^\]]+)\]/);
  var sessionRuns = m ? manifest.runs.filter(function(r) {
    var rm = (r.name || '').match(/^\[([^\]]+)\]/);
    return rm && rm[1] === m[1];
  }) : [run];
  var indices = sessionRuns.map(function(r) { return r.index; }).filter(function(i) { return i != null; }).join(',');
  var url = new URL(window.location.href);
  url.searchParams.set('indices', indices);
  url.searchParams.set('run', String(idx));
  window.history.pushState({}, '', url.toString());
  currentIdx = -1;
  document.getElementById('btn-prev').style.display = '';
  document.getElementById('btn-next').style.display = '';
  document.getElementById('nav-step').style.display = '';
  document.getElementById('btn-overview').style.display = '';
  refresh();
}

function navigate(delta) {
  var viewRuns = manifest && manifest._viewRuns ? manifest._viewRuns : (manifest ? manifest.runs : []);
  if (!manifest || !viewRuns.length) return;
  var next = currentIdx + delta;
  if (next < 0 || next >= viewRuns.length) return;
  currentIdx = next;
  loadRun(currentIdx);
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'ArrowLeft') navigate(-1);
  if (e.key === 'ArrowRight') navigate(1);
});

function updateNavBar(run) {
  var total = manifest ? ((manifest._viewRuns || manifest.runs).length) : 0;
  document.getElementById('nav-step').textContent = (currentIdx + 1) + ' / ' + total;
  document.getElementById('btn-prev').disabled = currentIdx <= 0;
  document.getElementById('btn-next').disabled = currentIdx >= total - 1;

  if (!run) {
    document.getElementById('nav-title').textContent = 'No runs yet';
    document.getElementById('nav-status').className = 'nav-status';
    document.getElementById('nav-status').textContent = '';
    document.getElementById('nav-times').textContent = '';
    return;
  }

  var typeLabel = run.type === 'validation' ? '280-SCENARIO'
              : run.type === 'cfv' ? 'CFV DEEP-FIX'
              : run.type === 'noautofix_deep' ? 'NOAUTOFIX DEEP'
              : 'FIX VALIDATION';
  document.getElementById('nav-title').innerHTML =
    '<span style="color:var(--blue)">[' + esc(run.code) + ']</span> ' +
    esc(run.name) + ' <span style="font-size:11px;color:#8b949e;font-weight:400">· ' + typeLabel + '</span>';

  var st = run.status || 'running';
  var statusEl = document.getElementById('nav-status');
  statusEl.className = 'nav-status ' + st;
  statusEl.textContent = st.toUpperCase();

  var times = '';
  if (run.started_at) {
    try { times = new Date(run.started_at).toLocaleString(); } catch(e) { times = run.started_at; }
  }
  if (run.finished_at) {
    try { times += ' → ' + new Date(run.finished_at).toLocaleTimeString(); } catch(e) { times += ' → ' + run.finished_at; }
  }
  document.getElementById('nav-times').textContent = times;
}

async function loadManifest() {
  try {
    var resp = await fetch('runs_manifest.json?t=' + Date.now());
    if (!resp.ok) throw new Error('manifest HTTP ' + resp.status);
    manifest = await resp.json();
  } catch(e) {
    manifest = { runs: [] };
  }
}

// ── Heal-loop status banner (shows next scheduled run + live countdown) ───────
var _statusBannerInterval = null;

async function refreshStatusBanner() {
  try {
    var resp = await fetch('heal_loop_status.json?t=' + Date.now());
    if (!resp.ok) return;
    var s = await resp.json();
    renderStatusBanner(s);
  } catch(e) { /* silently ignore */ }
}

function fmtCountdown(targetIso) {
  if (!targetIso) return '';
  try {
    var diff = new Date(targetIso) - Date.now();
    if (diff <= 0) return 'now';
    var h = Math.floor(diff / 3600000);
    var m = Math.floor((diff % 3600000) / 60000);
    var s = Math.floor((diff % 60000) / 1000);
    if (h > 0) return h + 'h ' + m + 'm';
    if (m > 0) return m + 'm ' + s + 's';
    return s + 's';
  } catch(e) { return ''; }
}

var _loopPaused = false;

function _setLoopButtons(running, paused) {
  var btnStart = document.getElementById('loop-btn-start');
  var btnPause = document.getElementById('loop-btn-pause');
  var btnStop  = document.getElementById('loop-btn-stop');
  if (!btnStart) return;
  if (running) {
    btnStart.style.display = 'none';
    btnPause.style.display = 'inline-block';
    btnStop.style.display  = 'inline-block';
    btnPause.textContent = paused ? '▶ Resume' : '⏸ Pause';
    btnPause.style.color  = paused ? '#4ade80' : '#fbbf24';
    btnPause.style.borderColor = paused ? '#166534' : '#92400e';
    btnPause.style.background  = paused ? '#14291f' : '#1c1500';
  } else {
    btnStart.style.display = 'inline-block';
    btnPause.style.display = 'none';
    btnStop.style.display  = 'none';
  }
}

async function loopStop() {
  var btn = document.getElementById('loop-btn-stop');
  btn.disabled = true; btn.textContent = 'Stopping…';
  try {
    var r = await fetch('/api/stop-loop', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
    var d = await r.json();
    if (d.ok) { _setLoopButtons(false, false); await refreshStatusBanner(); await loadManifest(); loadRun(currentIdx); }
    else { alert('Stop failed: ' + d.error); }
  } catch(e) { alert('Stop error: ' + e); }
  btn.disabled = false; btn.textContent = '■ Stop';
}

async function loopStart() {
  var btn = document.getElementById('loop-btn-start');
  btn.disabled = true; btn.textContent = 'Starting…';
  try {
    var r = await fetch('/api/start-loop', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
    var d = await r.json();
    if (d.ok) { _setLoopButtons(true, false); setTimeout(refreshStatusBanner, 2000); }
    else { alert('Start failed: ' + d.error); }
  } catch(e) { alert('Start error: ' + e); }
  btn.disabled = false; btn.textContent = '▶ Start';
}

async function loopPause() {
  var btn = document.getElementById('loop-btn-pause');
  _loopPaused = !_loopPaused;
  btn.disabled = true;
  var action = _loopPaused ? 'pause' : 'resume';
  try {
    var r = await fetch('/api/pause-loop', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({action: action})});
    var d = await r.json();
    if (d.ok) { _setLoopButtons(true, _loopPaused); }
    else { _loopPaused = !_loopPaused; alert('Pause failed: ' + d.error); }
  } catch(e) { _loopPaused = !_loopPaused; alert('Pause error: ' + e); }
  btn.disabled = false;
}

function renderStatusBanner(s) {
  var el = document.getElementById('status-banner');
  if (!el) return;
  _loopPaused = !!s.paused;
  _setLoopButtons(!!s.running, _loopPaused);
  if (s.running) {
    el.style.display = 'flex';
    el.style.background = s.paused ? '#1c1500' : '#14291f';
    el.style.borderColor = s.paused ? '#92400e' : '#166534';
    var dot = s.paused
      ? '<span style="width:9px;height:9px;border-radius:50%;background:#fbbf24;flex-shrink:0"></span>'
      : '<span style="width:9px;height:9px;border-radius:50%;background:#4ade80;animation:pulse 1.4s infinite;flex-shrink:0"></span>';
    var label = s.paused
      ? '<strong style="color:#fbbf24">Validation paused</strong>'
      : '<strong style="color:#4ade80">Validation running</strong>';
    el.innerHTML = dot + label +
      (s.phase ? '<span style="color:#9aa8b8;font-size:12px">' + esc(s.phase) + '</span>' : '');
    // Auto-reload the current run data while running
    if (!refreshTimer) refreshTimer = setInterval(() => loadRun(currentIdx), 8000);
  } else {
    // Stop auto-reload when not running
    if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
    var next = s.next_scheduled;
    var cd = fmtCountdown(next);
    var last = '';
    if (s.last_completed) {
      try { last = ' · Last run: ' + new Date(s.last_completed).toLocaleString(); } catch(e) {}
    }
    var nextStr = next ? ' — next in <strong style="color:#fde68a">' + cd + '</strong>' : '';
    if (cd || last) {
      el.style.display = 'flex';
      el.style.background = '#0f131a';
      el.style.borderColor = '#222736';
      el.innerHTML =
        '<span style="width:9px;height:9px;border-radius:50%;background:#8b9ab0;flex-shrink:0"></span>' +
        '<span style="color:#9aa8b8;font-size:13px">Nightly validation 23:30 Berlin' + nextStr + last + '</span>';
    } else {
      el.style.display = 'none';
    }
  }
}

// Tick countdown every second when not running
setInterval(() => {
  var el = document.getElementById('status-banner');
  if (el && el.style.display !== 'none' && el.innerHTML.includes('next in')) {
    refreshStatusBanner();
  }
}, 1000);

async function loadRun(idx) {
  var viewRuns = manifest && manifest._viewRuns ? manifest._viewRuns : (manifest ? manifest.runs : []);
  if (!manifest || idx < 0 || idx >= viewRuns.length) {
    updateNavBar(null);
    document.getElementById('content').innerHTML = '<div class="empty-state"><h2>No validation runs yet</h2><p>Start a validation or heal loop to see results here.</p></div>';
    return;
  }
  var run = viewRuns[idx];
  updateNavBar(run);

  if (run.type === 'validation') {
    await renderValidation(run);
  } else if (run.type === 'cfv') {
    await renderCFV(run);
  } else if (run.type === 'noautofix_deep') {
    await renderNoAutoFixDeep(run);
  } else {
    await renderFixValidation(run);
  }
}

async function renderNoAutoFixDeep(run) {
  var content = document.getElementById('content');
  var dir = run.output_dir || '';
  var buckets = run.buckets || [];
  var isRunning = run.status === 'running';

  // Try to load fresh summary if available
  var summary = null;
  try {
    var r = await fetch('/noautofix_deep/' + run.run_id + '/summary.json?t=' + Date.now());
    if (r.ok) summary = await r.json();
  } catch(e) {}

  // Update status from summary
  if (summary && summary.finished_at && isRunning) {
    run.status = 'finished';
    isRunning = false;
    updateNavBar(run);
  }

  var html = '';

  // Status bar
  var currentBucket = buckets.find(function(b) { return b.status === 'running'; });
  var doneBuckets = buckets.filter(function(b) { return b.status === 'done'; }).length;
  html += '<div class="status-bar">' +
    '<div class="status-dot ' + (isRunning ? 'running' : 'done') + '"></div>' +
    '<span class="sbar-val">' + (run.status || 'running').toUpperCase() + '</span>' +
    (currentBucket ? '<div class="sbar-item"><span class="sbar-label">Bucket:</span><span class="sbar-val c-yellow">' + esc(currentBucket.name) + '</span></div>' : '') +
    '<div class="sbar-item"><span class="sbar-label">Buckets done:</span><span class="sbar-val c-green">' + doneBuckets + ' / 5</span></div>' +
    '</div>';

  // KPI row
  var totalRuns = buckets.reduce(function(s, b) { return s + (b.total_runs || 0); }, 0);
  var totalPass = buckets.reduce(function(s, b) { return s + (b.pass_count || 0); }, 0);
  var totalFail = buckets.reduce(function(s, b) { return s + (b.fail_count || 0); }, 0);
  html += '<div class="kpi-grid">' +
    '<div class="kpi"><div class="kpi-label">Total Runs</div><div class="kpi-val">' + totalRuns + '</div></div>' +
    '<div class="kpi"><div class="kpi-label">Passed</div><div class="kpi-val c-green">' + totalPass + '</div></div>' +
    '<div class="kpi"><div class="kpi-label">Failed</div><div class="kpi-val" style="color:var(--fail)">' + totalFail + '</div></div>' +
    '<div class="kpi"><div class="kpi-label">Overall Rate</div><div class="kpi-val">' +
      (totalRuns > 0 ? ((totalPass/totalRuns)*100).toFixed(1) + '%' : '—') +
    '</div></div>' +
    '</div>';

  // Download links for all bucket JSONs
  html += '<div class="card"><div class="card-title">📥 Download Bucket Results</div>' +
    '<div style="display:flex;flex-wrap:wrap;gap:8px;font-size:13px">';
  for (var bkt of buckets) {
    if (bkt.total_runs === 0) continue;
    html += '<a href="/noautofix_deep/' + run.run_id + '/bucket_' + bkt.name + '.json" ' +
            'style="background:#1d4ed8;color:#60a5fa;padding:6px 12px;border-radius:4px;text-decoration:none;font-weight:600">' +
            'bucket_' + bkt.name + '.json (' + bkt.total_runs + ' runs)</a>';
  }
  html += '</div></div>';
  
  // Summary & consolidated report downloads
  html += '<div class="card"><div class="card-title">📊 Summary & Full Report</div>' +
    '<div style="display:flex;flex-wrap:wrap;gap:8px;font-size:13px">' +
    '<a href="/noautofix_deep/' + run.run_id + '/summary.json" ' +
    'style="background:#166534;color:#4ade80;padding:6px 12px;border-radius:4px;text-decoration:none;font-weight:600">summary.json</a>' +
    '<a href="/noautofix_deep/' + run.run_id + '/CONSOLIDATED_FAILURE_REPORT.json" ' +
    'style="background:#7c2d12;color:#fed7aa;padding:6px 12px;border-radius:4px;text-decoration:none;font-weight:600">CONSOLIDATED_FAILURE_REPORT.json</a>' +
    '</div></div>';

  // Bucket table
  html += '<div class="card"><div class="card-title">Tier 1 Bucket Results — NoAutoFix Deep Diagnostic</div><div class="tbl-wrap"><table><thead><tr>' +
    '<th>Bucket</th><th>Status</th><th>Runs</th><th>Pass Rate</th><th>Top Failure Patterns</th>' +
    '</tr></thead><tbody>';

  for (var bkt of buckets) {
    var statusCls = bkt.status === 'done' ? 'validated' : bkt.status === 'running' ? 'running-s' : 'pending-s';
    var patterns = bkt.failure_pattern_counts || {};
    var patternStr = Object.entries(patterns).sort(function(a,b){return b[1]-a[1];})
      .map(function(e) { return '<span style="color:#fbbf24">' + esc(e[0]) + '</span>=<b>' + e[1] + '</b>'; })
      .join('  ');
    html += '<tr>' +
      '<td><b>' + esc(bkt.name) + '</b></td>' +
      '<td class="' + statusCls + '">' + (bkt.status || 'pending').toUpperCase() + '</td>' +
      '<td>' + (bkt.total_runs || '—') + '</td>' +
      '<td>' + (bkt.pass_rate != null ? mkBar(bkt.pass_rate, 0.95) : '<span style="color:#556">—</span>') + '</td>' +
      '<td style="font-size:12px">' + (patternStr || '<span style="color:#556">—</span>') + '</td>' +
      '</tr>';
  }
  html += '</tbody></table></div></div>';

  // Per-bucket detail cards (loaded from bucket JSON files)
  for (var bkt of buckets) {
    if (bkt.status !== 'done') continue;
    var bucketUrl = '/noautofix_deep/' + run.run_id + '/bucket_' + bkt.name + '.json';
    html += '<div class="card" id="bkt-card-' + esc(bkt.name) + '">' +
      '<div class="card-title">' + esc(bkt.name) + ' — Failed Run Details</div>' +
      '<div class="loading" data-bucket-url="' + esc(bucketUrl) + '" data-bucket="' + esc(bkt.name) + '">Loading…</div>' +
      '</div>';
  }

  content.innerHTML = html;

  // Load per-bucket detail asynchronously
  for (var bkt of buckets) {
    if (bkt.status !== 'done') continue;
    var card = document.getElementById('bkt-card-' + bkt.name);
    if (!card) continue;
    var loader = card.querySelector('[data-bucket-url]');
    if (!loader) continue;
    var url = loader.getAttribute('data-bucket-url');
    try {
      var br = await fetch(url + '?t=' + Date.now());
      if (!br.ok) { loader.textContent = 'No data yet.'; continue; }
      var bd = await br.json();
      var scenarios = bd.scenarios || [];
      var failingScens = scenarios.filter(function(s) { return s.fail_count > 0; });
      if (failingScens.length === 0) {
        loader.innerHTML = '<span class="c-green">✓ All passing — no failures recorded</span>';
        continue;
      }
      var tbl = '<div class="tbl-wrap"><table><thead><tr>' +
        '<th>Scenario</th><th>Runs</th><th>Pass</th><th>Fail</th><th>Pass Rate</th><th>Failure Diagnoses</th>' +
        '</tr></thead><tbody>';
      for (var sc of failingScens) {
        var diags = {};
        for (var fr of (sc.failed_runs || [])) {
          var cause = (fr.diagnosis || {}).root_cause || 'unknown';
          diags[cause] = (diags[cause] || 0) + 1;
        }
        var diagStr = Object.entries(diags).sort(function(a,b){return b[1]-a[1];})
          .map(function(e){ return '<span style="color:#f87171">' + esc(e[0]) + '</span> ×' + e[1]; })
          .join('<br>');
        tbl += '<tr>' +
          '<td><b>' + esc(sc.scenario_id) + '</b></td>' +
          '<td>' + sc.total_runs + '</td>' +
          '<td class="c-green">' + sc.pass_count + '</td>' +
          '<td style="color:var(--fail)">' + sc.fail_count + '</td>' +
          '<td>' + mkBar(sc.pass_rate, 0.95) + '</td>' +
          '<td style="font-size:12px">' + (diagStr || '—') + '</td>' +
          '</tr>';
        // Show first 3 failed run details
        var shown = 0;
        for (var fr of (sc.failed_runs || [])) {
          if (shown++ >= 3) { tbl += '<tr><td colspan="6" style="color:#556;font-size:11px">… ' + (sc.fail_count - 3) + ' more failed runs</td></tr>'; break; }
          var diag = fr.diagnosis || {};
          var events = (fr.pipeline_events_all || []).slice(0, 5).map(function(e){ return '<code style="font-size:10px;color:#9aa8b8">' + esc(e) + '</code>'; }).join('<br>');
          tbl += '<tr style="background:#0d1117">' +
            '<td colspan="2" style="font-size:11px;color:#8b949e">[' + esc(fr.noise_variant) + '] rep' + fr.rep_idx + '</td>' +
            '<td colspan="2" style="font-size:11px;color:#f87171">' + esc(diag.root_cause || '?') + '</td>' +
            '<td colspan="2" style="font-size:10px">' + events + '</td>' +
            '</tr>';
        }
      }
      tbl += '</tbody></table></div>';
      loader.innerHTML = tbl;
    } catch(e) {
      loader.textContent = 'Load error: ' + e;
    }
  }

  // Auto-refresh while running
  if (isRunning) {
    if (!refreshTimer) refreshTimer = setInterval(function() { loadRun(currentIdx); }, 15000);
  }
}

async function renderValidation(run) {
  var dir = normalizeRunDirForFetch(run.dir);
  var content = document.getElementById('content');
  try {
    var resp = await fetch(dir + '/ab_live_status.json?t=' + Date.now());
    var d = await resp.json();
  } catch(e) {
    content.innerHTML = '<div class="loading">Loading data from ' + esc(dir) + '…</div>';
    return;
  }

  // Update run status dynamically
  if (d.running === false && run.status === 'running') {
    run.status = 'finished';
    updateNavBar(run);
  }

  var done = d.scenarios_done || 0, total = d.scenarios_total || 0, running = d.running;
  var elapsed = d.elapsed_s ? (Number(d.elapsed_s) < 60 ? d.elapsed_s.toFixed(0) + 's' : (d.elapsed_s / 60).toFixed(1) + 'm') : '--';
  var s = d.summary || {};
  var olt = s.one_live_cost_usd_total != null ? Number(s.one_live_cost_usd_total) : 0;
  var pw = d.parallel_workers || 1, hb = d.heartbeat || 0;

  var html = '';

  // Status bar
  html += '<div class="status-bar">' +
    '<div class="status-dot ' + (running ? 'running' : 'done') + '"></div>' +
    '<span class="sbar-val">' + (running ? 'Running' : 'Complete') + '</span>' +
    '<div class="sbar-item"><span class="sbar-label">Scenarios:</span><span class="sbar-val">' + done + ' / ' + total + '</span></div>' +
    '<div class="sbar-item"><span class="sbar-label">Elapsed:</span><span class="sbar-val">' + elapsed + '</span></div>' +
    '<div class="sbar-item"><span class="sbar-label">Workers:</span><span class="sbar-val">' + pw + '</span></div>' +
    '<div class="sbar-item"><span class="sbar-label">Cost:</span><span class="cost">$' + olt.toFixed(4) + '</span></div>' +
    '</div>';

  // KPIs
  var rate = s.one_live_rate || '--%';
  var rateNum = parseFloat(rate) || 0;
  html += '<div class="kpi-grid">' +
    '<div class="kpi"><div class="kpi-label">Pass Rate</div><div class="kpi-val c-green">' + rate + '</div><div class="kpi-sub">' + (s.one_live_passes || 0) + ' / ' + done + '</div><div class="kpi-bar"><div class="kpi-bar-fill" style="width:' + rateNum + '%"></div></div></div>' +
    '<div class="kpi"><div class="kpi-label">Avg Composite</div><div class="kpi-val">' + (s.one_live_avg_composite || '--') + '</div><div class="kpi-sub">Pass threshold: 72</div></div>' +
    '<div class="kpi"><div class="kpi-label">Call Latency</div><div class="kpi-val c-blue">' + (s.one_live_avg_call_latency_ms != null ? (Number(s.one_live_avg_call_latency_ms)/1000).toFixed(1) + 's' : '--') + '</div></div>' +
    '<div class="kpi"><div class="kpi-label">Cost Total</div><div class="kpi-val c-yellow">$' + olt.toFixed(4) + '</div></div>' +
    '<div class="kpi"><div class="kpi-label">Avg / Scenario</div><div class="kpi-val c-yellow">' + (done > 0 ? '$' + (olt/done).toFixed(4) : '--') + '</div></div>' +
    '<div class="kpi"><div class="kpi-label">Workers · HB</div><div class="kpi-val c-purple">' + pw + ' · #' + hb + '</div></div>' +
    '</div>';

  // Failure buckets + Phase breakdown
  var buckets = d.failure_buckets || [];
  var maxCnt = buckets.length ? buckets[0].count : 1;
  var bucketHtml = '';
  if (!buckets.length) { bucketHtml = '<div class="meta">No failures yet.</div>'; }
  else { for (var b of buckets) { bucketHtml += '<div class="bucket-row"><div class="bucket-reason">' + esc(b.reason) + '</div><div class="bucket-bar-wrap"><div class="bucket-bar-fill" style="width:' + (b.count/maxCnt*100).toFixed(0) + '%"></div></div><div class="bucket-cnt">' + b.count + '</div></div>'; } }

  var results = d.results || [];
  var phM = {1:{p:0,t:0}, 2:{p:0,t:0}, 3:{p:0,t:0}, 4:{p:0,t:0}};
  for (var r of results) { if (!r) continue; var ph = r.phase ? parseInt(r.phase.replace('phase','').replace(/\D/g,'')) : 0; if (ph >= 1 && ph <= 4) { phM[ph].t++; if (r.one_live_pass) phM[ph].p++; } }
  var phaseHtml = '<div class="phase-grid">';
  var phNames = {1:'Phase 1 — FAQ/40', 2:'Phase 2 — Tools/100', 3:'Phase 3 — Chaos/100', 4:'Phase 4 — Edge/40'};
  for (var pi = 1; pi <= 4; pi++) {
    var pm = phM[pi];
    phaseHtml += '<div class="phase-box"><div class="phase-box-title">' + phNames[pi] + '</div><div class="phase-box-rate">' + (pm.t > 0 ? (pm.p/pm.t*100).toFixed(0) + '%' : '--') + '</div><div class="phase-box-sub">' + pm.p + '/' + pm.t + '</div></div>';
  }
  phaseHtml += '</div>';

  html += '<div class="two-col"><div class="card"><div class="card-title">Top Failure Buckets</div><div class="bucket-list">' + bucketHtml + '</div></div><div class="card"><div class="card-title">Phase Breakdown</div>' + phaseHtml + '</div></div>';

  // Results table
  html += '<div class="card" style="margin-bottom:24px"><div class="card-title">Per-Scenario Results <span class="meta">(' + results.length + ' completed)</span></div><div class="tbl-wrap"><table><thead><tr>' +
    '<th>Time</th><th>Scenario ID</th><th>Phase</th><th>Persona</th><th>Result</th><th>Score</th><th>Latency</th><th>Turns</th><th>End</th><th>Expected → Called</th><th>Missing</th><th>Cost</th><th>Failures</th></tr></thead><tbody>';
  var cumCost = 0;
  for (var r of results) {
    if (!r) continue;
    var sc = r.one_live_cost_usd != null ? Number(r.one_live_cost_usd) : 0; if (!isNaN(sc)) cumCost += sc;
    html += '<tr>' +
      '<td>' + fmtTs(r.completed_at) + '</td>' +
      '<td><strong>' + esc(r.scenario_id) + '</strong>' + (r.description ? '<div class="meta">' + esc(r.description) + '</div>' : '') + '</td>' +
      '<td>' + fmtPhaseTag(r.phase, r.category) + '</td>' +
      '<td>' + fmtPersona(r.persona) + '</td>' +
      '<td class="' + (r.one_live_pass ? 'pass' : 'fail') + '">' + (r.one_live_pass ? '✓ PASS' : '✗ FAIL') + '</td>' +
      '<td>' + fmtScore(r.one_live_composite) + '</td>' +
      '<td>' + fmtMs(r.one_live_latency_ms) + '</td>' +
      '<td>' + (r.one_live_turns != null ? r.one_live_turns : '--') + '</td>' +
      '<td>' + fmtEndReason(r.one_live_end_reason) + '</td>' +
      '<td>' + fmtTools(r.expected_tools, r.one_live_tools) + '</td>' +
      '<td>' + fmtMissing(r.one_live_missing_tools) + '</td>' +
      '<td>' + fmtUsd(r.one_live_cost_usd) + '</td>' +
      '<td>' + fmtFail(r.one_live_failures) + '</td></tr>';
  }
  html += '</tbody></table></div></div>';
  content.innerHTML = html;
}

async function renderFixValidation(run) {
  var dir = normalizeRunDirForFetch(run.dir);
  var content = document.getElementById('content');
  try {
    var [stateRes, detailRes] = await Promise.all([
      fetch(dir + '/fix_validation_state.json?t=' + Date.now()),
      fetch(dir + '/fix_scenario_results.json?t=' + Date.now()).catch(function() { return null; })
    ]);
    var d = await stateRes.json();
  } catch(e) {
    content.innerHTML = '<div class="loading">Loading fix-validation data from ' + esc(dir) + '…</div>';
    return;
  }

  if (d.status !== 'running' && run.status === 'running') {
    run.status = d.status === 'finished' ? 'finished' : 'failed';
    updateNavBar(run);
  }

  var isRunning = d.status === 'running';
  var bs = d.buckets || [];
  var validatedCount = bs.filter(function(b) { return b.status === 'validated'; }).length;
  var unresolvedCount = bs.filter(function(b) { return b.status === 'unresolved'; }).length;
  var t1v = bs.filter(function(b) { return b.tier === 1 && b.status === 'validated'; }).length;
  var t1t = bs.filter(function(b) { return b.tier === 1; }).length;
  var t2v = bs.filter(function(b) { return b.tier === 2 && b.status === 'validated'; }).length;
  var t2t = bs.filter(function(b) { return b.tier === 2; }).length;

  var html = '';

  // Status bar
  html += '<div class="status-bar">' +
    '<div class="status-dot ' + (isRunning ? 'running' : 'done') + '"></div>' +
    '<span class="sbar-val">' + (d.status || '—').toUpperCase() + '</span>' +
    (d.current_bucket ? '<div class="sbar-item"><span class="sbar-label">Bucket:</span><span class="sbar-val">' + esc(d.current_bucket) + '</span></div>' : '') +
    (d.current_step ? '<div class="sbar-item"><span class="sbar-label">Step:</span><span class="sbar-val">' + d.current_step + '/3</span></div>' : '') +
    '<div class="sbar-item"><span class="sbar-label">HB:</span><span class="sbar-val">#' + (d.heartbeat || 0) + '</span></div>' +
    '</div>';

  // KPIs
  html += '<div class="kpi-grid">' +
    '<div class="kpi"><div class="kpi-label">Validated</div><div class="kpi-val c-green">' + validatedCount + ' / ' + bs.length + '</div></div>' +
    '<div class="kpi"><div class="kpi-label">Tier 1</div><div class="kpi-val c-green">' + t1v + ' / ' + t1t + '</div></div>' +
    '<div class="kpi"><div class="kpi-label">Tier 2</div><div class="kpi-val c-yellow">' + t2v + ' / ' + t2t + '</div></div>' +
    '<div class="kpi"><div class="kpi-label">Unresolved</div><div class="kpi-val" style="color:var(--fail)">' + unresolvedCount + '</div></div>' +
    '</div>';

  // Bucket table
  html += '<div class="card" style="margin-bottom:18px"><div class="card-title">Bucket Progress</div><div class="tbl-wrap"><table><thead><tr>' +
    '<th>#</th><th>Bucket</th><th>Tier</th><th>Threshold</th><th>Status</th><th>Attempts</th>' +
    '<th>Step 1 (10)</th><th>Step 2 (10)</th><th>Step 3 (10)</th><th>Combined</th><th>Fix Applied</th>' +
    '</tr></thead><tbody>';
  for (var b of bs) {
    var rowCls = b.tier === 1 ? 't1-row' : 't2-row';
    var stsCls = b.status === 'validated' ? 'validated' : b.status === 'unresolved' ? 'unresolved' : b.status === 'running' ? 'running-s' : 'pending-s';
    var thr = b.pass_threshold || 1.0;
    html += '<tr class="' + rowCls + '">' +
      '<td>' + b.priority + '</td>' +
      '<td><b>' + esc(b.name) + '</b></td>' +
      '<td>Tier ' + b.tier + '</td>' +
      '<td>' + (thr * 100).toFixed(0) + '%</td>' +
      '<td class="' + stsCls + '">' + (b.status || '').toUpperCase() + '</td>' +
      '<td>' + b.attempts + '/' + b.max_retries + '</td>' +
      '<td>' + (b.step1_count > 0 ? mkBar(b.step1_rate, thr) + ' (' + b.step1_count + ')' : '<span style="color:#555">Not run</span>') + '</td>' +
      '<td>' + (b.step2_count > 0 ? mkBar(b.step2_rate, thr) + ' (' + b.step2_count + ')' : (b.step1_count > 0 && b.step1_rate < thr ? '<span style="color:#6b7280" title="Step 1 below threshold — Step 2 gated">🔒 Gated</span>' : '<span style="color:#555">Not run</span>')) + '</td>' +
      '<td>' + (b.step3_count > 0 ? mkBar(b.step3_rate, thr) + ' (' + b.step3_count + ')' : (b.step2_count > 0 && b.step2_rate < thr ? '<span style="color:#6b7280" title="Step 2 below threshold — Step 3 gated">🔒 Gated</span>' : (b.step1_count > 0 && b.step1_rate < thr ? '<span style="color:#6b7280" title="Step 1 below threshold — Step 3 gated">🔒 Gated</span>' : '<span style="color:#555">Not run</span>'))) + '</td>' +
      '<td>' + mkBar(b.combined_rate > 0 ? b.combined_rate : null, thr) + '</td>' +
      '<td style="color:#9aa8b8;font-size:12px">' + esc(b.fix_description) + '</td></tr>';
  }
  html += '</tbody></table></div></div>';

  // Scenario detail table
  if (detailRes) {
    try {
      var scenarios = await detailRes.json();
      if (scenarios && scenarios.length) {
        html += '<div class="card"><div class="card-title">Scenario Detail (' + scenarios.length + ')</div><div class="tbl-wrap"><table class="detail-table"><thead><tr>' +
          '<th>Scenario</th><th>Bucket</th><th>Result</th><th>Score</th><th>Tools Expected → Called</th><th>Failures</th></tr></thead><tbody>';
        for (var r of scenarios) {
          html += '<tr>' +
            '<td>' + esc(r.scenario_id) + '</td>' +
            '<td>' + esc(r.bucket || '—') + '</td>' +
            '<td>' + (r.pass ? '<span class="pass-tag">PASS</span>' : '<span class="fail-tag">FAIL</span>') + '</td>' +
            '<td>' + (r.composite != null ? r.composite : '—') + '</td>' +
            '<td class="tools"><span style="color:#8b9ab0">exp:</span> ' + esc((r.expected_tools || []).join(', ')) + '<br><span style="color:#8b9ab0">got:</span> ' + esc((r.tools_called || []).join(', ')) + '</td>' +
            '<td class="fail-reason">' + esc((r.failures || []).join('; ')) + '</td></tr>';
        }
        html += '</tbody></table></div></div>';
      }
    } catch(e) {}
  }

  content.innerHTML = html;
}

async function renderCFV(run) {
  var dir = normalizeRunDirForFetch(run.dir);
  var content = document.getElementById('content');
  content.innerHTML = '<div class="loading">Loading CFV data…</div>';

  var state = null;
  try {
    var resp = await fetch(dir + '/cfv_state.json?t=' + Date.now());
    state = await resp.json();
  } catch(e) {
    content.innerHTML = '<div class="loading">CFV data not yet available — run may still be initializing.</div>';
    return;
  }

  var overallStatus = state.status || 'running';
  var isRunning = overallStatus === 'running';
  var resolvedCount = state.resolved_count || 0;
  var unresolvedCount = state.unresolved_count || 0;
  var projRate = state.projected_pass_rate != null ? (state.projected_pass_rate * 100).toFixed(1) + '%' : '—';
  var costUsd = (state.cost_usd || 0).toFixed(2);
  var currentBucket = state.current_bucket;
  var currentAttempt = state.current_attempt || 0;
  var maxAttempts = state.max_attempts || 10;

  var statusColor = isRunning ? '#60a5fa' : (unresolvedCount === 0 ? '#4ade80' : '#f87171');
  var statusLabel = isRunning ? 'RUNNING' : (unresolvedCount === 0 ? 'ALL RESOLVED' : 'PARTIAL / NEEDS REVIEW');

  var html = '<div style="font-family:monospace;color:#c9d1d9;padding:16px">';

  // Header KPIs
  html += '<div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;flex-wrap:wrap">';
  html += '<div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:12px 20px">';
  html += '<div style="font-size:11px;color:#8b949e;margin-bottom:4px">STATUS</div>';
  html += '<div style="font-size:16px;font-weight:700;color:' + statusColor + '">' + esc(statusLabel) + '</div>';
  html += '</div>';
  html += '<div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:12px 20px">';
  html += '<div style="font-size:11px;color:#8b949e;margin-bottom:4px">RESOLVED</div>';
  html += '<div style="font-size:22px;font-weight:700;color:#4ade80">' + resolvedCount + '</div>';
  html += '</div>';
  html += '<div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:12px 20px">';
  html += '<div style="font-size:11px;color:#8b949e;margin-bottom:4px">NEEDS REVIEW</div>';
  html += '<div style="font-size:22px;font-weight:700;color:' + (unresolvedCount > 0 ? '#f87171' : '#4ade80') + '">' + unresolvedCount + '</div>';
  html += '</div>';
  html += '<div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:12px 20px">';
  html += '<div style="font-size:11px;color:#8b949e;margin-bottom:4px">PROJECTED PASS</div>';
  html += '<div style="font-size:22px;font-weight:700;color:' + (state.projected_pass_rate >= 0.95 ? '#4ade80' : '#fb923c') + '">' + projRate + '</div>';
  html += '</div>';
  html += '<div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:12px 20px">';
  html += '<div style="font-size:11px;color:#8b949e;margin-bottom:4px">COST</div>';
  html += '<div style="font-size:18px;font-weight:700;color:#e2e8f0">$' + costUsd + '</div>';
  html += '</div>';
  html += '</div>';

  if (isRunning && currentBucket) {
    html += '<div style="background:#14291f;border:1px solid #166534;border-radius:6px;padding:10px 14px;margin-bottom:16px;display:flex;align-items:center;gap:10px">';
    html += '<span style="width:8px;height:8px;border-radius:50%;background:#4ade80;animation:pulse 1.4s infinite;flex-shrink:0"></span>';
    html += '<span style="color:#4ade80;font-weight:700">Running:</span>';
    html += '<span style="color:#c9d1d9"> Bucket <strong>' + esc(currentBucket) + '</strong> — Attempt ' + currentAttempt + '/' + maxAttempts + '</span>';
    html += '</div>';
  }

  // Per-bucket cards
  var buckets = state.buckets || [];
  var humanReviewBuckets = [];
  if (buckets.length) {
    html += '<div style="display:flex;flex-direction:column;gap:12px;margin-bottom:20px">';
    for (var i = 0; i < buckets.length; i++) {
      var bkt = buckets[i];
      var bStatus = bkt.status || 'pending';
      var bColor = (bStatus === 'resolved' || bStatus === 'resolved_manual' || bStatus === 'resolved_by_gemini_pro') ? '#4ade80'
                 : bStatus === 'unresolved' ? '#f87171'
                 : bStatus === 'human_review' ? '#fb923c'
                 : bStatus === 'running' ? '#60a5fa'
                 : '#8b949e';
      // Find which bucket is before this one in queue (for PENDING label)
      var runningBucketName = currentBucket || '';
      var pendingQueuePos = 0;
      if (bStatus === 'pending' && runningBucketName) {
        for (var qi = 0; qi < i; qi++) {
          if (buckets[qi].status === 'pending' || buckets[qi].status === 'running') pendingQueuePos++;
        }
      }
      var bLabel = (bStatus === 'resolved') ? '✅ RESOLVED'
                 : (bStatus === 'resolved_manual') ? '✅ RESOLVED (Manual Selection)'
                 : (bStatus === 'resolved_by_gemini_pro') ? '✅ RESOLVED (Gemini Pro)'
                 : bStatus === 'unresolved' ? '⛔ NEEDS MANUAL INPUT'
                 : bStatus === 'human_review' ? '⏸ AWAITING MANUAL INPUT'
                 : bStatus === 'running' ? '⟳ RUNNING'
                 : (bStatus === 'pending' && runningBucketName) ? '⏳ QUEUED (after ' + esc(runningBucketName) + ')'
                 : '⬜ PENDING';

      if (bStatus === 'unresolved' || bStatus === 'human_review') humanReviewBuckets.push(bkt);

      var bBorder = bStatus === 'unresolved' ? '#7f1d1d' : bStatus === 'human_review' ? '#78350f' : '#30363d';
      html += '<div style="background:#0d1117;border:1px solid ' + bBorder + ';border-radius:8px;padding:14px 18px">';

      // Bucket header row
      html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;gap:8px">';
      html += '<div style="display:flex;align-items:center;gap:10px">';
      html += '<span style="font-size:15px;font-weight:700;color:#e2e8f0">' + esc(bkt.name) + '</span>';
      html += '<span style="font-size:12px;font-weight:700;color:' + bColor + '">' + bLabel + '</span>';
      html += '</div>';
      html += '<div style="font-size:12px;color:#8b949e;display:flex;gap:14px;flex-wrap:wrap;align-items:center">';
      html += '<span>Attempts: ' + (bkt.attempts || 0) + '/' + maxAttempts + '</span>';
      if (bkt.final_combined_rate != null) {
        html += '<span>Best: ' + (bkt.final_combined_rate * 100).toFixed(1) + '%</span>';
      }
      if (bkt.started_at) {
        var elapsedStr = fmtElapsed(bkt.started_at, bkt.finished_at);
        html += '<span>⏱ ' + elapsedStr + '</span>';
      }
      html += '</div>';
      html += '</div>';

      // Attempt history table (Step 1/2/3 layout)
      var attempts = bkt.attempt_records || [];
      if (attempts.length) {
        html += '<div style="margin-bottom:10px">';
        html += '<div style="font-size:11px;color:#8b949e;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px">Attempt History</div>';
        html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">';
        html += '<thead><tr style="color:#8b949e;border-bottom:1px solid #21262d">' +
          '<th style="text-align:left;padding:4px 8px;font-weight:600">Attempt</th>' +
          '<th style="text-align:center;padding:4px 8px;font-weight:600">Step 1 (10)</th>' +
          '<th style="text-align:center;padding:4px 8px;font-weight:600">Step 2 (10)</th>' +
          '<th style="text-align:center;padding:4px 8px;font-weight:600">Step 3 (10)</th>' +
          '<th style="text-align:center;padding:4px 8px;font-weight:600">Combined</th>' +
          '<th style="text-align:center;padding:4px 8px;font-weight:600">Trend</th>' +
          '<th style="text-align:center;padding:4px 8px;font-weight:600">Outcome</th>' +
          '<th style="text-align:left;padding:4px 8px;font-weight:600">Notes</th>' +
          '<th style="text-align:center;padding:4px 8px;font-weight:600">Select</th>' +
          '</tr></thead><tbody>';
        for (var a = 0; a < attempts.length; a++) {
          var att = attempts[a];
          var attOutcome = att.outcome || 'unknown';
          var attColor = (attOutcome === 'validated' || attOutcome === 'resolved') ? '#4ade80'
                       : attOutcome === 'rejected' ? '#fb923c'
                       : attOutcome === 'error' ? '#f87171'
                       : '#9ca3af';
          var isManual = att.source === 'manual_instruction';
          var isGeminiPro = att.source === 'gemini_pro_redeploy';
          var isSelected = bkt.selected_attempt === att.attempt;
          var rowBg = isSelected ? 'background:#0f2a1a;border-left:3px solid #4ade80' : (isManual ? 'background:#0a1520' : (isGeminiPro ? 'background:#0a1a1a' : ''));
          // Trend: compare combined_rate to previous attempt (or step1 if combined same)
          var prevAtt = a > 0 ? attempts[a-1] : null;
          var trendHtml = '<span style="color:#6b7280">—</span>';
          if (prevAtt) {
            var curRate = att.combined_rate || att.step1_rate || 0;
            var prevRate = prevAtt.combined_rate || prevAtt.step1_rate || 0;
            var delta = curRate - prevRate;
            if (delta > 0.04) trendHtml = '<span style="color:#4ade80;font-weight:700">▲ +' + (delta*100).toFixed(0) + '%</span>';
            else if (delta < -0.04) trendHtml = '<span style="color:#f87171;font-weight:700">▼ ' + (delta*100).toFixed(0) + '%</span>';
            else trendHtml = '<span style="color:#6b7280">=</span>';
          }
          html += '<tr style="border-bottom:1px solid #161b22;' + rowBg + '">';
          var attLabel = (isManual ? '✏️ ' : (isGeminiPro ? '🔬 ' : '')) + 'Attempt ' + att.attempt;
          if (isSelected) attLabel = '★ ' + attLabel;
          html += '<td style="padding:5px 8px;color:#e2e8f0">' + attLabel + '</td>';
          html += '<td style="padding:5px 8px;text-align:center">' + fmtStepCell(att.step1_rate || 0, att.step1_count || 0) + '</td>';
          html += '<td style="padding:5px 8px;text-align:center">' + fmtStepCell(att.step2_rate || 0, att.step2_count || 0) + '</td>';
          html += '<td style="padding:5px 8px;text-align:center">' + fmtStepCell(att.step3_rate || 0, att.step3_count || 0) + '</td>';
          html += '<td style="padding:5px 8px;text-align:center">' + fmtStepCell(att.combined_rate || 0, (att.step1_count || 0) + (att.step2_count || 0) + (att.step3_count || 0) || 1) + '</td>';
          html += '<td style="padding:5px 8px;text-align:center">' + trendHtml + '</td>';
          html += '<td style="padding:5px 8px;text-align:center;color:' + attColor + ';font-weight:700">' + esc(attOutcome.toUpperCase()) + '</td>';
          var noteText = '';
          if (att.outcome === 'rejected' || att.outcome === 'error') {
            noteText = (att.rejection_reason || att.error || 'Unknown reason').substring(0, 70) + (att.rejection_reason && att.rejection_reason.length > 70 ? '…' : '');
          } else {
            noteText = att.analysis ? att.analysis.substring(0, 60) + (att.analysis.length > 60 ? '…' : '') : '';
            if (att.web_search_queries && att.web_search_queries.length) noteText += ' [' + att.web_search_queries.length + ' searches]';
          }
          if (att.human_instruction) noteText = '✏️ ' + att.human_instruction.substring(0, 40) + '…';
          html += '<td style="padding:5px 8px;color:#6b7280;font-size:11px">' + esc(noteText) + '</td>';
          var selectBtnStyle = isSelected
            ? 'background:#166534;color:#4ade80;border:1px solid #4ade80;padding:3px 8px;border-radius:4px;cursor:default;font-size:11px;font-weight:700'
            : 'background:#1c2333;color:#9ca3af;border:1px solid #30363d;padding:3px 8px;border-radius:4px;cursor:pointer;font-size:11px';
          var selectBtn = isSelected
            ? '<span style="' + selectBtnStyle + '">★ Selected</span>'
            : '<button style="' + selectBtnStyle + '" onclick="selectAttempt(' + JSON.stringify(bkt.name) + ',' + att.attempt + ',' + JSON.stringify(dir) + ')">Use this</button>';
          html += '<td style="padding:5px 8px;text-align:center">' + selectBtn + '</td>';
          html += '</tr>';
        }
        html += '</tbody></table></div></div>';
      }

      // Manual instruction panel (for human_review / unresolved buckets, or any non-resolved)
      if (bStatus !== 'resolved' && bStatus !== 'resolved_manual' && bStatus !== 'resolved_by_gemini_pro') {
        var selectedInfo = bkt.selected_attempt ? 'Attempt #' + bkt.selected_attempt + ' selected' : 'No attempt selected yet';
        html += '<div style="margin-top:12px;padding:12px;background:#080d16;border:1px solid #1d2d44;border-radius:6px">';
        html += '<div style="font-size:11px;color:#60a5fa;font-weight:700;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px">Manual Instruction</div>';
        html += '<textarea id="instr-' + esc(bkt.name) + '" rows="3" style="width:100%;box-sizing:border-box;background:#0d1117;border:1px solid #30363d;color:#c9d1d9;border-radius:4px;padding:8px;font-size:12px;font-family:monospace;resize:vertical" placeholder="e.g. Try removing verify_address from the GREETING node tools list and only allow it in ORDERING node..."></textarea>';
        html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;flex-wrap:wrap;gap:8px">';
        if (bkt.selected_attempt) {
          html += '<div style="display:flex;align-items:center;gap:8px">';
          html += '<span style="font-size:12px;color:#fbbf24;font-weight:700">★ ' + esc(selectedInfo) + '</span>';
          html += '<button onclick="deploySelected(' + JSON.stringify(bkt.name) + ',' + JSON.stringify(dir) + ')" style="background:#166534;color:#4ade80;border:1px solid #166534;padding:6px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:700">Deploy Attempt #' + bkt.selected_attempt + ' →</button>';
          html += '</div>';
        } else {
          html += '<span style="font-size:11px;color:#6b7280">Select an attempt above to deploy it, or re-run with a new instruction below.</span>';
        }
        html += '<button onclick="rerunBucket(' + JSON.stringify(bkt.name) + ',' + JSON.stringify(dir) + ')" style="background:#1d2d44;color:#60a5fa;border:1px solid #1d4ed8;padding:6px 14px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:700">Re-run with Instruction →</button>';
        html += '</div>';
        html += '</div>';
      }

      // Gemini Pro fix plan summary (if available)
      if (bkt.gemini_fix_plan) {
        var plan = bkt.gemini_fix_plan;
        html += '<div style="background:#0a1a1a;border:1px solid #134e4a;border-radius:6px;padding:10px 14px;margin-top:8px">';
        html += '<div style="font-size:11px;color:#2dd4bf;font-weight:700;margin-bottom:6px">🔬 GEMINI PRO ANALYSIS (with Google Search)</div>';
        if (plan.primary_failure_mode) {
          html += '<div style="margin-bottom:4px"><span style="color:#8b949e;font-size:11px">Failure Mode: </span><span style="color:#fbbf24;font-weight:700">' + esc(plan.primary_failure_mode) + '</span></div>';
        }
        if (plan.root_cause_analysis) {
          html += '<div style="color:#c9d1d9;font-size:12px;line-height:1.5;margin-bottom:6px">' + esc(plan.root_cause_analysis.substring(0, 300)) + (plan.root_cause_analysis.length > 300 ? '…' : '') + '</div>';
        }
        html += '<div style="display:flex;gap:12px;font-size:12px;flex-wrap:wrap">';
        html += '<span style="color:#8b949e">Confidence: <span style="color:#e2e8f0">' + ((plan.estimated_confidence || 0) * 100).toFixed(0) + '%</span></span>';
        html += '<span style="color:#8b949e">Fix Steps: <span style="color:#e2e8f0">' + (plan.fix_steps_count || 0) + '</span></span>';
        if (plan.web_searches && plan.web_searches.length) {
          html += '<span style="color:#8b949e">Web Searches: <span style="color:#79c0ff">' + plan.web_searches.length + '</span></span>';
        }
        if (bkt.human_review_plan_file) {
          html += '<a href="' + esc(dir) + '/' + esc(bkt.human_review_plan_file) + '" target="_blank" style="color:#58a6ff;text-decoration:none">📄 View Full Plan</a>';
        }
        if (bkt.human_review_file) {
          html += '<a href="' + esc(dir) + '/' + esc(bkt.human_review_file) + '" target="_blank" style="color:#58a6ff;text-decoration:none">📦 Download Review JSON</a>';
        }
        html += '</div>';
        if (bkt.gemini_redeploy_resolved) {
          html += '<div style="margin-top:6px;color:#4ade80;font-size:12px;font-weight:700">✅ Resolved by Gemini Pro auto-redeploy</div>';
        } else if (bkt.gemini_redeploy_attempts > 0) {
          html += '<div style="margin-top:6px;color:#f87171;font-size:12px">⛔ ' + bkt.gemini_redeploy_attempts + ' Gemini Pro redeploy attempts — still failing</div>';
        }
        html += '</div>';
      }

      // Web search queries (collapsed)
      var queries = bkt.web_search_queries || [];
      if (queries.length) {
        html += '<details style="margin-top:8px"><summary style="font-size:11px;color:#8b949e;cursor:pointer">▶ Web Searches Used (' + queries.length + ')</summary>';
        html += '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px">';
        for (var q = 0; q < queries.length; q++) {
          html += '<span style="background:#1c2333;border:1px solid #30363d;border-radius:4px;padding:2px 8px;font-size:11px;color:#79c0ff">' + esc(queries[q]) + '</span>';
        }
        html += '</div></details>';
      }

      html += '</div>'; // end bucket card
    }
    html += '</div>'; // end bucket list
  }

  // Human Investigation section — summary for buckets needing manual input
  if (humanReviewBuckets.length) {
    html += '<div style="background:#1a0505;border:2px solid #7f1d1d;border-radius:8px;padding:18px;margin-top:8px">';
    html += '<div style="font-size:14px;font-weight:700;color:#f87171;margin-bottom:8px">⛔ MANUAL INPUT REQUIRED — ' + humanReviewBuckets.length + ' bucket(s)</div>';
    html += '<p style="color:#c9d1d9;font-size:12px;margin:0 0 10px 0">';
    html += 'These buckets exhausted all automated attempts. Use the instruction panels above each bucket to provide guidance and re-run, or select the best attempt and deploy it.';
    html += '</p>';
    for (var hi = 0; hi < humanReviewBuckets.length; hi++) {
      var hrb = humanReviewBuckets[hi];
      html += '<div style="background:#0d0505;border:1px solid #7f1d1d;border-radius:6px;padding:10px 12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">';
      html += '<div>';
      html += '<div style="font-weight:700;color:#f87171;margin-bottom:4px">' + esc(hrb.name) + '</div>';
      if (hrb.gemini_fix_plan && hrb.gemini_fix_plan.primary_failure_mode) {
        html += '<div style="font-size:11px;color:#fbbf24">Failure mode: ' + esc(hrb.gemini_fix_plan.primary_failure_mode) + '</div>';
      }
      html += '</div>';
      html += '<div style="display:flex;gap:8px;flex-wrap:wrap">';
      if (hrb.human_review_file) {
        html += '<a href="' + esc(dir) + '/' + esc(hrb.human_review_file) + '" target="_blank" style="background:#7f1d1d;color:#fca5a5;padding:5px 10px;border-radius:4px;text-decoration:none;font-size:11px;font-weight:700">📦 Review JSON</a>';
      }
      if (hrb.human_review_plan_file) {
        html += '<a href="' + esc(dir) + '/' + esc(hrb.human_review_plan_file) + '" target="_blank" style="background:#134e4a;color:#99f6e4;padding:5px 10px;border-radius:4px;text-decoration:none;font-size:11px;font-weight:700">📄 Analysis Plan</a>';
      }
      html += '</div>';
      html += '</div>';
    }
    html += '</div>';
  }

  html += '</div>'; // end outer wrapper
  content.innerHTML = html;

  // Auto-refresh while running
  if (isRunning && !refreshTimer) {
    refreshTimer = setInterval(() => loadRun(currentIdx), 8000);
  } else if (!isRunning && refreshTimer) {
    clearInterval(refreshTimer); refreshTimer = null;
  }
}

// ── Shared helpers ────────────────────────────────────────────────────────────

function fmtElapsed(startedAt, finishedAt) {
  if (!startedAt) return '';
  var start = new Date(startedAt).getTime();
  var end = finishedAt ? new Date(finishedAt).getTime() : Date.now();
  var s = Math.floor((end - start) / 1000);
  if (s < 60) return s + 's';
  var m = Math.floor(s / 60); var rs = s % 60;
  return m + 'm ' + (rs > 0 ? rs + 's' : '');
}

function fmtStepCell(rate, count) {
  if (!count) return '<span style="color:#374151">—</span>';
  var pct = (rate * 100).toFixed(0) + '%';
  var col = rate >= 1.0 ? '#4ade80' : rate >= 0.7 ? '#facc15' : '#f87171';
  return '<span style="color:' + col + ';font-weight:700">' + pct + '</span><span style="color:#6b7280"> (' + count + ')</span>';
}

// ── CFV interactive actions ───────────────────────────────────────────────────

async function rerunBucket(bucketName, dir) {
  var textarea = document.getElementById('instr-' + bucketName);
  var instruction = textarea ? textarea.value.trim() : '';
  var btn = event.target;
  btn.disabled = true; btn.textContent = 'Triggering…';
  try {
    var resp = await fetch('/api/instruction', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ bucket: bucketName, instruction: instruction, run_dir: dir })
    });
    var result = await resp.json();
    if (result.ok) {
      if (textarea) textarea.value = '';
      btn.textContent = '✓ Re-run triggered!';
      btn.style.background = '#166534'; btn.style.color = '#4ade80';
      setTimeout(function() { loadRun(currentIdx); }, 3000);
    } else {
      btn.disabled = false; btn.textContent = 'Re-run with Instruction →';
      alert('Error: ' + (result.error || 'unknown'));
    }
  } catch(e) {
    btn.disabled = false; btn.textContent = 'Re-run with Instruction →';
    alert('Failed to trigger re-run: ' + e);
  }
}

async function selectAttempt(bucketName, attemptNum, dir) {
  try {
    var resp = await fetch('/api/select-attempt', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ bucket: bucketName, attempt: attemptNum, run_dir: dir })
    });
    var result = await resp.json();
    if (result.ok) {
      loadRun(currentIdx);
    } else {
      alert('Error: ' + (result.error || 'unknown'));
    }
  } catch(e) {
    alert('Failed to select attempt: ' + e);
  }
}

async function deploySelected(bucketName, dir) {
  if (!confirm('Deploy selected version for "' + bucketName + '"?\\nThis applies its patches and marks the bucket as manually resolved.')) return;
  var btn = event.target;
  btn.disabled = true; btn.textContent = 'Deploying…';
  try {
    var resp = await fetch('/api/deploy-selected', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ bucket: bucketName, run_dir: dir })
    });
    var result = await resp.json();
    if (result.ok) {
      btn.textContent = '✓ Deployed!';
      btn.style.background = '#14532d';
      setTimeout(function() { loadRun(currentIdx); }, 2000);
    } else {
      btn.disabled = false; btn.textContent = 'Deploy →';
      alert('Error: ' + (result.error || 'unknown'));
    }
  } catch(e) {
    btn.disabled = false; btn.textContent = 'Deploy →';
    alert('Failed to deploy: ' + e);
  }
}

function getHashRun() {
  // Support ?run=<dir> or #run=<dir> for deep-linking from the dashboard
  var params = new URLSearchParams(window.location.search);
  var hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  return params.get('run') || hashParams.get('run') || null;
}

function findRunByDir(dir) {
  if (!manifest || !dir) return -1;
  for (var i = 0; i < manifest.runs.length; i++) {
    if (manifest.runs[i].dir === dir || manifest.runs[i].dir === dir.replace(/\/$/, '')) return i;
  }
  return -1;
}

function getIndicesFilter() {
  // Support ?indices=<idx1>,<idx2>,... for session-scoped navigation (preferred)
  // Also support legacy ?runs=<dir1>,<dir2>,... for backward compatibility
  var params = new URLSearchParams(window.location.search);
  var indicesStr = params.get('indices');
  if (indicesStr) {
    var indices = indicesStr.split(',').map(function(s){ return parseInt(s.trim()); }).filter(function(n){ return !isNaN(n); });
    return indices.length ? indices : null;
  }
  // Fallback to dir-based filtering for backward compatibility
  var runsStr = params.get('runs');
  if (!runsStr) return null;
  var dirs = runsStr.split(',').map(function(d){ return d.trim(); }).filter(Boolean);
  return dirs.length ? dirs : null;
}

async function refresh() {
  await loadManifest();
  await refreshStatusBanner();
  if (manifest && manifest.runs.length) {
    var filter = getIndicesFilter();

    // No filter = show session overview (default landing)
    if (!filter) {
      renderOverview();
      return;
    }

    // Apply session scope filter
    if (typeof filter[0] === 'number') {
      var indexSet = filter;
      manifest._viewRuns = manifest.runs.filter(function(r){ return indexSet.indexOf(r.index) >= 0; });
    } else {
      manifest._viewRuns = manifest.runs.filter(function(r){ return filter.indexOf(r.dir) >= 0; });
    }
    if (!manifest._viewRuns.length) manifest._viewRuns = manifest.runs;

    // Show detail nav controls
    document.getElementById('btn-prev').style.display = '';
    document.getElementById('btn-next').style.display = '';
    document.getElementById('nav-step').style.display = '';
    document.getElementById('btn-overview').style.display = '';

    // On first load, respect ?run=<index/dir> or #run=<index/dir> deep-link
    if (currentIdx < 0) {
      var targetRun = getHashRun();
      if (targetRun) {
        var targetIdx = parseInt(targetRun);
        var found = -1;
        if (!isNaN(targetIdx)) {
          found = manifest._viewRuns.findIndex(function(r){ return r.index === targetIdx; });
        } else {
          found = manifest._viewRuns.findIndex(function(r){ return r.dir === targetRun || r.dir === targetRun.replace(/\/$/, ''); });
        }
        currentIdx = found >= 0 ? found : manifest._viewRuns.length - 1;
      } else {
        currentIdx = manifest._viewRuns.length - 1;
      }
    } else if (currentIdx >= manifest._viewRuns.length) {
      currentIdx = manifest._viewRuns.length - 1;
    }
    await loadRun(currentIdx);
  } else {
    updateNavBar(null);
    document.getElementById('content').innerHTML = '<div class="empty-state"><h2>No validation runs yet</h2><p>Start a validation or heal loop to see results here.</p></div>';
  }
}

refresh();
setInterval(refresh, 10000);
setInterval(refreshStatusBanner, 10000);
</script>
</body>
</html>"""


def write_dashboard(output_dir: Path = RUNS_ROOT) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(build_unified_dashboard_html())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(RUNS_ROOT / "index.html"),
                        help="Output path for index.html")
    args = parser.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_unified_dashboard_html())
    print(f"Dashboard written to {out}")
