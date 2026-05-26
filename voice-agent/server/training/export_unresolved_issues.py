#!/usr/bin/env python3
"""
Simple script to generate unresolved issues markdown from transcripts.
No external imports needed beyond json, pathlib.
"""

import json
from pathlib import Path
from collections import defaultdict
import sys

def main():
    run_dir = Path("/tmp/atl_20260402_202238")
    transcripts_dir = run_dir / "raw_transcripts"
    output_path = Path("/home/charles2/sailly-google-fork/unresolved issues.md")
    
    print(f"Loading transcripts from {transcripts_dir}...")
    
    # Load all transcripts
    failures = {}
    timeouts = {}
    count = 0
    
    for json_file in sorted(transcripts_dir.glob("*.json")):
        count += 1
        try:
            with open(json_file) as f:
                rec = json.load(f)
                sid = rec.get("scenario_id", "unknown")
                run_num = rec.get("run_number", 0)
                
                if not rec.get("passed", False):
                    if rec.get("timed_out", False):
                        timeouts[f"{sid}_run{run_num}"] = rec
                    else:
                        failures[f"{sid}_run{run_num}"] = rec
        except Exception as e:
            print(f"Error loading {json_file}: {e}", file=sys.stderr)
    
    print(f"Loaded {count} transcripts: {len(failures)} failures, {len(timeouts)} timeouts")
    
    # Load checkpoint for metadata
    cp_data = {}
    cp_path = run_dir / "checkpoint.json"
    if cp_path.exists():
        with open(cp_path) as f:
            cp_data = json.load(f)
    
    # Generate markdown
    with open(output_path, "w") as md:
        md.write("# Unresolved Issues Report\n\n")
        
        # Metadata
        md.write("## Metadata\n\n")
        md.write(f"- **Run directory:** `{run_dir}`\n")
        md.write(f"- **Total completed scenario runs:** {len(cp_data.get('completed_ids', []))}\n")
        md.write(f"- **Total auditor failures:** {len(failures)}\n")
        md.write(f"- **Total timeouts:** {len(timeouts)}\n")
        md.write(f"- **Total cost (USD):** ${cp_data.get('cost_usd', 0):.2f}\n")
        md.write(f"- **Raw transcripts scanned:** {count}\n\n")
        
        # Pipeline overview
        md.write("## Pipeline Overview\n\n")
        md.write("""The training loop executes a full audio round-trip per turn:

1. **Caller simulation** (GPT-4o-mini) → **TTS** (Google Wavenet-F) → caller audio
2. **STT** (Deepgram Nova-3-de) → transcript + WER
3. **LLM** (Gemini 2.5 Flash) → bot response + `[TOOL:name]` tags
4. **TTS** (Chirp3 HD) → bot audio  
5. **Auditor** (`call_auditor_de.py`): 10-dimension score (task, language, instruction, latency, audio, STT, flow, response, hallucination, completeness)

**Pass criteria:** Composite score ≥ 72 AND no dimension < 30 AND no explicit failures.

**Pre-auditor pass:** Only checks `all(expected_tools in tools_called)` — **not** composite.

**Key files:**
- [`server/training/conversation_loop.py`](file:///home/charles2/sailly-google-fork/server/training/conversation_loop.py): Orchestrates turns, extracts tools via `_parse_tool_calls`.
- [`server/training/call_auditor_de.py`](file:///home/charles2/sailly-google-fork/server/training/call_auditor_de.py): Audit logic and scoring.
- [`server/training/tier2_runner.py`](file:///home/charles2/sailly-google-fork/server/training/tier2_runner.py): System prompt and tool whitelist.
- [`server/scenarios/tier2_scenarios.py`](file:///home/charles2/sailly-google-fork/server/scenarios/tier2_scenarios.py): Scenario definitions.

---

## Known Structural Contradictions

### 1. Prompt vs Menu Knowledge
**File:** [`tier2_runner.py`](file:///home/charles2/sailly-google-fork/server/training/tier2_runner.py) lines ~104–158

The system prompt **requires** `[TOOL:get_menu]` before answering menu questions (Regel 5: "ZUERST [TOOL:get_menu]"), but also **embeds concrete menu prices and dishes** in the same prompt:
- Bibimbap 12.50€, Bulgogi 14.90€, etc.
- Vegetarian options listed.

**Consequence:** The model can satisfy menu questions **without** calling `get_menu`, while scenarios still expect it. This creates a systematic **training contradiction** where the prompt signal and expected_tools diverge.

**Impact:** Scenarios expecting `["get_menu", "create_order"]` may fail even if the bot correctly answers menu questions — not a quality issue, but an **evaluation validity** problem.

### 2. `get_menu` "Exactly Once" Rule vs Set-Based Tool Checking
**File:** [`tier2_runner.py`](file:///home/charles2/sailly-google-fork/server/training/tier2_runner.py) Regel 5

The prompt forbids a **second** `[TOOL:get_menu]` call. However, the auditor compares `expected_tools` as sets:

```python
# call_auditor_de.py ~328–331
expected_set = set(expected_tools)
called_set = set(all_tools)
missing = list(expected_set - called_set)
```

**Consequence:** Calling `get_menu` twice does **not** create a "missing tool" failure. Instead, it **only** triggers instruction/flow/repetition penalties if detected elsewhere. Claims like "the bot called `get_menu` twice so it failed" likely reflect **misinterpretation of auditor penalties**, not the tool-counting logic.

### 3. Scenario Expectations vs Prompt Priorities
**Example:** [`t2-ord-05`](file:///home/charles2/sailly-google-fork/server/scenarios/tier2_scenarios.py) line 530–533

Scenario: "Allergen question before order"
- Turns: `["Gibt es glutenfreie Optionen", "OK dann gib mir ein Bibimbap zum Mitnehmen"]`
- **Expected tools:** `["create_order"]` only (no `get_menu`)

But the global prompt says: **when a menu question is asked, always call `[TOOL:get_menu]` first**. A caller asking about allergen options triggers that rule.

**Consequence:** A correct bot calling `get_menu` on an allergen question will fail the auditor despite correctly handling the scenario.

### 4. Bulk-Generated Edge Scenarios with Conflicting Expected Tools
**File:** [`tier2_scenarios.py`](file:///home/charles2/sailly-google-fork/server/scenarios/tier2_scenarios.py) lines 1036–1049

`TIER2_TOOL_EDGE_CASES_EXTRA` (20 generated scenarios) use:
- Synthetic opener: `"Tool sequence {'A' if i%2 else 'B'} variant {i}"`
- Generic continuation: `"Bestellen"`
- **Expected tools alternate:**
  - `i % 2 == 0`: `["get_menu", "create_order", "send_sms"]`
  - `i % 2 == 1`: `["create_reservation"]` (odd iterations, e.g., i=3,5,7... → t2-edge-44,46,50)

**Problem:** A vague opener like "Tool sequence B variant 3" + "Bestellen" (order intent) is **ambiguous**. The bot may interpret it as an order flow (requiring `get_menu` + `create_order`) even though the scenario expects **only reservation tools**. This is an **eval design failure**, not a model quality issue.

**Affected IDs:** t2-edge-44, t2-edge-46, t2-edge-50, etc. (odd values of `i`)

### 5. Auditor Tool Parsing and `faq` Inconsistency
**File:** [`call_auditor_de.py`](file:///home/charles2/sailly-google-fork/server/training/call_auditor_de.py) lines 54–60, 152–161

`ALL_TOOLS` set does **not include `faq`**:

```python
ALL_TOOLS = {
    "ai_greeting", "end_call", "transfer_to_tier2", ...,
    "get_date_info", "get_weather",
}
```

But [`tier2_runner.py`](file:///home/charles2/sailly-google-fork/server/training/tier2_runner.py) line 515 **includes `"faq"`** in the tool whitelist.

**Consequence:** The auditor's `_parse_tools_full` (line 160: `if tool in text`) will still find `[TOOL:faq]` in brackets, but it won't match the `ALL_TOOLS` check for bare-word detection. This creates **asymmetric tool parsing**: explicit `[TOOL:faq]` tags are recognized, but substring logic may differ from intended.

### 6. Early `end_call` vs Min Turns Enforcement
**File:** [`conversation_loop.py`](file:///home/charles2/sailly-google-fork/server/training/conversation_loop.py) lines 306–325

The loop can **block** an early `end_call` tool if `min_turns` hasn't been reached. This interacts with proactive/fraud rules and may cause the bot to loop unexpectedly.

---

## Failure Breakdown by Root Cause

""")
        
        # Cluster failures
        clusters = defaultdict(list)
        
        for key, rec in sorted(failures.items()):
            failure_reasons = rec.get("failure_reasons", [])
            bucket = "other"
            
            if failure_reasons:
                reasons_text = " ".join(str(r).lower() for r in failure_reasons)
                
                if "missing" in reasons_text:
                    bucket = "missing_tools"
                elif "wer" in reasons_text:
                    bucket = "stt_quality"
                elif "english" in reasons_text or "repetition" in reasons_text:
                    bucket = "language_flow"
                elif "composite" in reasons_text or "autofail" in reasons_text:
                    bucket = "low_composite"
                else:
                    bucket = "instruction_quality"
            
            clusters[bucket].append((key, rec))
        
        # Write cluster summaries
        for bucket in sorted(clusters.keys()):
            records = clusters[bucket]
            md.write(f"\n### {bucket.replace('_', ' ').title()} ({len(records)} scenarios)\n\n")
            
            for key, rec in sorted(records):
                scenario_id = rec.get("scenario_id", "unknown")
                run_num = rec.get("run_number", 0)
                composite = rec.get("composite_score", 0)
                expected_tools = rec.get("expected_tools", [])
                tools_called = rec.get("tools_called", [])
                missing = [t for t in expected_tools if t not in tools_called]
                
                # Get first turn utterance
                first_turn = "(no turns)"
                turns = rec.get("turns", [])
                if turns and len(turns) > 0:
                    first_turn = str(turns[0].get("user_utterance", ""))[:60]
                
                md.write(f"**{scenario_id}_run{run_num}** (composite: {composite:.0f}/100)\n\n")
                
                # Dimension breakdown
                dims = {
                    "task": rec.get("score_task", 0),
                    "language": rec.get("score_language", 0),
                    "instruction": rec.get("score_instruction", 0),
                    "flow": rec.get("score_flow", 0),
                }
                dim_str = " | ".join(f"{k}:{v:.0f}" for k, v in dims.items() if v < 100)
                if dim_str:
                    md.write(f"- Weak dimensions: {dim_str}\n")
                
                # Expected vs called
                md.write(f"- Expected tools: {expected_tools}\n")
                md.write(f"- Tools called: {tools_called}\n")
                if missing:
                    md.write(f"- **Missing:** {missing}\n")
                
                # Failure reasons
                if rec.get("failure_reasons"):
                    md.write(f"- Failure reasons:\n")
                    for reason in rec["failure_reasons"][:2]:
                        md.write(f"  - {reason}\n")
                
                md.write(f"- First turn: \"{first_turn}\"\n\n")
        
        # Timeouts
        if timeouts:
            md.write(f"\n## Timeouts: Pipeline Infrastructure Issues ({len(timeouts)} scenarios)\n\n")
            md.write("These are infrastructure failures, not model quality issues.\n\n")
            
            for key in sorted(timeouts.keys()):
                rec = timeouts[key]
                scenario_id = rec.get("scenario_id", "unknown")
                run_num = rec.get("run_number", 0)
                md.write(f"- {scenario_id}_run{run_num}: {rec.get('error', 'timeout')}\n")
            
            md.write("\n")
        
        # Recommendations
        md.write("\n## Recommended Fix Strategies\n\n")
        md.write("""
### A. Runtime Policy — `get_menu` Idempotency (Quick Win)
**Files:** `server/training/conversation_loop.py` (~250–310) or shared `_parse_tool_calls`

**Change:** Track the first `get_menu` call per conversation. Strip or no-op any subsequent `[TOOL:get_menu]` before the auditor sees it.

**Why:** Eliminates the "exactly once" instruction collision without modifying the prompt.

**Effort:** Low (few lines in tool parser)

**Expected impact:** Fixes scenarios where duplicate `get_menu` is a false-positive.

---

### B. Prompt Structure Alignment (Medium)
**File:** `server/training/tier2_runner.py` (~104–158)

**Option 1:** Remove pre-embedded menu facts. Keep only `get_menu` instruction with placeholder.

**Option 2:** Restructure prompt so pre-menu facts are only activated **after** `get_menu` is called.

**Why:** Resolves the fundamental contradiction between "must call get_menu" and "already know menu".

**Effort:** Medium (rewrite prompt, test for regressions)

**Expected impact:** Fixes scenarios with menu-first requirements.

---

### C. Scenario Repair (High-Value)
**File:** `server/scenarios/tier2_scenarios.py` (~1036–1049)

**Action:**
1. **Replace `TIER2_TOOL_EDGE_CASES_EXTRA`** with scenarios that have coherent openers and tool expectations.
2. **Fix t2-ord-05**: Add `"get_menu"` to expected_tools or update scenario to avoid allergen-first logic.
3. **Audit all `expected_tools`** against the global prompt rules.

**Why:** Removes eval-design errors; failures become pure model quality.

**Effort:** High (edit ~40+ scenarios)

**Expected impact:** Eliminates false-positive failures from scenario misalignment.

---

### D. Auditor Extension (Optional)
**File:** `server/training/call_auditor_de.py` (~54–60)

**Change:** 
- Add `faq` to `ALL_TOOLS` for consistency.
- Optionally add **per-tool `max_count` rules** for specific scenarios.

**Effort:** Low

**Expected impact:** Clarifies tool parsing; allows fine-grained validation.

---

### E. GPT Caller Tightening (Medium)
**File:** `server/training/conversation_loop.py` (~40–50: PERSONAS)

**Change:** For tool edge-case categories, tighten GPT system prompts so the **user simulation matches the scenario intent**.

**Effort:** Medium (rewrite personas + test)

**Expected impact:** Eliminates ambiguous scenarios.

---

### F. Production Gate: Quarantine Bulk-Generated Scenarios (Quick)
**Action:** Temporarily disable `TIER2_TOOL_EDGE_CASES_EXTRA` from production runs.

**Effort:** Very Low

**Expected impact:** Removes ~20 unreliable failure signals.

---

## Summary

**Quick Wins (implement first):**
1. ✓ Strategy A: Runtime `get_menu` idempotency
2. ✓ Strategy F: Quarantine bad bulk scenarios
3. ✓ Fix t2-ord-05 expected_tools conflict

**Medium-term (for production readiness):**
4. Strategy B: Simplify prompt, remove embedded menu facts
5. Strategy C: Audit and repair remaining scenarios
6. Strategy E: Tighten GPT personas for edge categories

**Result:** Production-ready bot with genuine quality issues isolated from eval-design problems.
""")
    
    print(f"✅ Report written to {output_path}")
    print(f"   Total failures analyzed: {len(failures)}")
    print(f"   Total timeouts: {len(timeouts)}")

if __name__ == "__main__":
    main()
