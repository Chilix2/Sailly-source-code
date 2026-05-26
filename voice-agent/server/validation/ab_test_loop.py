"""
Demo Training Loop — ADK validation harness with live dashboard.

Primary mode is ADK-only validation over 4 phases (280 scenarios) with:
- live status JSON for the dashboard (heartbeat every 10s)
- checkpoint saved after every scenario (resume on crash)
- self-healing: auto-detect and fix rate-limit / timeout errors
- real latency summaries, 10-dimension auditor scores
- optional legacy comparison mode

Phase scenario counts: Phase1=40 | Phase2=100 | Phase3=100 | Phase4=40

Usage:
  # Run all 4 phases, 15 workers, 360s timeout:
  python -m server.training.ab_test_loop \\
      --phases 1 2 3 4 --adk-only --workers 15 --timeout 360

Dashboard HTML:
- Written to --output (default /tmp/ab_test_results) when you run a test.
- Generate without API calls:  python -m server.training.ab_test_loop --write-dashboard
- Optional checked-in copy: server/training/adk_test_dashboard/ (regen with
  --write-dashboard --output server/training/adk_test_dashboard).
"""

import argparse
import asyncio
import importlib.util
import json
import logging
import os
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

from dotenv import load_dotenv

from server.training.cost_tracker import CostTracker

load_dotenv()

logger = logging.getLogger(__name__)

# ── Failed scenario IDs (top 50 from recent validation runs) ─────────
FAILED_50 = [
    "t2-ord-01", "t2-ord-03", "t2-ord-06", "t2-ord-17", "t2-ord-20",
    "t2-ord-26", "t2-ord-31", "t2-ord-35", "t2-ord-40", "t2-ord-44",
    "t2-ord-47", "t2-ord-55", "t2-ord-58",
    "t2-res-01", "t2-res-02", "t2-res-03", "t2-res-06", "t2-res-08",
    "t2-res-09", "t2-res-10", "t2-res-11", "t2-res-12", "t2-res-13",
    "t2-res-14", "t2-res-15", "t2-res-17", "t2-res-18", "t2-res-19",
    "t2-res-20", "t2-res-21", "t2-res-22", "t2-res-25", "t2-res-26",
    "t2-res-27", "t2-res-30", "t2-res-31", "t2-res-32", "t2-res-33",
    "t2-res-36", "t2-res-60",
    "t2-tool-02", "t2-tool-03", "t2-tool-04", "t2-tool-05", "t2-tool-06",
    "t2-tool-10", "t2-tool-12", "t2-tool-13", "t2-tool-15", "t2-tool-24",
]


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * pct))))
    return float(ordered[idx])


def _bucket_failures(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    for result in results:
        for reason in result.get("one_live_failures") or []:
            counts[reason] = counts.get(reason, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"reason": reason, "count": count} for reason, count in ordered[:12]]


def _empty_live_status_stub() -> Dict[str, Any]:
    """Minimal JSON so the dashboard JS can load before any test run."""
    return {
        "running": False,
        "scenarios_done": 0,
        "scenarios_total": 0,
        "elapsed_s": 0,
        "parallel_workers": 1,
        "current_scenario_id": None,
        "failure_buckets": [],
        "summary": {
            "one_live_passes": 0,
            "one_live_rate": "--",
            "one_live_avg_composite": "--",
            "one_live_cost_usd_total": 0.0,
            "cost_usd_grand_total": 0.0,
            "one_live_avg_call_latency_ms": None,
            "one_live_avg_turn_latency_ms": None,
            "one_live_p50_turn_latency_ms": None,
            "one_live_p90_turn_latency_ms": None,
        },
        "results": [],
    }


def write_dashboard_bundle(output_dir: Path) -> Tuple[Path, Path]:
    """
    Write index.html + ab_live_status.json (stub) into output_dir.
    Returns (path_to_html, path_to_json).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "index.html"
    json_path = output_dir / "ab_live_status.json"
    html_path.write_text(_build_dashboard_html(str(output_dir)), encoding="utf-8")
    json_path.write_text(
        json.dumps(_empty_live_status_stub(), indent=2),
        encoding="utf-8",
    )
    return html_path, json_path


# Default folder inside the repo (visible in the tree; regenerate with --write-dashboard).
PACKAGE_DASHBOARD_DIR = Path(__file__).resolve().parent / "adk_test_dashboard"


def _build_dashboard_html(output_dir: str) -> str:
    """Generate a self-refreshing HTML dashboard for the Demo Training Loop."""
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Demo Training Loop — Dashboard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0b0e14; color: #d4d8e2; padding: 20px 24px; }
h1 { font-size: 1.5rem; color: #fff; margin-bottom: 4px; }
.subtitle { color: #556; font-size: 0.82rem; margin-bottom: 18px; }
.status-bar { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; margin-bottom: 18px;
  padding: 10px 16px; background: #13171f; border-radius: 8px; border: 1px solid #222736; font-size: 0.82rem; }
.status-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.status-dot.running { background: #facc15; animation: pulse 1.4s infinite; }
.status-dot.done { background: #4ade80; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.35} }
.sbar-item { display:flex; gap:6px; align-items:center; }
.sbar-label { color:#556; }
.sbar-val   { color:#e2e8f0; font-weight:600; font-variant-numeric: tabular-nums; }
.sbar-fix   { color:#f97316; }
.hb         { color:#6ee7b7; font-size:0.75rem; }
.kpi-grid { display: grid; grid-template-columns: repeat(6, minmax(0,1fr)); gap: 12px; margin-bottom: 14px; }
.kpi { background: #13171f; border: 1px solid #222736; border-radius: 10px; padding: 14px 16px; }
.kpi-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: .07em; color: #556; margin-bottom: 6px; }
.kpi-val  { font-size: 1.5rem; font-weight: 700; color: #fff; font-variant-numeric: tabular-nums; }
.kpi-sub  { font-size: 0.72rem; color: #778; margin-top: 4px; }
.kpi-bar  { height: 5px; background:#1e2433; border-radius:3px; margin-top:8px; overflow:hidden; }
.kpi-bar-fill { height:100%; background:#4ade80; border-radius:3px; transition:width .6s; }
.c-green { color: #4ade80; } .c-yellow{ color: #fde68a; } .c-blue { color: #93c5fd; }
.c-purple{ color: #c4b5fd; } .c-orange{ color: #fb923c; }
.two-col { display: grid; grid-template-columns: 1.6fr 1fr; gap: 14px; margin-bottom: 14px; }
.card { background: #13171f; border: 1px solid #222736; border-radius: 10px; padding: 16px; }
.card-title { font-size: 0.85rem; font-weight: 600; color: #c4cdd8; margin-bottom: 12px; }
.bucket-list { display:flex; flex-direction:column; gap:7px; }
.bucket-row { display:flex; justify-content:space-between; align-items:center; padding:7px 10px;
  background:#0f131a; border-radius:7px; border:1px solid #1e2433; }
.bucket-reason { font-size:0.8rem; color:#c4cdd8; }
.bucket-bar-wrap { flex:1; margin:0 12px; height:5px; background:#1e2433; border-radius:3px; overflow:hidden; }
.bucket-bar-fill { height:100%; background:#f87171; border-radius:3px; }
.bucket-cnt { font-size:0.78rem; font-variant-numeric:tabular-nums; min-width:2.2rem; text-align:right; color:#f87171; font-weight:600; }
.phase-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
.phase-box { background:#0f131a; border:1px solid #1e2433; border-radius:8px; padding:10px 12px; }
.phase-box-title { font-size:0.68rem; text-transform:uppercase; letter-spacing:.06em; color:#556; margin-bottom:6px; }
.phase-box-rate  { font-size:1.1rem; font-weight:700; color:#4ade80; }
.phase-box-sub   { font-size:0.7rem; color:#778; margin-top:2px; }
.tbl-wrap { overflow-x: auto; }
table { width:100%; border-collapse:collapse; font-size:0.78rem; min-width:1600px; }
th, td { padding: 8px 10px; text-align:left; border-bottom:1px solid #1a1e28; vertical-align:top; }
th { color:#556; font-weight:500; font-size:0.68rem; text-transform:uppercase; letter-spacing:.05em;
  background:#10131a; position:sticky; top:0; z-index:1; }
tr:hover td { background:#0f1320; }
.pass { color:#4ade80; font-weight:700; } .fail { color:#f87171; font-weight:700; }
.meta  { color:#556; font-size:0.72rem; }
.latency { font-variant-numeric:tabular-nums; color:#93c5fd; white-space:nowrap; }
.cost    { font-variant-numeric:tabular-nums; color:#fde68a; }
.cost-cum{ font-variant-numeric:tabular-nums; color:#a3a3a3; font-size:0.72rem; }
.cost-bd { font-size:0.68rem; color:#a78bfa; line-height:1.5; margin-top:2px; }
.tools   { color:#cbd5e1; font-size:0.74rem; line-height:1.4; }
.fail-reason { color:#fca5a5; font-size:0.74rem; line-height:1.35; }
.ts      { font-variant-numeric:tabular-nums; color:#556; font-size:0.7rem; white-space:nowrap; }
.persona-tag { display:inline-block; padding:2px 7px; border-radius:999px; font-size:0.68rem;
  font-weight:600; background:#1e2433; color:#c4b5fd; white-space:nowrap; }
.phase-tag { display:inline-block; padding:2px 6px; border-radius:5px; font-size:0.68rem;
  font-weight:700; background:#1a2436; color:#93c5fd; white-space:nowrap; }
.end-tag { font-size:0.7rem; padding:2px 6px; border-radius:4px; }
.end-tag.ok  { background:#14291f; color:#4ade80; }
.end-tag.warn{ background:#2a2010; color:#fbbf24; }
.end-tag.err { background:#2a1212; color:#f87171; }
.missing-tool { color:#f87171; font-size:0.72rem; }
.latency-split { font-size:0.7rem; color:#778; margin-top:2px; line-height:1.5; }
.score-val { font-variant-numeric:tabular-nums; font-weight:700; }
.score-72p { color:#4ade80; } .score-50p { color:#fbbf24; } .score-lo  { color:#f87171; }
.cost-note { color:#445; font-size:0.7rem; margin-top:10px; line-height:1.5; }
@media(max-width:1100px){ .kpi-grid{grid-template-columns:repeat(3,1fr)} .two-col{grid-template-columns:1fr} }
</style>
</head>
<body>
<h1>Demo Training Loop</h1>
<p class="subtitle">ADK Runner &middot; Gemini 2.5 Flash LLM &middot; Gemini Flash TTS &middot; Deepgram Nova-3 DE &middot; 10-dimension auditor &middot; auto-refresh 5s</p>

<div class="status-bar" id="status-bar">Loading&hellip;</div>

<div class="kpi-grid">
  <div class="kpi"><div class="kpi-label">Pass Rate</div><div class="kpi-val c-green" id="kpi-rate">--%</div><div class="kpi-sub"><span id="kpi-pass">0</span> / <span id="kpi-done">0</span></div><div class="kpi-bar"><div class="kpi-bar-fill" id="kpi-bar" style="width:0%"></div></div></div>
  <div class="kpi"><div class="kpi-label">Avg Composite</div><div class="kpi-val" id="kpi-composite">--</div><div class="kpi-sub">Pass threshold: 72</div></div>
  <div class="kpi"><div class="kpi-label">Call Latency</div><div class="kpi-val c-blue" id="kpi-call-lat">--</div><div class="kpi-sub" id="kpi-turn-lat">turn p50 / p90</div></div>
  <div class="kpi"><div class="kpi-label">Cost Total</div><div class="kpi-val c-yellow" id="kpi-cost">$0.0000</div><div class="kpi-sub" id="kpi-cost-proj"></div></div>
  <div class="kpi"><div class="kpi-label">Avg / Scenario</div><div class="kpi-val c-yellow" id="kpi-cost-avg">--</div><div class="kpi-sub" id="kpi-cost-ext"></div></div>
  <div class="kpi"><div class="kpi-label">Workers &middot; Heartbeat</div><div class="kpi-val c-purple" id="kpi-workers">--</div><div class="kpi-sub" id="kpi-autofix"></div></div>
</div>

<div class="two-col">
  <div class="card"><div class="card-title">Top Failure Buckets</div><div class="bucket-list" id="bucket-list"><div class="meta">No failures yet.</div></div></div>
  <div class="card"><div class="card-title">Phase Breakdown</div>
    <div class="phase-grid">
      <div class="phase-box"><div class="phase-box-title">Phase 1 &mdash; FAQ/40</div><div class="phase-box-rate" id="ph1-rate">--</div><div class="phase-box-sub" id="ph1-sub">0/40</div></div>
      <div class="phase-box"><div class="phase-box-title">Phase 2 &mdash; Tools/100</div><div class="phase-box-rate" id="ph2-rate">--</div><div class="phase-box-sub" id="ph2-sub">0/100</div></div>
      <div class="phase-box"><div class="phase-box-title">Phase 3 &mdash; Chaos/100</div><div class="phase-box-rate" id="ph3-rate">--</div><div class="phase-box-sub" id="ph3-sub">0/100</div></div>
      <div class="phase-box"><div class="phase-box-title">Phase 4 &mdash; Edge/40</div><div class="phase-box-rate" id="ph4-rate">--</div><div class="phase-box-sub" id="ph4-sub">0/40</div></div>
    </div>
  </div>
</div>

<div class="card" style="margin-bottom:24px">
  <div class="card-title">Per-Scenario Results <span class="meta" id="tbl-count"></span></div>
  <div class="tbl-wrap">
  <table>
    <thead><tr>
      <th>Completed At</th><th>Scenario ID &amp; Description</th><th>Phase</th><th>Persona</th>
      <th>Result</th><th>Score</th><th>Call Latency</th><th>Bot / Caller Avg</th>
      <th>Turns</th><th>End Reason</th><th>Expected &rarr; Called</th><th>Missing Tools</th>
      <th>Scenario $</th><th>Cumulative $</th><th>Cost Breakdown</th>
      <th>Failure Reasons</th><th>Node Path</th>
    </tr></thead>
    <tbody id="results-body"></tbody>
  </table>
  </div>
  <p class="cost-note">Costs estimated: Gemini LLM tokens + GPT-4o-mini tokens + Deepgram audio seconds + Google TTS characters. Bot TTS: Gemini 2.5 Flash TTS (default). See cost_tracker.py for rates.</p>
</div>

<script>
function esc(s){if(s==null||s==='')return '';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function fmtMs(v){if(v==null||v==='')return '<span class="meta">&mdash;</span>';var n=Number(v);if(isNaN(n))return '<span class="meta">&mdash;</span>';return '<span class="latency">'+(n>=60000?(n/60000).toFixed(1)+'m':n>=1000?(n/1000).toFixed(1)+'s':n.toFixed(0)+'ms')+'</span>';}
function fmtScore(v){if(v==null)return '<span class="meta">&mdash;</span>';var n=Number(v);if(isNaN(n))return '<span class="meta">&mdash;</span>';var c=n>=72?'score-72p':n>=50?'score-50p':'score-lo';return '<span class="score-val '+c+'">'+n.toFixed(1)+'</span>';}
function fmtUsd(v){if(v==null||v==='')return '<span class="meta">&mdash;</span>';var n=Number(v);if(isNaN(n))return '<span class="meta">&mdash;</span>';return '<span class="cost">$'+n.toFixed(4)+'</span>';}
function fmtCostBd(bd){if(!bd)return '';var p=[];if(bd.gemini_calls)p.push('Gemini x'+bd.gemini_calls+' ('+((bd.gemini_input_tokens||0)+(bd.gemini_output_tokens||0))+'tok)');if(bd.openai_calls)p.push('GPT x'+bd.openai_calls+' ('+(bd.openai_prompt_tokens||0)+'+'+( bd.openai_completion_tokens||0)+'tok)');if(bd.deepgram_requests)p.push('DG x'+bd.deepgram_requests+' '+Number(bd.deepgram_audio_seconds||0).toFixed(1)+'s');if(bd.caller_tts_chars)p.push('CalTTS '+bd.caller_tts_chars+'ch');if(bd.bot_tts_chars)p.push('BotTTS '+bd.bot_tts_chars+'ch');return '<div class="cost-bd">'+p.join('<br>')+'</div>';}
function fmtEndReason(v){if(!v)return '<span class="meta">&mdash;</span>';var s=esc(v);var c=(v==='end_call_tool'||v==='goodbye')?'ok':(v==='max_turns'||v==='TIMEOUT')?'warn':'err';return '<span class="end-tag '+c+'">'+s+'</span>';}
function fmtPersona(v){if(!v)return '<span class="meta">&mdash;</span>';return '<span class="persona-tag">'+esc(v)+'</span>';}
function fmtPhaseTag(v,cat){if(!v)return '<span class="meta">&mdash;</span>';return '<span class="phase-tag">'+esc(v)+'</span>'+(cat?'<div class="meta" style="margin-top:3px">'+esc(cat)+'</div>':'');}
function fmtTs(v){if(!v)return '<span class="meta">&mdash;</span>';try{var d=new Date(v);return '<span class="ts">'+d.toLocaleTimeString()+'</span>';}catch(e){return '<span class="meta">&mdash;</span>';}}
function fmtMissing(arr){if(!arr||!arr.length)return '<span class="c-green meta">&#x2713; none</span>';return '<span class="missing-tool">'+arr.map(esc).join('<br>')+'</span>';}
function fmtTools(exp,got){var e=exp&&exp.length?esc(exp.join(', ')):'<span class="meta">&mdash;</span>';var g=got&&got.length?esc(got.join(', ')):'<span class="meta">&mdash;</span>';return '<div class="tools"><span class="meta">exp:</span> '+e+'<br><span class="meta">got:</span> '+g+'</div>';}
function fmtFail(arr){if(!arr||!arr.length)return '<span class="c-green meta">&mdash;</span>';return '<div class="fail-reason">'+arr.map(esc).join('<br>')+'</div>';}
function fmtLatSplit(bot,caller){if(bot==null&&caller==null)return '';var b=bot!=null?Number(bot).toFixed(0)+'ms':'&mdash;';var c=caller!=null?Number(caller).toFixed(0)+'ms':'&mdash;';return '<div class="latency-split">bot '+b+' &middot; caller '+c+'</div>';}

async function refresh(){
  try{
    const resp=await fetch('ab_live_status.json?t='+Date.now());
    const d=await resp.json();
    const done=d.scenarios_done||0,total=d.scenarios_total||0,running=d.running;
    const elapsed=d.elapsed_s?(Number(d.elapsed_s)<60?d.elapsed_s.toFixed(0)+'s':(d.elapsed_s/60).toFixed(1)+'m'):'--';
    const s=d.summary||{};
    var olt=s.one_live_cost_usd_total!=null?Number(s.one_live_cost_usd_total):0;
    var pw=d.parallel_workers||1,hb=d.heartbeat||0,fixes=d.auto_fix_count||0;
    var fixStr=fixes>0?' <span class="sbar-fix">&middot; '+fixes+' auto-fix'+(fixes>1?'es':'')+'</span>':'';
    var cur=d.current_scenario_id?' &middot; <span class="sbar-label">running: </span><span class="sbar-val">'+esc(d.current_scenario_id)+'</span>':'';
    document.getElementById('status-bar').innerHTML=
      '<div class="status-dot '+(running?'running':'done')+'"></div>'+
      '<span class="sbar-val">'+(running?'Running':'Complete')+'</span>'+
      '<div class="sbar-item"><span class="sbar-label">Scenarios:</span><span class="sbar-val">'+done+' / '+total+'</span></div>'+
      '<div class="sbar-item"><span class="sbar-label">Elapsed:</span><span class="sbar-val">'+elapsed+'</span></div>'+
      '<div class="sbar-item"><span class="sbar-label">Workers:</span><span class="sbar-val">'+pw+'</span></div>'+
      '<div class="sbar-item hb">HB #'+hb+'</div>'+
      '<div class="sbar-item"><span class="sbar-label">Cost:</span><span class="cost">$'+olt.toFixed(4)+'</span></div>'+
      fixStr+cur;

    var rate=s.one_live_rate||'0%';
    document.getElementById('kpi-rate').textContent=s.one_live_rate||'--%';
    document.getElementById('kpi-pass').textContent=s.one_live_passes||0;
    document.getElementById('kpi-done').textContent=done;
    document.getElementById('kpi-bar').style.width=rate;
    document.getElementById('kpi-composite').textContent=s.one_live_avg_composite||'--';
    document.getElementById('kpi-call-lat').textContent=s.one_live_avg_call_latency_ms!=null?(Number(s.one_live_avg_call_latency_ms)/1000).toFixed(1)+'s':'--';
    document.getElementById('kpi-turn-lat').textContent='p50 '+(s.one_live_p50_turn_latency_ms!=null?Number(s.one_live_p50_turn_latency_ms).toFixed(0)+'ms':'--')+' / p90 '+(s.one_live_p90_turn_latency_ms!=null?Number(s.one_live_p90_turn_latency_ms).toFixed(0)+'ms':'--');
    document.getElementById('kpi-cost').textContent='$'+olt.toFixed(4);
    var avgCost=done>0?olt/done:null;
    document.getElementById('kpi-cost-avg').textContent=avgCost!=null?'$'+avgCost.toFixed(4):'--';
    document.getElementById('kpi-cost-proj').textContent=avgCost!=null&&total>0?'Projected: $'+(avgCost*total).toFixed(2):'';
    document.getElementById('kpi-cost-ext').textContent=avgCost!=null&&(total-done)>0?'~$'+(avgCost*(total-done)).toFixed(2)+' remaining':'';
    document.getElementById('kpi-workers').innerHTML=pw+' workers &middot; HB#'+hb;
    document.getElementById('kpi-autofix').textContent=fixes>0?fixes+' auto-fix(es)':'No fixes needed';

    var bl=document.getElementById('bucket-list');bl.innerHTML='';
    var buckets=d.failure_buckets||[],maxCnt=buckets.length?buckets[0].count:1;
    if(!buckets.length){bl.innerHTML='<div class="meta">No failures yet.</div>';}
    else{for(var b of buckets){bl.innerHTML+='<div class="bucket-row"><div class="bucket-reason">'+esc(b.reason)+'</div><div class="bucket-bar-wrap"><div class="bucket-bar-fill" style="width:'+(b.count/maxCnt*100).toFixed(0)+'%"></div></div><div class="bucket-cnt">'+b.count+'</div></div>';}}

    var results=d.results||[];
    var phM={1:{p:0,t:0},2:{p:0,t:0},3:{p:0,t:0},4:{p:0,t:0}};
    for(var r of results){if(!r)continue;var ph=r.phase?parseInt(r.phase.replace('phase','').replace(/\D/g,'')):0;if(ph>=1&&ph<=4){phM[ph].t++;if(r.one_live_pass)phM[ph].p++;}}
    for(var pi=1;pi<=4;pi++){var pm=phM[pi];document.getElementById('ph'+pi+'-rate').textContent=pm.t>0?(pm.p/pm.t*100).toFixed(0)+'%':'--';document.getElementById('ph'+pi+'-sub').textContent=pm.p+'/'+pm.t;}

    var tbody=document.getElementById('results-body');tbody.innerHTML='';
    document.getElementById('tbl-count').textContent=results.length?'('+results.length+' completed)':'';
    var cumCost=0;
    for(var r of results){
      if(!r)continue;
      var sc=r.one_live_cost_usd!=null?Number(r.one_live_cost_usd):0;if(!isNaN(sc))cumCost+=sc;
      var tr=document.createElement('tr');
      tr.innerHTML=
        '<td>'+fmtTs(r.completed_at)+'</td>'+
        '<td style="white-space:nowrap"><strong>'+esc(r.scenario_id)+'</strong>'+(r.description?'<div class="meta" style="max-width:11rem;white-space:normal">'+esc(r.description)+'</div>':'')+'</td>'+
        '<td>'+fmtPhaseTag(r.phase,r.category)+'</td>'+
        '<td>'+fmtPersona(r.persona)+'</td>'+
        '<td class="'+(r.one_live_pass?'pass':'fail')+'">'+(r.one_live_pass?'&#x2713; PASS':'&#x2717; FAIL')+'</td>'+
        '<td>'+fmtScore(r.one_live_composite)+'</td>'+
        '<td>'+fmtMs(r.one_live_latency_ms)+'<div class="meta" style="margin-top:2px">avg '+fmtMs(r.one_live_avg_turn_latency_ms)+' &middot; max '+fmtMs(r.one_live_max_turn_latency_ms)+'</div></td>'+
        '<td>'+fmtLatSplit(r.one_live_avg_bot_latency_ms,r.one_live_avg_caller_latency_ms)+'</td>'+
        '<td class="mono">'+(r.one_live_turns!=null?r.one_live_turns:'--')+'</td>'+
        '<td>'+fmtEndReason(r.one_live_end_reason)+'</td>'+
        '<td>'+fmtTools(r.expected_tools,r.one_live_tools)+'</td>'+
        '<td>'+fmtMissing(r.one_live_missing_tools)+'</td>'+
        '<td>'+fmtUsd(r.one_live_cost_usd)+'</td>'+
        '<td><span class="cost-cum">$'+cumCost.toFixed(4)+'</span></td>'+
        '<td>'+fmtCostBd(r.one_live_cost_breakdown)+'</td>'+
        '<td>'+fmtFail(r.one_live_failures)+'</td>'+
        '<td><span class="meta" style="font-size:0.7rem">'+esc(r.phases||'&mdash;')+'</span></td>';
      tbody.appendChild(tr);
    }
  }catch(e){console.error('Refresh error',e);}
}
setInterval(refresh,5000);
refresh();
</script>
</body>
</html>"""

def _conv_result_to_audit_turns(result) -> List[Dict]:
    """Convert ConvResult turns to the dict format audit_call expects."""
    audit_turns = []
    for t in result.turns:
        audit_turns.append({
            "turn_idx": t.turn_idx,
            "user_utterance": t.caller_text,
            "stt_transcript": t.stt_transcript,
            "wer": t.wer,
            "llm_response": t.bot_response,
            "tts_bytes": t.tts_bytes,
            "tools_called": t.tools_called,
            "latency_ms": t.total_latency_ms,
            "passed": t.passed,
        })
    return audit_turns


@dataclass
class RunnerStack:
    """One isolated Tier2AudioRunner + both conversation loops (safe for concurrent scenarios)."""

    runner: Any
    current_loop: Any
    one_live_loop: Any


import re as _re_module

# --------------------------------------------------------------------------- #
# Self-heal rules (ported from audio_training_loop.py)
# --------------------------------------------------------------------------- #

_AUTO_FIX_RULES = [
    # (error substring, description, fix_method_name)
    ("429", "rate-limit — adding 20s cooldown", "_fix_rate_limit"),
    ("quota", "quota exceeded — adding 30s cooldown", "_fix_quota"),
    ("timeout", "timeout — bumping call_timeout by 30s", "_fix_timeout"),
    ("ResourceExhausted", "resource exhausted — adding 20s cooldown", "_fix_rate_limit"),
    ("DeadlineExceeded", "deadline exceeded — bumping call_timeout by 30s", "_fix_timeout"),
]


class ABTestLoop:
    """Demo Training Loop — ADK validation harness with 4-phase support."""

    def __init__(
        self,
        output_dir: str = "/tmp/ab_test_results",
        max_scenarios: int = 50,
        call_timeout: float = 360.0,
        parallel_workers: int = 15,
        phases: Optional[List[int]] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_scenarios = max_scenarios
        self.call_timeout = call_timeout
        self.parallel_workers = max(1, parallel_workers)
        self.phases = phases  # None → legacy behavior
        self.results: List[Dict] = []
        self._start_time = None
        self.adk_only = False
        self.current_scenario_id: Optional[str] = None
        self._runner_pool: Optional[asyncio.Queue] = None
        self._scenario_slots: Optional[List[Optional[Dict]]] = None
        self._status_lock: Optional[asyncio.Lock] = None
        # Heartbeat / self-heal state
        self._heartbeat: int = 0
        self._cooldown_secs: float = 0.0
        self._auto_fixes: List[str] = []
        # Checkpoint: scenario IDs already completed (for crash recovery)
        self._completed_ids: set = set()
        self._checkpoint_lock: Optional[asyncio.Lock] = None

    # ---------------------------------------------------------------------- #
    # Self-heal helpers
    # ---------------------------------------------------------------------- #

    def _detect_and_fix(self, error_msg: str) -> Optional[str]:
        """Match error against AUTO_FIX_RULES and apply the first matching fix."""
        for pattern, description, method_name in _AUTO_FIX_RULES:
            if pattern.lower() in error_msg.lower():
                fix_method = getattr(self, method_name, None)
                if fix_method:
                    fix_method()
                msg = f"[INFRA-FIX] {description} — triggered by: {error_msg[:60]}"
                logger.warning(f"⚡ {msg}")
                self._auto_fixes.append(
                    f"{datetime.now().strftime('%H:%M:%S')} {msg}"
                )
                return msg
        return None

    def _fix_rate_limit(self):
        self._cooldown_secs = min(120.0, self._cooldown_secs + 20.0)
        logger.warning(f"  cooldown now {self._cooldown_secs:.0f}s")

    def _fix_quota(self):
        self._cooldown_secs = min(120.0, self._cooldown_secs + 30.0)
        logger.warning(f"  cooldown now {self._cooldown_secs:.0f}s")

    def _fix_timeout(self):
        self.call_timeout = min(600.0, self.call_timeout + 30.0)
        logger.warning(f"  call_timeout bumped to {self.call_timeout:.0f}s")

    # ---------------------------------------------------------------------- #
    # Heartbeat
    # ---------------------------------------------------------------------- #

    async def _heartbeat_loop(self):
        """Emit a heartbeat tick every 10 seconds and refresh the live status JSON."""
        while True:
            await asyncio.sleep(10)
            self._heartbeat += 1
            await self._flush_live_status(running=True)

    # ---------------------------------------------------------------------- #
    # Checkpoint (crash recovery)
    # ---------------------------------------------------------------------- #

    def _checkpoint_path(self) -> Path:
        return self.output_dir / "checkpoint.json"

    def _load_checkpoint(self):
        """Restore completed IDs from a previous run (skip already-done scenarios)."""
        cp = self._checkpoint_path()
        if not cp.exists():
            return
        try:
            data = json.loads(cp.read_text())
            self._completed_ids = set(data.get("completed_ids", []))
            self.call_timeout = data.get("call_timeout", self.call_timeout)
            self._cooldown_secs = data.get("cooldown_secs", 0.0)
            if self._completed_ids:
                logger.info(
                    f"✅ Checkpoint loaded — {len(self._completed_ids)} already completed"
                )
        except Exception as e:
            logger.warning(f"Checkpoint load failed: {e}")

    async def _save_checkpoint(self):
        """Atomically write checkpoint after every completed scenario."""
        cp = self._checkpoint_path()
        tmp = cp.with_suffix(".tmp")
        data = {
            "completed_ids": list(self._completed_ids),
            "call_timeout": self.call_timeout,
            "cooldown_secs": self._cooldown_secs,
            "saved_at": datetime.now().isoformat(),
            "auto_fixes": self._auto_fixes[-20:],
        }
        if self._checkpoint_lock:
            async with self._checkpoint_lock:
                tmp.write_text(json.dumps(data, indent=2))
                tmp.replace(cp)
        else:
            tmp.write_text(json.dumps(data, indent=2))
            tmp.replace(cp)

    def _make_runner_stack(self) -> RunnerStack:
        """Build one isolated Tier2AudioRunner + ConversationLoop + ADKRunner."""
        from server.training.tier2_runner import Tier2AudioRunner
        from server.training.conversation_loop import ConversationLoop
        from server.training.adk_runner import ADKRunner

        project_id = os.environ.get("GCP_PROJECT_ID", "sailly-voice-agent-eu")
        deepgram_key = os.environ.get("DEEPGRAM_API_KEY", "")
        openai_key = os.environ.get("OPENAI_API_KEY", "")

        runner = Tier2AudioRunner(
            google_project_id=project_id,
            deepgram_api_key=deepgram_key,
            gemini_model="gemini-2.5-flash",
            temperature=0.0,
        )
        runner._init_clients()

        current_loop = ConversationLoop(
            audio_injector=runner.audio_injector,
            gemini_runner=runner,
            openai_api_key=openai_key,
        )
        one_live_loop = ADKRunner(
            audio_injector=runner.audio_injector,
            gemini_runner=runner,
            openai_api_key=openai_key,
        )
        return RunnerStack(
            runner=runner, current_loop=current_loop, one_live_loop=one_live_loop
        )

    def _attach_cost_tracker(
        self, tracker: Optional[CostTracker], stack: Optional[RunnerStack] = None
    ) -> None:
        """Point runner + loops at the cost tracker for the active scenario."""
        if stack is not None:
            stack.runner.set_cost_tracker(tracker)
            stack.one_live_loop.cost_tracker = tracker
            stack.current_loop.cost_tracker = tracker
            return
        self._runner.set_cost_tracker(tracker)
        self.one_live_loop.cost_tracker = tracker
        if hasattr(self, "current_loop"):
            self.current_loop.cost_tracker = tracker

    def _init_runners(self):
        """Initialize a single runner stack (sequential mode)."""
        stack = self._make_runner_stack()
        self._runner = stack.runner
        self.current_loop = stack.current_loop
        self.one_live_loop = stack.one_live_loop

    _PHASE_MODULE_MAP = {
        1: ("server.scenarios.phase1_scenarios", "PHASE1_SCENARIOS"),
        2: ("server.scenarios.phase2_scenarios", "PHASE2_SCENARIOS"),
        3: ("server.scenarios.phase3_scenarios", "PHASE3_SCENARIOS"),
        4: ("server.scenarios.phase4_scenarios", "PHASE4_SCENARIOS"),
    }

    def _load_scenarios(self, scenario_ids: Optional[List[str]] = None):
        """Load scenarios — phase mode or legacy targeted mode.

        Phase mode (--phases 1 2 3 4): loads from generated phase scenario files.
        Legacy mode (no --phases): loads tier2 + fix_validation filtered by IDs.
        """
        import importlib

        # ── Phase mode ────────────────────────────────────────────────────────
        if self.phases:
            scenarios = []
            for p in sorted(self.phases):
                if p not in self._PHASE_MODULE_MAP:
                    logger.warning(f"Unknown phase {p}, skipping")
                    continue
                mod_name, attr = self._PHASE_MODULE_MAP[p]
                try:
                    mod = importlib.import_module(mod_name)
                    phase_scenarios = getattr(mod, attr)
                    scenarios.extend(phase_scenarios)
                    logger.info(f"  Phase {p}: {len(phase_scenarios)} scenarios loaded")
                except (ImportError, AttributeError) as e:
                    logger.error(f"  Phase {p}: failed to load ({e})")
            # Also load production failure scenarios if the catalog exists
            prod_failures_path = (
                Path(__file__).parent.parent / "scenarios" / "production_failures.py"
            )
            if prod_failures_path.exists():
                try:
                    spec = importlib.util.spec_from_file_location(
                        "server.scenarios.production_failures",
                        str(prod_failures_path),
                    )
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    prod_scens = getattr(mod, "PRODUCTION_FAILURE_SCENARIOS", [])
                    scenarios.extend(prod_scens)
                    if prod_scens:
                        logger.info(
                            f"  Production failures: {len(prod_scens)} captured scenarios loaded"
                        )
                except Exception as e:
                    logger.warning(f"  Production failures: failed to load ({e})")

            logger.info(
                f"Demo Training Loop: {len(scenarios)} scenarios "
                f"(phases {sorted(self.phases)})"
            )
            return scenarios

        # ── Legacy targeted mode ──────────────────────────────────────────────
        from server.scenarios.tier2_scenarios import TIER2_SCENARIOS
        from server.scenarios.fix_validation_scenarios import FIX_VALIDATION_SCENARIOS

        ids = set(scenario_ids or FAILED_50)
        catalog = list(TIER2_SCENARIOS) + list(FIX_VALIDATION_SCENARIOS)
        seen = set()
        scenarios = []
        for scenario in catalog:
            if scenario.id in ids and scenario.id not in seen:
                scenarios.append(scenario)
                seen.add(scenario.id)

        if len(scenarios) < len(ids):
            found = {s.id for s in scenarios}
            missing = ids - found
            logger.warning(f"Missing {len(missing)} scenarios: {sorted(missing)[:5]}...")

        if not getattr(self, "_skip_extras", False):
            from server.scenarios.ab_test_scenarios import (
                PHASE3_SCENARIOS as _P3,
                REAL_LIVE_SCENARIOS as _RL,
            )
            scenarios += _P3
            scenarios += _RL
            logger.info(
                f"Loaded {len(scenarios)} scenarios "
                f"(tier2: {len([s for s in scenarios if s.id.startswith('t2-')])}, "
                f"phase3: {len(_P3)}, real-live: {len(_RL)})"
            )
        else:
            logger.info(f"Loaded {len(scenarios)} scenarios (targeted, no extras)")

        return scenarios

    def _write_live_status(
        self,
        running: bool = True,
        results_snapshot: Optional[List[Dict]] = None,
    ):
        """Write live status JSON for the dashboard."""
        results = results_snapshot if results_snapshot is not None else self.results
        done = len(results)
        elapsed = time.time() - self._start_time if self._start_time else 0

        one_live_passes = sum(1 for r in results if r.get("one_live_pass"))
        one_live_composites = [
            r["one_live_composite"]
            for r in results
            if r.get("one_live_composite") is not None
        ]
        ol_cost = sum(float(r.get("one_live_cost_usd") or 0) for r in results)
        call_lats = [
            float(r.get("one_live_latency_ms") or 0)
            for r in results
            if r.get("one_live_latency_ms") is not None
        ]
        turn_avg_lats = [
            float(r.get("one_live_avg_turn_latency_ms") or 0)
            for r in results
            if r.get("one_live_avg_turn_latency_ms") is not None
        ]

        status = {
            "running": running,
            "scenarios_done": done,
            "scenarios_total": self.max_scenarios,
            "elapsed_s": elapsed,
            "parallel_workers": self.parallel_workers,
            "heartbeat": self._heartbeat,
            "auto_fix_count": len(self._auto_fixes),
            "auto_fixes_recent": self._auto_fixes[-5:],
            "cooldown_secs": self._cooldown_secs,
            "call_timeout": self.call_timeout,
            "current_scenario_id": self.current_scenario_id,
            "failure_buckets": _bucket_failures(results),
            "summary": {
                "one_live_passes": one_live_passes,
                "one_live_rate": f"{one_live_passes/done*100:.1f}%" if done else "--",
                "one_live_avg_composite": f"{sum(one_live_composites)/len(one_live_composites):.1f}" if one_live_composites else "--",
                "one_live_cost_usd_total": round(ol_cost, 4),
                "cost_usd_grand_total": round(ol_cost, 4),
                "one_live_avg_call_latency_ms": round(sum(call_lats) / len(call_lats), 1) if call_lats else None,
                "one_live_avg_turn_latency_ms": round(sum(turn_avg_lats) / len(turn_avg_lats), 1) if turn_avg_lats else None,
                "one_live_p50_turn_latency_ms": round(_percentile(turn_avg_lats, 0.50), 1) if turn_avg_lats else None,
                "one_live_p90_turn_latency_ms": round(_percentile(turn_avg_lats, 0.90), 1) if turn_avg_lats else None,
            },
            "results": results,
        }

        with open(self.output_dir / "ab_live_status.json", "w") as f:
            json.dump(status, f, indent=2)

    async def _flush_live_status(self, running: bool = True):
        """Refresh dashboard JSON (locked when running scenarios in parallel)."""
        if self.parallel_workers <= 1:
            self._write_live_status(running=running)
            return
        assert self._status_lock is not None and self._scenario_slots is not None
        async with self._status_lock:
            snap = [r for r in self._scenario_slots if r is not None]
            self._write_live_status(running=running, results_snapshot=snap)

    async def _run_one_scenario(
        self,
        scenario,
        idx: int,
        total: int,
        stack: Optional[RunnerStack] = None,
    ):
        """Run a single scenario through the ADK runner, with optional legacy comparison."""
        from server.training.call_auditor_de import audit_call

        if stack is not None:
            runner = stack.runner
            current = stack.current_loop
            one_live = stack.one_live_loop
        else:
            runner = self._runner
            current = self.current_loop
            one_live = self.one_live_loop

        sid = scenario.id
        expected = list(getattr(scenario, "expected_tools", []) or [])
        if self.parallel_workers <= 1:
            self.current_scenario_id = sid
        await self._flush_live_status(running=True)
        logger.info(f"[{idx+1}/{total}] {sid} — running ADK validation...")

        result = {
            "scenario_id": sid,
            "expected_tools": expected,
            "phase": getattr(scenario, "phase", ""),
            "category": getattr(scenario, "category", ""),
            "persona": getattr(scenario, "persona", "") or "",
            "description": getattr(scenario, "description", "")[:80],
            "started_at": datetime.now().isoformat(),
        }

        # ── One-Live Loop ─────────────────────────────────────────
        ct_ol = CostTracker()
        self._attach_cost_tracker(ct_ol, stack)
        try:
            try:
                one_live_result = await asyncio.wait_for(
                    one_live.run(scenario, phase=2, run_number=1),
                    timeout=self.call_timeout,
                )
                audit_turns_a = _conv_result_to_audit_turns(one_live_result)
                audit_a = audit_call(
                    scenario_id=sid,
                    phase=2,
                    run_number=1,
                    turns=audit_turns_a,
                    expected_tools=expected,
                    total_latency_ms=one_live_result.total_latency_ms,
                )
                result["one_live_pass"] = audit_a.passed
                result["one_live_composite"] = round(audit_a.composite, 1)
                result["one_live_tools"] = one_live_result.tools_called
                result["one_live_turns"] = len(one_live_result.turns)
                result["one_live_latency_ms"] = round(one_live_result.total_latency_ms, 1)
                turn_lats = [float(t.total_latency_ms) for t in one_live_result.turns]
                result["one_live_avg_turn_latency_ms"] = round(sum(turn_lats) / len(turn_lats), 1) if turn_lats else None
                result["one_live_max_turn_latency_ms"] = round(max(turn_lats), 1) if turn_lats else None
                result["one_live_avg_bot_latency_ms"] = round(sum(float(t.bot_latency_ms) for t in one_live_result.turns) / len(one_live_result.turns), 1) if one_live_result.turns else None
                result["one_live_avg_caller_latency_ms"] = round(sum(float(t.caller_latency_ms) for t in one_live_result.turns) / len(one_live_result.turns), 1) if one_live_result.turns else None
                result["one_live_missing_tools"] = list(audit_a.tools_missing)
                result["one_live_end_reason"] = getattr(one_live_result, "end_reason", "")
                hist = getattr(one_live_result, "_phase_history", None) or getattr(
                    one_live_result, "_node_history", None
                ) or []
                result["phases"] = " → ".join(hist[:12])
                if not audit_a.passed:
                    result["one_live_failures"] = audit_a.failure_reasons[:8]
            except asyncio.TimeoutError:
                result["one_live_pass"] = False
                result["one_live_composite"] = 0
                result["one_live_tools"] = []
                result["one_live_turns"] = 0
                result["one_live_latency_ms"] = round(self.call_timeout * 1000, 1)
                result["one_live_avg_turn_latency_ms"] = None
                result["one_live_max_turn_latency_ms"] = None
                result["one_live_avg_bot_latency_ms"] = None
                result["one_live_avg_caller_latency_ms"] = None
                result["one_live_missing_tools"] = list(expected)
                result["phases"] = "TIMEOUT"
                result["one_live_failures"] = [f"TIMEOUT (>{self.call_timeout:.0f}s)"]
                logger.warning(f"  {sid} One-Live: TIMEOUT")
            except Exception as e:
                result["one_live_pass"] = False
                result["one_live_composite"] = 0
                result["one_live_tools"] = []
                result["one_live_turns"] = 0
                result["one_live_latency_ms"] = None
                result["one_live_avg_turn_latency_ms"] = None
                result["one_live_max_turn_latency_ms"] = None
                result["one_live_avg_bot_latency_ms"] = None
                result["one_live_avg_caller_latency_ms"] = None
                result["one_live_missing_tools"] = list(expected)
                result["phases"] = "ERROR"
                result["one_live_failures"] = [f"ERROR: {e!s}"[:200]]
                logger.error(f"  {sid} One-Live error: {e}")
        finally:
            result["one_live_cost_usd"] = round(ct_ol.estimate_usd(), 4)
            result["one_live_cost_breakdown"] = ct_ol.to_dict()

        # ── Current Loop ──────────────────────────────────────────
        if not self.adk_only:
            runner._active_prompt_override = None

            ct_cur = CostTracker()
            self._attach_cost_tracker(ct_cur, stack)
            try:
                try:
                    current_result = await asyncio.wait_for(
                        current.run(scenario, phase=2, run_number=1),
                        timeout=self.call_timeout,
                    )
                    audit_turns_b = _conv_result_to_audit_turns(current_result)
                    audit_b = audit_call(
                        scenario_id=sid,
                        phase=2,
                        run_number=1,
                        turns=audit_turns_b,
                        expected_tools=expected,
                        total_latency_ms=current_result.total_latency_ms,
                    )
                    result["current_pass"] = audit_b.passed
                    result["current_composite"] = round(audit_b.composite, 1)
                    result["current_tools"] = current_result.tools_called
                    result["current_turns"] = len(current_result.turns)
                    if not audit_b.passed:
                        result["current_failures"] = audit_b.failure_reasons[:3]
                except asyncio.TimeoutError:
                    result["current_pass"] = False
                    result["current_composite"] = 0
                    result["current_tools"] = []
                    result["current_turns"] = 0
                    result["current_failures"] = [f"TIMEOUT (>{self.call_timeout:.0f}s)"]
                    logger.warning(f"  {sid} Current: TIMEOUT")
                except Exception as e:
                    result["current_pass"] = False
                    result["current_composite"] = 0
                    result["current_tools"] = []
                    result["current_turns"] = 0
                    result["current_failures"] = [f"ERROR: {e!s}"[:200]]
                    logger.error(f"  {sid} Current error: {e}")
            finally:
                result["current_cost_usd"] = round(ct_cur.estimate_usd(), 4)
                result["current_cost_breakdown"] = ct_cur.to_dict()
        else:
            # ADK-only mode: skip Current Loop
            result["current_pass"] = None
            result["current_composite"] = None
            result["current_tools"] = None
            result["current_turns"] = None
            result["current_cost_usd"] = None
            result["current_cost_breakdown"] = None

        self._attach_cost_tracker(None, stack)

        # Winner / status label
        a_score = result.get("one_live_composite", 0) or 0
        b_score = result.get("current_composite", 0) or 0
        result["winner"] = "ADK" if self.adk_only else ("One-Live" if a_score > b_score else "Current" if b_score > a_score else "Tie")

        # Log
        a_status = "PASS" if result.get("one_live_pass") else "FAIL"
        ol_f = result.get("one_live_failures") or []
        ol_note = f" | OL: {ol_f[0][:80]}" if ol_f else ""
        ol_usd = result.get("one_live_cost_usd", 0)
        if self.adk_only:
            logger.info(
                f"  {sid}: ADK={a_score:.0f} {a_status}"
                f" | call {result.get('one_live_latency_ms') or 0:.0f}ms"
                f" | avg turn {result.get('one_live_avg_turn_latency_ms') or 0:.0f}ms"
                f" | cost ${ol_usd:.4f}{ol_note}"
            )
        else:
            b_status = "PASS" if result.get("current_pass") else "FAIL"
            cur_f = result.get("current_failures") or []
            cur_note = f" | Cur: {cur_f[0][:80]}" if cur_f else ""
            cur_usd = result.get("current_cost_usd", 0)
            logger.info(
                f"  {sid}: One-Live={a_score:.0f} {a_status} | "
                f"Current={b_score:.0f} {b_status} | Winner: {result['winner']}"
                f" | Cost OL ${ol_usd:.4f} Cur ${cur_usd:.4f}"
                f"{ol_note}{cur_note}"
            )

        if self.parallel_workers <= 1:
            self.results.append(result)
        else:
            assert self._scenario_slots is not None
            self._scenario_slots[idx] = result
        if self.parallel_workers <= 1:
            self.current_scenario_id = None

        result["completed_at"] = datetime.now().isoformat()

        # Self-heal: check for errors in result and apply fixes
        failures = result.get("one_live_failures") or []
        for failure_text in failures:
            fixed = self._detect_and_fix(failure_text)
            if fixed:
                break
        if result.get("phases") in ("TIMEOUT", "ERROR"):
            self._detect_and_fix(result.get("phases", ""))

        # Apply cooldown if set by self-heal
        if self._cooldown_secs > 0:
            await asyncio.sleep(self._cooldown_secs)
            self._cooldown_secs = max(0.0, self._cooldown_secs - 5.0)

        # Checkpoint: mark completed and save
        self._completed_ids.add(sid)
        await self._save_checkpoint()

        # Persist partial ab_results.json after every scenario
        await self._write_partial_results()

        await self._flush_live_status(running=True)

    async def _write_partial_results(self):
        """Write ab_results.json with results gathered so far (for crash recovery)."""
        if self.parallel_workers <= 1:
            results = self.results
        else:
            results = [r for r in (self._scenario_slots or []) if r is not None]
        if not results:
            return
        total = len(results)
        one_live_passes = sum(1 for r in results if r.get("one_live_pass"))
        out = {
            "partial": True,
            "summary": {
                "total": total,
                "one_live_passes": one_live_passes,
                "one_live_rate": f"{one_live_passes/total*100:.1f}%" if total else "--",
            },
            "results": results,
        }
        if self._checkpoint_lock:
            async with self._checkpoint_lock:
                _path = self.output_dir / "ab_results.json"
                _path.write_text(json.dumps(out, indent=2))
        else:
            (self.output_dir / "ab_results.json").write_text(json.dumps(out, indent=2))

    async def _confirm_failures(
        self,
        failed_ids: List[str],
        confirmation_runs: int = 2,
    ) -> List[str]:
        """
        Flaky-test filter: re-run each failed scenario up to `confirmation_runs` extra times.
        A scenario is only counted as a REAL failure if it fails in at least 2 out of
        (1 original + confirmation_runs) total runs.

        Returns the list of confirmed (non-flaky) failed scenario IDs.
        """
        if not failed_ids:
            return []
        logger.info(
            f"[FlakFilter] Confirming {len(failed_ids)} failures "
            f"({confirmation_runs} extra runs each, 2-of-{1+confirmation_runs} rule)..."
        )
        confirmed: List[str] = []
        total_runs = 1 + confirmation_runs  # original run + extra runs

        # Build a fresh runner stack for confirmation (avoid state contamination)
        self._init_runners()

        for sid in failed_ids:
            # Find scenario object
            all_scenarios = self._load_scenarios()
            scenario = next((s for s in all_scenarios if s.id == sid), None)
            if scenario is None:
                logger.warning(f"  [FlakFilter] {sid}: scenario not found — keeping as failure")
                confirmed.append(sid)
                continue

            fail_count = 1  # the original run already failed
            for attempt in range(confirmation_runs):
                try:
                    result = await self._run_one_scenario(scenario, self._adk_runner, self._adk_runner)
                    run_passed = result.get("one_live_pass", False)
                except Exception as e:
                    logger.warning(f"  [FlakFilter] {sid} attempt {attempt+1} error: {e}")
                    run_passed = False

                if not run_passed:
                    fail_count += 1

                # Early exit: already confirmed as real failure (>=2 fails)
                if fail_count >= 2:
                    break

            if fail_count >= 2:
                confirmed.append(sid)
                logger.info(f"  [FlakFilter] {sid}: CONFIRMED failure ({fail_count}/{total_runs} runs failed)")
            else:
                logger.info(f"  [FlakFilter] {sid}: FLAKY — passed {total_runs - fail_count}/{total_runs} retries, skipping")

        logger.info(
            f"[FlakFilter] {len(confirmed)}/{len(failed_ids)} failures confirmed as real "
            f"({len(failed_ids) - len(confirmed)} flaky filtered out)"
        )
        return confirmed

    async def run_retry_failed(self, confirmation_runs: int = 2) -> dict:
        """
        Re-run only the failed scenarios from the previous ab_results.json.

        Steps:
        1. Read {output_dir}/ab_results.json → extract failed scenario IDs
        2. Apply flaky filter (2-of-3 confirmation)
        3. Run only confirmed failures and write to ab_results_retry.json

        Returns a summary dict with confirmed_failures, flaky_count, retry_pass_rate.
        """
        import json as _json

        results_path = self.output_dir / "ab_results.json"
        if not results_path.exists():
            raise FileNotFoundError(
                f"No ab_results.json found at {results_path}. "
                "Run a full validation first before using --retry-failed."
            )

        data = _json.loads(results_path.read_text())
        all_results = data.get("results", [])
        failed_ids = [r["scenario_id"] for r in all_results if not r.get("one_live_pass", True)]
        logger.info(
            f"[RetryFailed] Found {len(failed_ids)} failed scenarios in {results_path}"
        )

        if not failed_ids:
            logger.info("[RetryFailed] No failures to retry — already at 100%")
            return {"confirmed_failures": 0, "flaky_count": 0, "retry_pass_rate": 1.0}

        # Apply flaky filter
        confirmed = await self._confirm_failures(failed_ids, confirmation_runs)
        flaky_count = len(failed_ids) - len(confirmed)

        if not confirmed:
            logger.info("[RetryFailed] All failures were flaky — effective pass rate is 100%")
            # Write an empty retry results file so the heal loop can detect this
            retry_summary = {
                "summary": {
                    "total": 0,
                    "confirmed_failures": 0,
                    "flaky_count": flaky_count,
                    "retry_pass_rate": 1.0,
                    "flaky_filtered": True,
                },
                "results": [],
            }
            retry_path = self.output_dir / "ab_results_retry.json"
            retry_path.write_text(_json.dumps(retry_summary, indent=2))
            return retry_summary["summary"]

        # Run only confirmed failures
        logger.info(f"[RetryFailed] Running {len(confirmed)} confirmed failures...")
        self._completed_ids.clear()  # Don't skip anything in retry mode
        await self.run(scenario_ids=confirmed)

        # Rename ab_results.json → ab_results_retry.json so heal loop can read it
        retry_path = self.output_dir / "ab_results_retry.json"
        import shutil as _shutil
        _shutil.copy2(str(self.output_dir / "ab_results.json"), str(retry_path))

        # Parse results for summary
        retry_data = _json.loads(retry_path.read_text())
        retry_results = retry_data.get("results", [])
        retry_passed = sum(1 for r in retry_results if r.get("one_live_pass", False))
        retry_pass_rate = retry_passed / len(retry_results) if retry_results else 0.0

        summary = {
            "confirmed_failures": len(confirmed),
            "flaky_count": flaky_count,
            "retry_pass_rate": retry_pass_rate,
            "retry_passed": retry_passed,
            "retry_total": len(retry_results),
        }
        logger.info(
            f"[RetryFailed] Done: {retry_passed}/{len(retry_results)} passed "
            f"({retry_pass_rate:.1%}), {flaky_count} flaky filtered"
        )
        return summary

    async def run(self, scenario_ids: Optional[List[str]] = None):
        """Run the Demo Training Loop validation."""
        self._start_time = time.time()

        # Load checkpoint for crash recovery
        self._load_checkpoint()

        scenarios = self._load_scenarios(scenario_ids)

        # Skip scenarios already completed in a previous run
        if self._completed_ids:
            skipped = [s for s in scenarios if s.id in self._completed_ids]
            scenarios = [s for s in scenarios if s.id not in self._completed_ids]
            logger.info(
                f"Checkpoint: skipping {len(skipped)} already-completed scenarios, "
                f"{len(scenarios)} remaining"
            )

        self.max_scenarios = len(scenarios)

        if self.parallel_workers > 1:
            pool_size = min(self.parallel_workers, max(1, len(scenarios)))
            logger.info(
                f"Parallel mode: {pool_size} worker stack(s) "
                f"(each with isolated Gemini/TTS/STT clients)"
            )
            self._status_lock = asyncio.Lock()
            self._checkpoint_lock = asyncio.Lock()
            self._scenario_slots = [None] * len(scenarios)
            self._runner_pool = asyncio.Queue()
            for _ in range(pool_size):
                await self._runner_pool.put(self._make_runner_stack())
            self.results = []
        else:
            self._status_lock = None
            self._checkpoint_lock = None
            self._scenario_slots = None
            self._runner_pool = None
            logger.info("Initializing runners...")
            self._init_runners()

        # Write dashboard HTML
        dashboard_path = self.output_dir / "index.html"
        with open(dashboard_path, "w") as f:
            f.write(_build_dashboard_html(str(self.output_dir)))

        # Write initial status
        await self._flush_live_status(running=True)

        logger.info(f"Dashboard: file://{dashboard_path}")
        logger.info(
            f"Starting {'ADK-only validation' if self.adk_only else 'comparison run'} "
            f"with {len(scenarios)} scenarios"
            f"{' (sequential)' if self.parallel_workers <= 1 else f' ({self.parallel_workers} parallel)'}..."
        )

        # Start heartbeat as a background task (cancelled when scenarios finish)
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        try:
            if self.parallel_workers <= 1:
                for idx, scenario in enumerate(scenarios):
                    await self._run_one_scenario(scenario, idx, len(scenarios))
            else:
                assert self._runner_pool is not None

                async def _run_with_pool(i: int, sc):
                    st = await self._runner_pool.get()
                    try:
                        await self._run_one_scenario(sc, i, len(scenarios), stack=st)
                    except Exception as e:
                        logger.exception(
                            "Unhandled error in scenario %s: %s", sc.id, e
                        )
                        self._scenario_slots[i] = {
                            "scenario_id": sc.id,
                            "expected_tools": list(
                                getattr(sc, "expected_tools", []) or []
                            ),
                            "one_live_pass": False,
                            "one_live_composite": 0,
                            "one_live_tools": [],
                            "one_live_turns": 0,
                            "one_live_failures": [f"RUNNER CRASH: {e!s}"[:200]],
                            "phases": "ERROR",
                        }
                        await self._flush_live_status(running=True)
                    finally:
                        await self._runner_pool.put(st)

                await asyncio.gather(
                    *(_run_with_pool(i, s) for i, s in enumerate(scenarios))
                )
                self.results = list(self._scenario_slots)
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        # Final status
        if self.parallel_workers > 1:
            self._write_live_status(running=False, results_snapshot=self.results)
        else:
            self._write_live_status(running=False)

        # Print summary
        total = len(self.results)
        one_live_passes = sum(1 for r in self.results if r.get("one_live_pass"))
        current_passes = sum(1 for r in self.results if r.get("current_pass"))
        a_wins = sum(1 for r in self.results if r.get("winner") == "One-Live")
        b_wins = sum(1 for r in self.results if r.get("winner") == "Current")
        ties = sum(1 for r in self.results if r.get("winner") == "Tie")

        one_live_composites = [r["one_live_composite"] for r in self.results if r.get("one_live_composite")]
        current_composites = [r["current_composite"] for r in self.results if r.get("current_composite")]
        ol_cost_sum = sum(float(r.get("one_live_cost_usd") or 0) for r in self.results)
        cur_cost_sum = sum(float(r.get("current_cost_usd") or 0) for r in self.results)

        print(f"\n{'='*70}")
        print(f"{'ADK VALIDATION RESULTS' if self.adk_only else 'A/B TEST RESULTS'} ({total} scenarios)")
        print(f"{'='*70}")
        if total:
            print(f"  ADK Runner: {one_live_passes}/{total} pass ({one_live_passes/total*100:.1f}%)")
        print(f"  Avg composite: {sum(one_live_composites)/len(one_live_composites):.1f}" if one_live_composites else "")
        if total:
            adk_call_lats = [float(r.get('one_live_latency_ms') or 0) for r in self.results if r.get('one_live_latency_ms') is not None]
            adk_turn_lats = [float(r.get('one_live_avg_turn_latency_ms') or 0) for r in self.results if r.get('one_live_avg_turn_latency_ms') is not None]
            if adk_call_lats:
                print(f"  Call latency avg: {sum(adk_call_lats)/len(adk_call_lats):.0f}ms")
            if adk_turn_lats:
                print(f"  Turn latency p50/p90: {_percentile(adk_turn_lats, 0.50):.0f}ms / {_percentile(adk_turn_lats, 0.90):.0f}ms")
        print(f"  Est. API cost (USD): ADK ${ol_cost_sum:.4f}")
        if not self.adk_only:
            print(f"  Current Loop: {current_passes}/{total} pass ({current_passes/total*100:.1f}%)" if total else "")
            print(f"  Est. API cost current (USD): ${cur_cost_sum:.4f} | Total ${ol_cost_sum + cur_cost_sum:.4f}")
            print(f"  One-Live wins: {a_wins} | Current wins: {b_wins} | Ties: {ties}")
        print(f"  Elapsed: {time.time() - self._start_time:.0f}s")
        print(f"{'='*70}")
        print(f"  Dashboard: file://{dashboard_path}")
        print(f"  Full results: {self.output_dir / 'ab_results.json'}")
        print(f"{'='*70}\n")

        # Save full results
        with open(self.output_dir / "ab_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total": total,
                    "one_live_passes": one_live_passes,
                    "one_live_rate": f"{one_live_passes/total*100:.1f}%" if total else "--",
                    "current_passes": current_passes,
                    "current_rate": f"{current_passes/total*100:.1f}%" if total else "--",
                    "one_live_wins": a_wins,
                    "current_wins": b_wins,
                    "ties": ties,
                    "one_live_cost_usd_total": round(ol_cost_sum, 4),
                    "current_cost_usd_total": round(cur_cost_sum, 4),
                    "cost_usd_grand_total": round(ol_cost_sum + cur_cost_sum, 4),
                },
                "results": self.results,
            }, f, indent=2)


def _start_dashboard_server(output_dir: str, port: int = 8787):
    """Start a local HTTP server for the dashboard."""
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=output_dir, **kwargs)
        def log_message(self, format, *args):
            pass  # Suppress request logs

    server = HTTPServer(("0.0.0.0", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


async def main():
    parser = argparse.ArgumentParser(
        description="Demo Training Loop — ADK Validation Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # Full 4-phase run (280 scenarios, 15 workers):
              python -m server.training.ab_test_loop \\
                  --phases 1 2 3 4 --adk-only --workers 15 --timeout 360

              # Single phase quick test:
              python -m server.training.ab_test_loop --phases 1 --adk-only --workers 5

              # Legacy targeted mode:
              python -m server.training.ab_test_loop --ids t2-res-01 t2-ord-03
        """),
    )
    parser.add_argument("--scenarios", type=int, default=50, help="Number of scenarios (legacy mode)")
    parser.add_argument("--output", default="/tmp/ab_test_results", help="Output directory")
    parser.add_argument("--timeout", type=float, default=360.0, help="Per-scenario timeout in seconds (default 360)")
    parser.add_argument("--dashboard-port", type=int, default=8787, help="Dashboard HTTP port")
    parser.add_argument("--ids", nargs="+", default=None, help="Specific scenario IDs to test (legacy mode)")
    parser.add_argument("--no-extras", action="store_true", default=False, help="Skip phase3/real-live extra scenarios (legacy mode)")
    parser.add_argument("--adk-only", action="store_true", help="Run ADK Runner only (skip Current Loop)")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        default=False,
        help=(
            "Re-run only failed scenarios from a previous ab_results.json in --output dir. "
            "Applies 2-of-3 flaky filter: re-runs each failure 2 extra times and only "
            "counts it as a confirmed failure if it fails at least 2 out of 3 total runs. "
            "Writes results to ab_results_retry.json."
        ),
    )
    parser.add_argument(
        "--flaky-runs",
        type=int,
        default=2,
        metavar="N",
        help="Extra confirmation runs per failed scenario when --retry-failed is set (default 2 → 2-of-3 rule)",
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        type=int,
        choices=[1, 2, 3, 4],
        default=None,
        metavar="N",
        help="Load scenarios from phase files (1=FAQ/40, 2=tools/100, 3=chaos/100, 4=edge/40). Example: --phases 1 2 3 4",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=15,
        metavar="N",
        help=(
            "Run up to N scenarios concurrently. Each worker uses its own "
            "Gemini/TTS/STT client stack (default 15)."
        ),
    )
    parser.add_argument(
        "--write-dashboard",
        action="store_true",
        help=(
            "Only write index.html + ab_live_status.json to --output and exit "
            "(no API calls). Use --serve-dashboard to keep a local HTTP server up."
        ),
    )
    parser.add_argument(
        "--serve-dashboard",
        action="store_true",
        help="With --write-dashboard, start http server and block (Ctrl+C to stop).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.write_dashboard:
        out = Path(args.output)
        html_path, json_path = write_dashboard_bundle(out)
        print("\nDashboard files written:")
        print(f"  {html_path}")
        print(f"  {json_path}")
        print("\nOpen in browser (recommended — fetch() needs HTTP):")
        print(f"  cd {out.resolve()}")
        print(f"  python3 -m http.server {args.dashboard_port}")
        print(f"  → http://127.0.0.1:{args.dashboard_port}/index.html")
        print(
            f"\nChecked-in template (regenerate into repo): "
            f"--output {PACKAGE_DASHBOARD_DIR}"
        )
        if args.serve_dashboard:
            _start_dashboard_server(str(out.resolve()), args.dashboard_port)
            logger.info(
                "Serving %s at http://localhost:%s/  (Ctrl+C to stop)",
                out,
                args.dashboard_port,
            )
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                pass
        return

    ab = ABTestLoop(
        output_dir=args.output,
        max_scenarios=args.scenarios,
        call_timeout=args.timeout,
        parallel_workers=args.workers,
        phases=args.phases or None,
    )
    ab._skip_extras = getattr(args, "no_extras", False)
    ab.adk_only = getattr(args, "adk_only", False)

    # Start dashboard server
    try:
        server, port = _start_dashboard_server(args.output, args.dashboard_port)
        logger.info(f"Dashboard live at: http://localhost:{port}/")
    except Exception as e:
        logger.warning(f"Could not start dashboard server: {e}")

    if getattr(args, "retry_failed", False):
        flaky_runs = getattr(args, "flaky_runs", 2)
        summary = await ab.run_retry_failed(confirmation_runs=flaky_runs)
        logger.info(f"[RetryFailed] Summary: {summary}")
    else:
        await ab.run(scenario_ids=args.ids)


if __name__ == "__main__":
    asyncio.run(main())
