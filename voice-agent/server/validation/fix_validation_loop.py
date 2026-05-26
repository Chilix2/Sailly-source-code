"""
Fix Validation Loop.

Validates each of the 12 failure buckets identified in the Demo Training Loop.

For each bucket (in priority order, Tier 1 first then Tier 2):
  Step 1 — run 10 targeted scenarios
    If pass → Step 2 (10 different scenarios)
    If fail → retry (up to 3 attempts), then STOP
  Step 2 — run 10 different scenarios
    If combined 1+2 pass → Step 3 (10 different scenarios)
    If fail → retry from Step 1
  Step 3 — run 10 different scenarios (final confirmation)
    If combined 1+2+3 pass → VALIDATED
    If fail → retry from Step 1
  After 3 failed attempts at any gate → UNRESOLVED

Tier 1 thresholds: 100% (compliance-critical tools)
Tier 2 thresholds: 60% (quality/reliability)

Reuses ABTestLoop's runner pool, checkpoint, heartbeat, and auditor pipeline.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _find_free_port(start: int = 8766, end: int = 8810) -> int:
    """Pick a free TCP port for the local fix-validation dashboard HTTP server."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free port in range {start}-{end - 1} for fix validation dashboard")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class FixBucket:
    name: str
    priority: int
    tier: int                       # 1 = 100% required, 2 = 60% required
    baseline_fail_count: int
    fix_description: str
    targeted_scenarios: list
    step_size: int = 10
    max_retries: int = 3
    pass_threshold: float = 1.0     # 1.0 for Tier 1, 0.6 for Tier 2
    # Runtime state
    status: str = "pending"         # pending / running / validated / unresolved
    attempts: int = 0
    step1_rate: float = 0.0
    step2_rate: float = 0.0
    step3_rate: float = 0.0
    combined_rate: float = 0.0
    step1_results: list = field(default_factory=list)
    step2_results: list = field(default_factory=list)
    step3_results: list = field(default_factory=list)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dashboard HTML
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_fix_dashboard_html(output_dir: str) -> str:
    return """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Fix Validation Loop</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--bg:#0b0e14;--surface:#13171f;--border:#222736;--text:#d4d8e2;--muted:#8b9ab0;
      --pass:#4ade80;--fail:#f87171;--warn:#fde68a;--blue:#93c5fd;--purple:#c4b5fd;--orange:#fb923c}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;
     font-size:14px;padding:20px}
h1{font-size:1.4rem;font-weight:600;margin-bottom:16px;color:#fff}
h2{font-size:1rem;font-weight:600;color:#fff;margin:20px 0 10px}
.status-bar{background:var(--surface);border:1px solid var(--border);border-radius:8px;
            padding:12px 16px;display:flex;align-items:center;gap:12px;margin-bottom:20px;
            flex-wrap:wrap;font-size:.82rem}
.status-text{color:#e2e8f0;font-weight:600}
.dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.dot.running{background:#facc15;animation:pulse 1.4s infinite}
.dot.done{background:var(--pass)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
.meta{color:#9aa8b8;font-size:12px}

/* KPI cards */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.kpi-val{font-size:1.6rem;font-weight:700;color:#fff;margin-bottom:4px;font-variant-numeric:tabular-nums}
.kpi-label{color:var(--muted);font-size:.68rem;text-transform:uppercase;letter-spacing:.07em}
.pass-c{color:var(--pass)}.fail-c{color:var(--fail)}.warn-c{color:var(--warn)}.blue-c{color:var(--blue)}

/* Progress table */
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border-bottom:1px solid #1a1e28;padding:8px 12px;text-align:left;vertical-align:top}
th{background:#10131a;color:var(--muted);font-weight:500;font-size:.68rem;
   text-transform:uppercase;letter-spacing:.05em;position:sticky;top:0;z-index:1}
td{color:#d4d8e2}
tr:hover td{background:#0f1320}
.t1-row{border-left:3px solid var(--pass)}
.t2-row{border-left:3px solid var(--warn)}
.validated{color:var(--pass);font-weight:700}
.unresolved{color:var(--fail);font-weight:700}
.running-s{color:var(--blue);font-weight:700}
.pending-s{color:var(--muted)}

/* Bar */
.bar-bg{background:#1e2433;height:14px;border-radius:7px;width:120px;display:inline-block;
        vertical-align:middle;overflow:hidden}
.bar-fill{height:100%;border-radius:7px;transition:width .3s}
.bar-pass{background:var(--pass)}.bar-warn{background:#fbbf24}.bar-fail{background:var(--fail)}

/* Scenario detail table */
.detail-table td{font-size:12px;padding:6px 10px;color:#cbd5e1}
.detail-table .meta{color:#9aa8b8}
.pass-tag{background:#14532d;color:var(--pass);border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700}
.fail-tag{background:#450a0a;color:var(--fail);border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700}
.tools-col{color:#cbd5e1;font-size:.74rem;line-height:1.4}
.fail-reason{color:#fca5a5;font-size:.74rem;line-height:1.35}
.score-val{font-variant-numeric:tabular-nums;font-weight:700}
.score-hi{color:var(--pass)}.score-mid{color:#fbbf24}.score-lo{color:var(--fail)}
</style>
</head>
<body>
<h1>Fix Validation Loop</h1>
<div class="status-bar">
  <div id="dot" class="dot running"></div>
  <span id="status-text" class="status-text">Initializing...</span>
  <span id="timing" class="meta" style="color:#9aa8b8"></span>
  <span id="progress" style="color:#e2e8f0;font-weight:600"></span>
</div>

<!-- KPIs -->
<div class="kpis">
  <div class="kpi">
    <div id="kpi-validated" class="kpi-val pass-c">—</div>
    <div class="kpi-label">Validated Buckets</div>
  </div>
  <div class="kpi">
    <div id="kpi-t1" class="kpi-val pass-c">—</div>
    <div class="kpi-label">Tier 1 Validated</div>
  </div>
  <div class="kpi">
    <div id="kpi-t2" class="kpi-val warn-c">—</div>
    <div class="kpi-label">Tier 2 Validated</div>
  </div>
  <div class="kpi">
    <div id="kpi-unresolved" class="kpi-val fail-c">—</div>
    <div class="kpi-label">Unresolved</div>
  </div>
</div>

<h2>Bucket Progress</h2>
<table id="bucket-table">
<thead>
<tr>
  <th>#</th><th>Bucket</th><th>Tier</th><th>Threshold</th>
  <th>Status</th><th>Attempts</th>
  <th>Step 1 (10)</th><th>Step 2 (10)</th><th>Step 3 (10)</th><th>Combined</th>
  <th>Baseline Fails</th><th>Fix Applied</th>
</tr>
</thead>
<tbody id="bucket-body"></tbody>
</table>

<h2>Scenario Detail</h2>
<div id="scenario-detail"><span class="meta">No scenarios run yet.</span></div>

<script>
function escHtml(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }
function pct(r){ return r!=null ? (r*100).toFixed(0)+'%' : '—' }
function barCls(r, thr){
  if(r==null) return 'bar-fail';
  return r>=thr ? 'bar-pass' : (r>=thr*0.6 ? 'bar-warn' : 'bar-fail');
}
function mkBar(r, thr){
  if(r==null) return '<span style="color:#556">—</span>';
  const w = Math.round(r*100);
  const cls = barCls(r, thr);
  const pctColor = r>=thr ? '#4ade80' : (r>=thr*0.6 ? '#fbbf24' : '#f87171');
  return '<div class="bar-bg"><div class="bar-fill '+cls+'" style="width:'+w+'%"></div></div> <span style="color:'+pctColor+';font-weight:600">'+pct(r)+'</span>';
}

async function refresh(){
  try{
    const [stateRes, detailRes] = await Promise.all([
      fetch('fix_validation_state.json?_='+Date.now()),
      fetch('fix_scenario_results.json?_='+Date.now()).catch(()=>null)
    ]);
    const d = await stateRes.json();
    
    // Status bar
    const running = d.status==='running';
    document.getElementById('dot').className = 'dot '+(running?'running':'done');
    document.getElementById('status-text').textContent = 
      'Fix Validation — ' + (d.status||'—').toUpperCase();
    if(d.started_at) document.getElementById('timing').textContent = 'Started: '+d.started_at;
    const cur = d.current_bucket ? ('Bucket: '+d.current_bucket+' Step '+d.current_step+'/3') : '';
    document.getElementById('progress').textContent = cur;

    // KPIs
    const bs = d.buckets||[];
    const validated = bs.filter(b=>b.status==='validated').length;
    const unresolved = bs.filter(b=>b.status==='unresolved').length;
    const t1v = bs.filter(b=>b.tier===1&&b.status==='validated').length;
    const t1t = bs.filter(b=>b.tier===1).length;
    const t2v = bs.filter(b=>b.tier===2&&b.status==='validated').length;
    const t2t = bs.filter(b=>b.tier===2).length;
    document.getElementById('kpi-validated').textContent = validated+'/'+bs.length;
    document.getElementById('kpi-t1').textContent = t1v+'/'+t1t;
    document.getElementById('kpi-t2').textContent = t2v+'/'+t2t;
    document.getElementById('kpi-unresolved').textContent = unresolved;

    // Bucket table
    const tbody = document.getElementById('bucket-body');
    tbody.innerHTML = '';
    for(const b of bs){
      const rowCls = b.tier===1 ? 't1-row':'t2-row';
      const stsCls = b.status==='validated'?'validated':b.status==='unresolved'?'unresolved':b.status==='running'?'running-s':'pending-s';
      const thr = b.pass_threshold||1.0;
      const tr = document.createElement('tr');
      tr.className = rowCls;
      tr.innerHTML =
        '<td>'+b.priority+'</td>'+
        '<td><b>'+escHtml(b.name)+'</b></td>'+
        '<td>Tier '+b.tier+'</td>'+
        '<td>'+(thr*100).toFixed(0)+'%</td>'+
        '<td class="'+stsCls+'">'+b.status.toUpperCase()+'</td>'+
        '<td>'+b.attempts+'/'+b.max_retries+'</td>'+
        '<td>'+mkBar(b.step1_rate>0?b.step1_rate:null, thr)+' ('+b.step1_count+')</td>'+
        '<td>'+mkBar(b.step2_rate>0?b.step2_rate:null, thr)+' ('+(b.step2_count||0)+')</td>'+
        '<td>'+mkBar(b.step3_rate>0?b.step3_rate:null, thr)+' ('+(b.step3_count||0)+')</td>'+
        '<td>'+mkBar(b.combined_rate>0?b.combined_rate:null, thr)+'</td>'+
        '<td>'+b.baseline_fail_count+'</td>'+
        '<td style="color:#9aa8b8;font-size:12px">'+escHtml(b.fix_description)+'</td>';
      tbody.appendChild(tr);
    }

    // Scenario detail
    if(detailRes){
      try{
        const scenarios = await detailRes.json();
        let html = '<table class="detail-table"><thead><tr>'+
          '<th>Scenario</th><th>Bucket</th><th>Result</th><th>Score</th>'+
          '<th>Tools Expected → Called</th><th>Failures</th></tr></thead><tbody>';
        for(const r of (scenarios||[])){
          const pass = r.pass;
          const sc = r.composite!=null ? Number(r.composite) : null;
          const scCls = sc!=null ? (sc>=72?'score-hi':sc>=50?'score-mid':'score-lo') : '';
          html += '<tr>'+
            '<td><strong>'+escHtml(r.scenario_id)+'</strong></td>'+
            '<td>'+escHtml(r.bucket||'—')+'</td>'+
            '<td>'+(pass?'<span class="pass-tag">PASS</span>':'<span class="fail-tag">FAIL</span>')+'</td>'+
            '<td>'+(sc!=null?'<span class="score-val '+scCls+'">'+sc.toFixed(1)+'</span>':'—')+'</td>'+
            '<td class="tools-col"><span style="color:#8b9ab0">exp:</span> '+escHtml((r.expected_tools||[]).join(', '))+
              '<br><span style="color:#8b9ab0">got:</span> '+escHtml((r.tools_called||[]).join(', '))+'</td>'+
            '<td class="fail-reason">'+escHtml((r.failures||[]).join('; '))+'</td>'+
            '</tr>';
        }
        html += '</tbody></table>';
        document.getElementById('scenario-detail').innerHTML = html;
      }catch(e){}
    }

  }catch(e){
    console.error('Refresh error:', e);
  }
}
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fix Validation Loop
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class FixValidationLoop:
    """
    Iterates over 12 failure buckets, running 10+10 targeted scenarios each.
    Reuses ABTestLoop's runner pool and auditor pipeline.
    """

    def __init__(
        self,
        output_dir: str = "/tmp/fix_validation",
        workers: int = 20,
        timeout: float = 360.0,
        failed_ids: Optional[List[str]] = None,
        single_bucket: Optional[str] = None,
        concurrent_buckets: int = 2,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.workers = workers
        self.call_timeout = timeout
        self.concurrent_buckets = concurrent_buckets
        # When set, only scenarios whose IDs appear in this set will be run.
        # Buckets that have no overlap are skipped entirely.
        self._failed_ids_filter: Optional[set] = set(failed_ids) if failed_ids else None
        # When set, only this single named bucket is run (for CFV single-bucket mode)
        self._single_bucket: Optional[str] = single_bucket
        self.buckets: List[FixBucket] = []
        self.scenario_results: List[Dict] = []
        self._runner_pool: Optional[asyncio.Queue] = None
        self._status: str = "pending"
        self._current_buckets: set = set()
        self._current_step: int = 0
        self._started_at: Optional[str] = None
        self._finished_at: Optional[str] = None
        self._heartbeat: int = 0
        self._results_lock: Optional[asyncio.Lock] = None
        self._state_lock: Optional[asyncio.Lock] = None
        
        # Initialize failure ingestor
        try:
            from server.failure_ingestor import FailureIngestor
            self.ingestor = FailureIngestor()
        except ImportError:
            logger.warning("FailureIngestor not available")
            self.ingestor = None
        
        self._init_buckets()

    def _init_buckets(self):
        from server.scenarios.fix_validation_buckets import (
            AI_GREETING_SCENARIOS,
            VERIFY_ADDRESS_SCENARIOS,
            CREATE_ORDER_SCENARIOS,
            SEND_SMS_SCENARIOS,
            CREATE_RESERVATION_SCENARIOS,
            GET_DATE_INFO_SCENARIOS,
            CHECK_AVAILABILITY_SCENARIOS,
            GET_WEATHER_SCENARIOS,
            TASK_SCORE_SCENARIOS,
            INSTRUCTION_SCORE_SCENARIOS,
            TIMEOUT_SCENARIOS,
            CONVERSATION_LOOP_SCENARIOS,
        )

        tier1_defs = [
            ("ai_greeting",          1, 6,  "Force ai_greeting on turn 0",               AI_GREETING_SCENARIOS,          1.0),
            ("verify_address",       2, 41, "Sticky flag + no node restriction",          VERIFY_ADDRESS_SCENARIOS,        1.0),
            ("create_order",         3, 4,  "Remove confirmation gate + partial dish",    CREATE_ORDER_SCENARIOS,          1.0),
            ("send_sms",             4, 0,  "Auto-pair send_sms with create_order",       SEND_SMS_SCENARIOS,              1.0),
            ("create_reservation",   5, 31, "Remove confirmation gate + check_avail",     CREATE_RESERVATION_SCENARIOS,    1.0),
            ("get_date_info",        6, 13, "Remove turn==0 + add ordering node",         GET_DATE_INFO_SCENARIOS,         1.0),
            ("check_availability",   7, 5,  "Widen trigger to ordering + faq nodes",      CHECK_AVAILABILITY_SCENARIOS,    1.0),
            ("get_weather",          8, 0,  "Add forced commit + state flag",             GET_WEATHER_SCENARIOS,           1.0),
        ]
        tier2_defs = [
            ("task_score",           9,  38, "Expand _ORDER_KW + _RESERVATION_KW",        TASK_SCORE_SCENARIOS,            0.60),
            ("instruction_score",    10, 6,  "Escalation prompt German-only enforcement", INSTRUCTION_SCORE_SCENARIOS,     0.60),
            ("timeout",              11, 8,  "5-turn loop escape + stuck-loop detector",  TIMEOUT_SCENARIOS,               0.60),
            ("conversation_loop",    12, 3,  "4-identical-response detector → end_call",  CONVERSATION_LOOP_SCENARIOS,     0.60),
        ]

        STEPS = 3
        STEP_SIZE = 10  # scenarios per step
        FULL_POOL_SIZE = STEPS * STEP_SIZE  # 30 total needed for all 3 steps

        for name, pri, fails, desc, scens, thr in tier1_defs + tier2_defs:
            if self._failed_ids_filter:
                # Scenarios that specifically failed — must appear in Step 1
                failed_scens = [s for s in scens if s.id in self._failed_ids_filter]
                if not failed_scens:
                    # None of this bucket's scenarios are in the failed list — skip bucket
                    continue

                # Supplement with non-failed scenarios from the full pool so that
                # Steps 2 and 3 can run with fresh scenarios (validates the fix
                # didn't break anything else, not just that it fixed the known failures).
                failed_ids_set = {s.id for s in failed_scens}
                supplement = [s for s in scens if s.id not in failed_ids_set]

                # Step 1: known-failing scenarios (up to step_size)
                # Steps 2+3: supplement from the rest of the pool
                # If the pool has fewer than 30 total, repeat / cycle as needed
                combined = failed_scens[:]
                needed = FULL_POOL_SIZE - len(combined)
                if supplement:
                    # Fill from supplement pool; cycle if necessary
                    for s in itertools.islice(itertools.cycle(supplement), needed):
                        combined.append(s)
                elif len(combined) < FULL_POOL_SIZE:
                    # Only failing scenarios available — cycle them for steps 2+3
                    for s in itertools.islice(itertools.cycle(failed_scens), needed):
                        combined.append(s)

                final_scens = combined
                logger.debug(
                    f"[FixVal] Bucket '{name}': {len(failed_scens)} failing + "
                    f"{len(final_scens) - len(failed_scens)} supplemented = {len(final_scens)} total"
                )
            else:
                # Standalone run (no filter) — use full scenario pool
                final_scens = scens

            self.buckets.append(FixBucket(
                name=name,
                priority=pri,
                tier=1 if thr == 1.0 else 2,
                baseline_fail_count=fails,
                fix_description=desc,
                targeted_scenarios=final_scens,
                pass_threshold=thr,
            ))

        if self._failed_ids_filter and self.buckets:
            logger.info(
                f"[FixVal] Filtered to {len(self.buckets)} relevant buckets "
                f"for {len(self._failed_ids_filter)} failed IDs (scenarios supplemented to 30/bucket)"
            )

        # Single-bucket mode (CFV): keep only the named bucket
        if self._single_bucket:
            self.buckets = [b for b in self.buckets if b.name == self._single_bucket]
            if self.buckets:
                logger.info(f"[FixVal] Single-bucket mode: running only '{self._single_bucket}'")
            else:
                logger.warning(f"[FixVal] Single-bucket mode: bucket '{self._single_bucket}' not found — nothing to run")

    # ---------------------------------------------------------------------- #
    # Runner pool (reuses ABTestLoop's _make_runner_stack)
    # ---------------------------------------------------------------------- #

    def _make_runner_stack(self):
        from server.training.tier2_runner import Tier2AudioRunner
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

        adk = ADKRunner(
            audio_injector=runner.audio_injector,
            gemini_runner=runner,
            openai_api_key=openai_key,
        )
        return runner, adk

    # ---------------------------------------------------------------------- #
    # Core scenario runner
    # ---------------------------------------------------------------------- #

    async def _run_scenario(self, scenario, runner, adk, bucket_name: str) -> Dict:
        """Run one scenario through ADKRunner + auditor. Returns result dict."""
        from server.training.call_auditor_de import audit_call
        from server.training.cost_tracker import CostTracker
        from server.training.ab_test_loop import _conv_result_to_audit_turns

        sid = scenario.id
        expected = list(getattr(scenario, "expected_tools", []) or [])
        ct = CostTracker()
        runner.set_cost_tracker(ct)
        adk.cost_tracker = ct

        result = {
            "scenario_id": sid,
            "bucket": bucket_name,
            "expected_tools": expected,
            "pass": False,
            "composite": 0,
            "tools_called": [],
            "failures": [],
            "turns": 0,
            "latency_ms": None,
            "cost_usd": 0.0,
        }
        try:
            conv = await asyncio.wait_for(
                adk.run(scenario, phase=2, run_number=1),
                timeout=self.call_timeout,
            )
            audit_turns = _conv_result_to_audit_turns(conv)
            audit = audit_call(
                scenario_id=sid,
                phase=2,
                run_number=1,
                turns=audit_turns,
                expected_tools=expected,
                total_latency_ms=conv.total_latency_ms,
            )
            result["pass"] = audit.passed
            result["composite"] = round(audit.composite, 1)
            result["tools_called"] = conv.tools_called
            result["failures"] = list(audit.failure_reasons[:5]) if not audit.passed else []
            result["turns"] = len(conv.turns)
            result["latency_ms"] = round(conv.total_latency_ms, 1)
        except asyncio.TimeoutError:
            result["failures"] = [f"TIMEOUT (>{self.call_timeout:.0f}s)"]
            logger.warning(f"  {sid}: TIMEOUT")
        except Exception as e:
            result["failures"] = [f"ERROR: {str(e)[:120]}"]
            logger.error(f"  {sid}: ERROR — {e}")
        finally:
            result["cost_usd"] = round(ct.estimate_usd(), 4)
            runner.set_cost_tracker(None)
            adk.cost_tracker = None

        # Ingest failure into known issues database
        if not result["pass"] and self.ingestor:
            self.ingestor.ingest_failure({
                "scenario_id": result["scenario_id"],
                "call_sid": getattr(conv, "call_sid", "") if "conv" in locals() else "",
                "composite_score": result["composite"],
                "tools_expected": result["expected_tools"],
                "tools_called": result["tools_called"],
                "failure_reasons": result["failures"],
                "passed": result["pass"],
                "source": "validation",
            })

        return result

    async def _run_batch(self, scenarios: list, bucket_name: str) -> List[Dict]:
        """Run a batch of scenarios using the runner pool."""
        results = []
        tasks = []

        async def run_one_from_pool(scenario):
            runner, adk = await self._runner_pool.get()
            try:
                r = await self._run_scenario(scenario, runner, adk, bucket_name)
                return r
            finally:
                await self._runner_pool.put((runner, adk))

        tasks = [run_one_from_pool(s) for s in scenarios]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Append to global scenario results for dashboard
        async with self._results_lock:
            self.scenario_results.extend(results)
            self._save_scenario_results()

        return list(results)

    @staticmethod
    def _pass_rate(results: List[Dict]) -> float:
        if not results:
            return 0.0
        return sum(1 for r in results if r.get("pass")) / len(results)

    # ---------------------------------------------------------------------- #
    # State persistence
    # ---------------------------------------------------------------------- #

    def _save_state(self):
        state = {
            "status": self._status,
            "current_bucket": list(self._current_buckets),
            "current_step": self._current_step,
            "started_at": self._started_at,
            "finished_at": self._finished_at,
            "heartbeat": self._heartbeat,
            "buckets": [],
        }
        for b in self.buckets:
            state["buckets"].append({
                "name": b.name,
                "priority": b.priority,
                "tier": b.tier,
                "baseline_fail_count": b.baseline_fail_count,
                "fix_description": b.fix_description,
                "status": b.status,
                "pass_threshold": b.pass_threshold,
                "max_retries": b.max_retries,
                "attempts": b.attempts,
                "step1_rate": round(b.step1_rate, 4),
                "step2_rate": round(b.step2_rate, 4),
                "step3_rate": round(b.step3_rate, 4),
                "combined_rate": round(b.combined_rate, 4),
                "step1_count": len(b.step1_results),
                "step2_count": len(b.step2_results),
                "step3_count": len(b.step3_results),
            })
        (self.output_dir / "fix_validation_state.json").write_text(
            json.dumps(state, indent=2)
        )

    async def _save_state_async(self):
        """Thread-safe async version of _save_state (acquires _state_lock)."""
        async with self._state_lock:
            self._save_state()

    def _save_scenario_results(self):
        (self.output_dir / "fix_scenario_results.json").write_text(
            json.dumps(self.scenario_results, indent=2)
        )

    # ---------------------------------------------------------------------- #
    # Dashboard
    # ---------------------------------------------------------------------- #

    def _start_dashboard_server(self):
        # Kill any previously tracked http.server from an earlier iteration
        prev_pid_file = self.output_dir.parent / "_dashboard_server_pid"
        if prev_pid_file.exists():
            try:
                old_pid = int(prev_pid_file.read_text().strip())
                import signal as _sig
                try:
                    os.kill(old_pid, _sig.SIGTERM)
                    logger.info(f"[Dashboard] Killed prior http.server PID {old_pid}")
                except ProcessLookupError:
                    pass
            except Exception:
                pass

        html = _build_fix_dashboard_html(str(self.output_dir))
        (self.output_dir / "index.html").write_text(html)
        port = _find_free_port()
        # Use same Python as this process; avoid hardcoding "python3" on PATH.
        proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port), "-d", str(self.output_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Persist PID so the next iteration can clean it up
        prev_pid_file.write_text(str(proc.pid))
        (self.output_dir / "dashboard_port.txt").write_text(str(port))
        logger.info(
            f"Fix Validation Dashboard (this run): http://127.0.0.1:{port}/index.html "
            f"(port in {self.output_dir / 'dashboard_port.txt'})"
        )
        logger.info(
            "Public URL (all heal-loop iterations): https://sailly.tech/fix-validation/ "
            "→ open latest iter_*/index.html"
        )

    # ---------------------------------------------------------------------- #
    # Heartbeat
    # ---------------------------------------------------------------------- #

    async def _heartbeat_loop(self):
        while True:
            await asyncio.sleep(10)
            self._heartbeat += 1
            self._save_state()

    # ---------------------------------------------------------------------- #
    # Main validation loop
    # ---------------------------------------------------------------------- #

    async def run(self):
        self._started_at = datetime.now().isoformat()
        self._status = "running"

        # Build shared runner pool (no artificial cap — async LLM calls are non-blocking)
        pool_size = self.workers
        logger.info(f"Building runner pool ({pool_size} workers, {self.concurrent_buckets} concurrent buckets)...")
        self._runner_pool = asyncio.Queue()
        self._results_lock = asyncio.Lock()
        self._state_lock = asyncio.Lock()
        for _ in range(pool_size):
            stack = self._make_runner_stack()
            await self._runner_pool.put(stack)

        self._save_state()
        self._start_dashboard_server()

        # Start heartbeat
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info(
            f"Starting Fix Validation Loop — {len(self.buckets)} buckets × 30 scenarios "
            f"(3 steps × 10) with {self.concurrent_buckets} parallel bucket slots"
        )

        # Task-queue scheduler: concurrent_buckets slot workers drain the bucket queue
        bucket_queue: asyncio.Queue = asyncio.Queue()
        for b in self.buckets:
            await bucket_queue.put(b)

        async def slot_worker():
            while True:
                try:
                    bucket = bucket_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                await self._validate_bucket(bucket)

        try:
            await asyncio.gather(*[slot_worker() for _ in range(self.concurrent_buckets)])
        finally:
            heartbeat_task.cancel()

        self._status = "finished"
        self._finished_at = datetime.now().isoformat()
        self._save_state()
        self._print_summary()

    async def _validate_bucket(self, bucket: FixBucket):
        """
        Gated 3-step validation:
          Step 1: 10 scenarios → must pass threshold to proceed
          Step 2: 10 different scenarios → combined 1+2 must pass to proceed
          Step 3: 10 different scenarios → combined 1+2+3 must pass → VALIDATED

        If Step 1 fails after 3 attempts → stop (UNRESOLVED), don't waste time on Step 2.
        If Step 1 passes but Step 2 combined fails → retry from Step 1.
        """
        bucket.status = "running"
        self._current_buckets.add(bucket.name)
        self._save_state()

        validated = False

        for attempt in range(1, bucket.max_retries + 1):
            bucket.attempts = attempt
            logger.info(
                f"\n{'='*60}\n"
                f"Bucket {bucket.priority}/12: {bucket.name} "
                f"(Tier {bucket.tier}, threshold={bucket.pass_threshold:.0%})\n"
                f"Attempt {attempt}/{bucket.max_retries} — {bucket.fix_description}\n"
                f"{'='*60}"
            )

            # ── Step 1: first 10 scenarios ────────────────────────────
            self._current_step = 1
            step1_scens = bucket.targeted_scenarios[:bucket.step_size]
            logger.info(f"  Step 1: running {len(step1_scens)} scenarios...")
            step1_results = await self._run_batch(step1_scens, bucket.name)
            bucket.step1_results = step1_results
            bucket.step1_rate = self._pass_rate(step1_results)
            passes1 = sum(1 for r in step1_results if r.get("pass"))
            bucket.combined_rate = bucket.step1_rate
            logger.info(
                f"  Step 1 result: {bucket.step1_rate:.0%} "
                f"({passes1}/{len(step1_results)})"
            )
            self._save_state()

            if bucket.step1_rate < bucket.pass_threshold:
                logger.warning(
                    f"  Step 1 {bucket.step1_rate:.0%} < "
                    f"{bucket.pass_threshold:.0%} — skipping Steps 2+3"
                )
                if attempt < bucket.max_retries:
                    logger.info(f"  Retrying in 5s... (attempt {attempt+1}/{bucket.max_retries})")
                    await asyncio.sleep(5)
                continue

            # ── Step 2: next 10 different scenarios (gated by Step 1) ──
            self._current_step = 2
            step2_scens = bucket.targeted_scenarios[
                bucket.step_size : bucket.step_size * 2
            ]
            if not step2_scens:
                bucket.status = "validated"
                validated = True
                logger.info(
                    f"  ✅ VALIDATED (Step 1 passed, no Step 2 scenarios) — {bucket.name} "
                    f"({bucket.step1_rate:.0%} >= {bucket.pass_threshold:.0%})"
                )
                break

            logger.info(f"  Step 2: running {len(step2_scens)} different scenarios...")
            step2_results = await self._run_batch(step2_scens, bucket.name)
            bucket.step2_results = step2_results
            bucket.step2_rate = self._pass_rate(step2_results)
            passes2 = sum(1 for r in step2_results if r.get("pass"))
            combined_12 = step1_results + step2_results
            bucket.combined_rate = self._pass_rate(combined_12)
            logger.info(
                f"  Step 2 result: {bucket.step2_rate:.0%} "
                f"({passes2}/{len(step2_results)}) | "
                f"Combined 1+2: {bucket.combined_rate:.0%}"
            )
            self._save_state()

            if bucket.combined_rate < bucket.pass_threshold:
                logger.warning(
                    f"  Combined 1+2 {bucket.combined_rate:.0%} < "
                    f"{bucket.pass_threshold:.0%} — skipping Step 3"
                )
                if attempt < bucket.max_retries:
                    logger.info(f"  Retrying in 5s... (attempt {attempt+1}/{bucket.max_retries})")
                    await asyncio.sleep(5)
                continue

            # ── Step 3: next 10 different scenarios (gated by Step 1+2) ──
            self._current_step = 3
            step3_scens = bucket.targeted_scenarios[
                bucket.step_size * 2 : bucket.step_size * 3
            ]
            if not step3_scens:
                bucket.status = "validated"
                validated = True
                logger.info(
                    f"  ✅ VALIDATED (Steps 1+2 passed, no Step 3 scenarios) — {bucket.name} "
                    f"({bucket.combined_rate:.0%} >= {bucket.pass_threshold:.0%})"
                )
                break

            logger.info(f"  Step 3: running {len(step3_scens)} different scenarios...")
            step3_results = await self._run_batch(step3_scens, bucket.name)
            bucket.step3_results = step3_results
            bucket.step3_rate = self._pass_rate(step3_results)
            passes3 = sum(1 for r in step3_results if r.get("pass"))
            all_results = combined_12 + step3_results
            bucket.combined_rate = self._pass_rate(all_results)
            logger.info(
                f"  Step 3 result: {bucket.step3_rate:.0%} "
                f"({passes3}/{len(step3_results)}) | "
                f"Combined 1+2+3: {bucket.combined_rate:.0%}"
            )
            self._save_state()

            if bucket.combined_rate >= bucket.pass_threshold:
                bucket.status = "validated"
                validated = True
                logger.info(
                    f"  ✅ VALIDATED — {bucket.name} "
                    f"({bucket.combined_rate:.0%} >= {bucket.pass_threshold:.0%})"
                )
                break
            else:
                logger.warning(
                    f"  All 3 steps combined: {bucket.combined_rate:.0%} < "
                    f"{bucket.pass_threshold:.0%} — not yet validated"
                )
                if attempt < bucket.max_retries:
                    logger.info(f"  Retrying in 5s... (attempt {attempt+1}/{bucket.max_retries})")
                    await asyncio.sleep(5)

        if not validated:
            bucket.status = "unresolved"
            logger.warning(
                f"  UNRESOLVED — {bucket.name} "
                f"after {bucket.max_retries} attempts "
                f"(combined={bucket.combined_rate:.0%})"
            )

        self._current_buckets.discard(bucket.name)
        self._save_state()

    # ---------------------------------------------------------------------- #
    # Summary
    # ---------------------------------------------------------------------- #

    def _print_summary(self):
        print("\n" + "=" * 70)
        print("FIX VALIDATION RESULTS")
        print("=" * 70)
        validated = [b for b in self.buckets if b.status == "validated"]
        unresolved = [b for b in self.buckets if b.status == "unresolved"]
        t1 = [b for b in self.buckets if b.tier == 1]
        t2 = [b for b in self.buckets if b.tier == 2]
        t1v = [b for b in t1 if b.status == "validated"]
        t2v = [b for b in t2 if b.status == "validated"]

        for b in self.buckets:
            icon = "✓" if b.status == "validated" else "✗"
            print(
                f"  {icon} [T{b.tier}] {b.name:25s} "
                f"{b.status:12s} "
                f"combined={b.combined_rate:.0%}  "
                f"baseline: {b.baseline_fail_count} fails"
            )

        print(f"\nTotal:  {len(validated)}/{len(self.buckets)} validated")
        print(f"Tier 1: {len(t1v)}/{len(t1)} validated (required: 100%)")
        print(f"Tier 2: {len(t2v)}/{len(t2)} validated (required: 60%)")
        if unresolved:
            print(f"\nUnresolved buckets requiring manual investigation:")
            for b in unresolved:
                print(f"  - {b.name}: combined={b.combined_rate:.0%}, attempts={b.attempts}")
        print("=" * 70)
        print(f"\nResults: {self.output_dir}/fix_validation_state.json")
        print(f"Dashboard: http://localhost:8766")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI entry point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    # Reduce noise from google auth / grpc
    for noisy in ("google", "grpc", "urllib3", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _main():
    import argparse

    _setup_logging()

    parser = argparse.ArgumentParser(
        description="Fix Validation Loop — validates 12 failure buckets after a Claude fix"
    )
    parser.add_argument(
        "--output", default="/tmp/fix_validation",
        help="Output directory for results + dashboard (default: /tmp/fix_validation)",
    )
    parser.add_argument(
        "--workers", type=int, default=20,
        help="Parallel runner workers (default: 20)",
    )
    parser.add_argument(
        "--concurrent-buckets", type=int, default=2,
        dest="concurrent_buckets",
        help="Number of buckets to validate in parallel (default: 2)",
    )
    parser.add_argument(
        "--timeout", type=float, default=360.0,
        help="Per-scenario timeout in seconds (default: 360)",
    )
    parser.add_argument(
        "--failed-ids-file",
        default=None,
        metavar="PATH",
        help=(
            "JSON file containing a list of failed scenario IDs from a previous run "
            "(written by validation_heal_loop). Only scenarios matching these IDs will be "
            "run within each bucket. Buckets with no matching scenarios are skipped."
        ),
    )
    parser.add_argument(
        "--bucket",
        default=None,
        metavar="BUCKET_NAME",
        help=(
            "Run only this single named bucket (e.g. 'verify_address'). "
            "Used by Crucial Fix Validation to test one bucket at a time. "
            "When set, all other buckets are skipped regardless of failed-ids-file."
        ),
    )
    args = parser.parse_args()

    failed_ids = None
    if args.failed_ids_file:
        try:
            failed_ids = json.loads(Path(args.failed_ids_file).read_text())
            logger.info(f"[FixVal] Loaded {len(failed_ids)} failed IDs from {args.failed_ids_file}")
        except Exception as e:
            logger.warning(f"[FixVal] Could not load --failed-ids-file: {e} — running all buckets")

    loop = FixValidationLoop(
        output_dir=args.output,
        workers=args.workers,
        timeout=args.timeout,
        failed_ids=failed_ids,
        single_bucket=args.bucket,
        concurrent_buckets=args.concurrent_buckets,
    )
    asyncio.run(loop.run())


if __name__ == "__main__":
    _main()
