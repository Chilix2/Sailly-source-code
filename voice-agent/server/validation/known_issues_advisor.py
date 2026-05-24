"""
Known Issues Advisor — matches current batch failure pattern against the complete issue library
and automatically records every fix attempt outcome back into known_issues.json.

Reads known_issues.json (53 issues, sourced from 60 batch results + 8 agent transcripts +
9 git commits + FIX_VALIDATION_IMPLEMENTATION_GUIDE.md) and injects a curated context block
into every Haiku fix prompt containing:
  - Root causes of matched known issues
  - What was tried and FAILED (do not repeat)
  - What is CONFIRMED to work (start here)
  - Mandatory Python 3.12+ / indentation code quality rules
  - Fix effectiveness index (score delta evidence)

Auto-update (called from scenario_based_loop after each scored attempt):
    advisor.update_from_fix_result(
        fix_plan=fix_plan,          # the Haiku-generated fix dict
        score_before=45.0,          # composite score BEFORE the fix
        score_after=72.0,           # composite score AFTER the fix
        batch_key="A1.7_D2",        # e.g. "A1.7_D2"
        attempt=3,                  # attempt number
    )
  → Writes outcome into known_issues.json under the matched issue's fix_attempts list.
  → Promotes fixes that improve score >= 10 pts to confirmed_working_fixes.
  → Unknown fixes go into "unmatched_fix_log" for manual review.

Usage:
    from server.validation.known_issues_advisor import KnownIssuesAdvisor
    advisor = KnownIssuesAdvisor()
    block = advisor.get_advice_block(grok_report, call_metrics, batch_key="A1.7_D2")
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_LIBRARY_PATH = Path(__file__).parent / "known_issues.json"

# ── Scoring weights ──────────────────────────────────────────────────────────
_W_FLAG_EXACT   = 15   # achtung flag exact match
_W_KEYWORD      = 3    # grok text keyword match
_W_METRIC       = 4    # low-metric match
_W_PHASE_EXACT  = 8    # exact phase match (e.g. A1.7)
_W_PHASE_PREFIX = 4    # phase prefix match (e.g. A1)
_W_CATEGORY_FAQ = 6    # special bonus for intent_misdetect when A2.x
_THRESHOLD      = 6    # minimum score to include issue in advice

# These categories are ALWAYS included (code quality, critical bugs)
_ALWAYS_INCLUDE_IDS = {"PYTHON312_SCOPE_001", "INDENTATION_HAIKU_001"}

# Maximum issues to show (to avoid making prompt too long)
_MAX_ISSUES = 5


class KnownIssuesAdvisor:
    def __init__(self, library_path: Optional[Path] = None):
        path = library_path or _LIBRARY_PATH
        try:
            self._db = json.loads(path.read_text(encoding="utf-8"))
            self._issues: List[Dict] = self._db.get("issue_library", [])
            self._effectiveness: Dict = self._db.get("fix_effectiveness_index", {})
            self._phase_summary: Dict = self._db.get("phase_summary", {})
            logger.info("[advisor] Loaded %d known issues from %s (schema v%s)",
                        len(self._issues), path.name,
                        self._db.get("_meta", {}).get("schema_version", "?"))
        except Exception as exc:
            logger.warning("[advisor] Could not load known_issues.json: %s", exc)
            self._issues = []
            self._effectiveness = {}
            self._phase_summary = {}

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def get_advice_block(
        self,
        grok_report: Dict[str, Any],
        call_metrics: Dict[str, Any],
        batch_key: Optional[str] = None,
    ) -> str:
        if not self._issues:
            return ""

        matched, always = self._match_issues(grok_report, call_metrics, batch_key)
        if not matched and not always:
            return ""

        lines: List[str] = [
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "KNOWN ISSUE LIBRARY — READ BEFORE GENERATING FIXES",
            "Sources: 60 batch results + 8 transcripts + 9 git commits (Apr 27–May 18)",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "CRITICAL: These document what was already tried (and FAILED) and what is",
            "CONFIRMED to work. Repeating a failed fix wastes tokens and degrades score.",
            "",
        ]

        # Phase summary if batch_key known
        if batch_key:
            phase_info = self._phase_advice(batch_key)
            if phase_info:
                lines.append(phase_info)
                lines.append("")

        # Matched issues
        for score, issue in matched[:_MAX_ISSUES]:
            lines.extend(self._format_issue(issue, score))

        # Always-include code quality issues (compacted)
        code_quality = [i for i in always if i["id"] not in {i["id"] for _, i in matched}]
        if code_quality:
            lines.append("━━ MANDATORY CODE QUALITY RULES (Haiku frequently violates these) ━━")
            for issue in code_quality:
                lines.extend(self._format_code_quality(issue))

        # Fix effectiveness index (evidence of what score delta to expect)
        eff_block = self._effectiveness_block(matched)
        if eff_block:
            lines.append(eff_block)

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    # Matching
    # ──────────────────────────────────────────────────────────────────────────

    def _match_issues(
        self,
        grok_report: Dict[str, Any],
        call_metrics: Dict[str, Any],
        batch_key: Optional[str],
    ) -> Tuple[List[Tuple[int, Dict]], List[Dict]]:
        """Returns (scored_matched_issues, always_include_issues)."""

        # Extract achtung flag codes
        all_flags: List[str] = []
        for f in (grok_report.get("achtung_flags") or []):
            m = re.search(r"Achtung Sailly: ([A-Z_]+)", f.get("flag", ""))
            if m:
                all_flags.append(m.group(1))
        for f in (call_metrics.get("achtung_flags") or []):
            m = re.search(r"Achtung Sailly: ([A-Z_]+)", f.get("flag", ""))
            if m:
                all_flags.append(m.group(1))
        if call_metrics.get("loop_detections"):
            all_flags.append("BOT_LOOP")

        # Text for keyword matching
        combined_text = " ".join([
            (grok_report.get("improvements") or ""),
            (grok_report.get("tool_analysis") or ""),
            (call_metrics.get("conversation_issues") and
             json.dumps(call_metrics["conversation_issues"][:3])) or "",
        ]).lower()

        # Low metrics
        scores = grok_report.get("metric_scores", {})
        low_metrics = {k for k, v in scores.items() if isinstance(v, (int, float)) and v < 60}

        # Phase prefix extraction
        phase_exact = batch_key or ""         # e.g. "A1.7_D2"
        phase_prefix = ""
        if batch_key and "_" in batch_key:
            parts = batch_key.split("_")
            phase_exact = parts[0]            # "A1.7"
            phase_prefix = re.match(r"[A-Z]\d", parts[0]).group() if re.match(r"[A-Z]\d", parts[0]) else ""  # "A1"

        always: List[Dict] = []
        scored: List[Tuple[int, Dict]] = []
        seen_ids: set = set()

        for issue in self._issues:
            issue_id = issue["id"]

            # Always-include code quality issues
            if issue_id in _ALWAYS_INCLUDE_IDS:
                always.append(issue)
                seen_ids.add(issue_id)
                continue

            score = 0

            # Achtung flag exact match
            for fc in all_flags:
                if fc in issue.get("achtung_flags", []):
                    score += _W_FLAG_EXACT

            # Keyword match in Grok text
            for kw in issue.get("grok_pattern_keywords", []):
                if kw.lower() in combined_text:
                    score += _W_KEYWORD

            # Metric match
            for metric in low_metrics:
                if metric in issue.get("affects_metrics", []):
                    score += _W_METRIC

            # Phase match
            for phase in issue.get("affected_phases", []):
                if phase == phase_exact:
                    score += _W_PHASE_EXACT
                elif phase_prefix and (phase.startswith(phase_prefix) or phase_prefix in phase):
                    score += _W_PHASE_PREFIX

            # Bonus: A2.x with INTENT_MISDETECT
            if phase_prefix == "A2" and issue.get("category") == "intent_detection":
                score += _W_CATEGORY_FAQ

            if score >= _THRESHOLD and issue_id not in seen_ids:
                scored.append((score, issue))
                seen_ids.add(issue_id)

        scored.sort(key=lambda x: -x[0])
        return scored, always

    # ──────────────────────────────────────────────────────────────────────────
    # Formatting
    # ──────────────────────────────────────────────────────────────────────────

    def _format_issue(self, issue: Dict, score: int) -> List[str]:
        lines = [
            f"▶ [{issue['id']}] {issue['title']}  (relevance={score})",
            f"  Category: {issue['category']}  |  Severity: {issue['severity']}  |  "
            f"Files: {', '.join(issue.get('affected_files', [])[:2])}",
            f"  ROOT CAUSE: {issue['root_cause'][:300]}",
        ]

        examples = issue.get("observed_examples", [])
        if examples:
            lines.append(f"  Examples: {examples[0][:120]}")

        failed = [a for a in issue.get("fix_attempts", [])
                  if "fail" in a.get("outcome", "").lower()]
        if failed:
            lines.append(f"  FAILED FIXES — DO NOT REPEAT:")
            for f in failed[:2]:
                desc = f.get("description", "")[:100]
                lesson = f.get("lesson", "")[:100]
                lines.append(f"    ✗ {desc}")
                if lesson:
                    lines.append(f"      Lesson: {lesson}")

        confirmed = issue.get("confirmed_working_fixes", [])
        if confirmed:
            lines.append(f"  CONFIRMED WORKING — START HERE:")
            for c in confirmed[:3]:
                lines.append(f"    ✓ {c[:160]}")

        lines.append("")
        return lines

    def _format_code_quality(self, issue: Dict) -> List[str]:
        """Compact format for code quality issues."""
        lines = [f"  [{issue['id']}] {issue['title']}"]
        for fix in issue.get("confirmed_working_fixes", [])[:4]:
            lines.append(f"    • {fix[:150]}")
        lines.append("")
        return lines

    def _phase_advice(self, batch_key: str) -> str:
        """Return a one-line phase-level context if known."""
        phase_prefix = re.match(r"([A-Z]\d)", batch_key)
        if not phase_prefix:
            return ""
        prefix = phase_prefix.group(1)
        for phase_key, info in self._phase_summary.items():
            if phase_key.startswith(prefix):
                return (
                    f"PHASE {phase_key} STATUS: {info.get('status','?').upper()}  |  "
                    f"Best: {info.get('best_pass_rate','?')}  |  "
                    f"Primary issues: {', '.join(info.get('primary_issues', [])[:3])}"
                )
        return ""

    def _effectiveness_block(self, matched: List[Tuple[int, Dict]]) -> str:
        """Return score-delta evidence for matched issue categories."""
        if not self._effectiveness:
            return ""
        lines = ["━━ FIX EFFECTIVENESS INDEX (score evidence from past runs) ━━"]
        count = 0
        for key, entry in self._effectiveness.items():
            verdict = entry.get("verdict", "")
            if "WORKS" in verdict and count < 4:
                delta = entry.get("score_delta", "")
                desc = entry.get("description", "")[:80]
                lines.append(f"  ✓ {desc}: {delta} → {verdict}")
                count += 1
            elif "CATASTROPHIC" in verdict or "FAILED" in verdict:
                desc = entry.get("description", "")[:80]
                lines.append(f"  ✗ {desc}: NEVER USE — {entry.get('verdict','')[:60]}")
        lines.append("")
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    # Auto-update: record fix outcomes back into known_issues.json
    # ──────────────────────────────────────────────────────────────────────────

    def update_from_fix_result(
        self,
        fix_plan: Dict[str, Any],
        score_before: float,
        score_after: float,
        batch_key: str,
        attempt: int,
        passed_before: int = 0,
        passed_after: int = 0,
        total: int = 7,
    ) -> None:
        """
        Called after a batch attempt completes to record the fix outcome.

        For each fix in fix_plan["fixes"], finds the best-matching known issue
        and appends a fix_attempt entry. If score improved >= 10 pts, also
        promotes the fix description to confirmed_working_fixes.

        Unmatched fixes go to the top-level "unmatched_fix_log" list for
        manual review and future categorization.

        Thread-safe: uses atomic file replace (write to .tmp then rename).
        """
        if not fix_plan or not self._issues:
            return

        fixes = fix_plan.get("fixes", [])
        if not fixes:
            return

        delta = score_after - score_before
        if delta >= 10:
            outcome = "worked"
            verdict = f"WORKS — +{delta:.1f} pts ({score_before:.1f} → {score_after:.1f})"
        elif delta >= 3:
            outcome = "partial"
            verdict = f"PARTIAL — +{delta:.1f} pts ({score_before:.1f} → {score_after:.1f})"
        elif delta <= -3:
            outcome = "failed (regression)"
            verdict = f"REGRESSION — {delta:.1f} pts ({score_before:.1f} → {score_after:.1f})"
        else:
            outcome = "failed (no improvement)"
            verdict = f"NO IMPROVEMENT — {delta:.1f} pts ({score_before:.1f} → {score_after:.1f})"

        ts = time.strftime("%Y-%m-%d")
        unmatched: List[Dict] = []

        for fix in fixes:
            fix_desc = fix.get("issue", "")[:200]
            fix_reason = fix.get("reason", "")[:200]
            fix_files = [fix.get("file", "")]
            summary_text = f"{fix_desc} → {fix_reason}"

            # Find best matching known issue
            matched_issue = self._match_fix_to_issue(fix)

            attempt_entry = {
                "attempt_ref": f"{batch_key} attempt {attempt} ({ts})",
                "description": summary_text[:200],
                "files_changed": [f for f in fix_files if f],
                "outcome": outcome,
                "score_delta": f"{delta:+.1f} pts",
                "lesson": self._derive_lesson(outcome, fix_desc, fix_reason),
            }

            if matched_issue is not None:
                # Append to the matched issue's fix_attempts
                if "fix_attempts" not in matched_issue:
                    matched_issue["fix_attempts"] = []
                matched_issue["fix_attempts"].append(attempt_entry)

                # Promote to confirmed_working_fixes if clearly successful
                if outcome == "worked":
                    confirmed = matched_issue.setdefault("confirmed_working_fixes", [])
                    promotion = f"[AUTO {ts} +{delta:.1f}pts] {fix_desc[:120]}"
                    if promotion not in confirmed:
                        confirmed.append(promotion)
                    logger.info(
                        "[advisor] Promoted fix to confirmed_working_fixes in [%s]: %s",
                        matched_issue["id"], fix_desc[:60],
                    )
                elif outcome in ("failed (regression)", "failed (no improvement)"):
                    logger.info(
                        "[advisor] Recorded failed fix in [%s]: %s (delta=%+.1f)",
                        matched_issue["id"], fix_desc[:60], delta,
                    )
            else:
                unmatched.append({
                    "batch_key": batch_key,
                    "attempt": attempt,
                    "date": ts,
                    "fix_description": fix_desc,
                    "fix_reason": fix_reason,
                    "fix_file": fix.get("file", ""),
                    "outcome": outcome,
                    "score_delta": f"{delta:+.1f} pts",
                })
                logger.debug("[advisor] Fix did not match any known issue — added to unmatched_fix_log")

        # Update fix_effectiveness_index with aggregate result for this batch
        eff_key = f"auto_{batch_key}_attempt{attempt}_{ts}"
        self._effectiveness[eff_key] = {
            "description": f"Batch {batch_key} attempt {attempt}: {len(fixes)} fix(es)",
            "worked_in": [batch_key],
            "score_delta": f"{delta:+.1f} pts ({score_before:.1f} → {score_after:.1f}), {passed_after}/{total} passed",
            "verdict": verdict,
        }

        # Update phase_summary pass rates if improvement
        self._update_phase_summary(batch_key, passed_after, total, score_after)

        # Persist unmatched to the database
        if unmatched:
            existing = self._db.setdefault("unmatched_fix_log", [])
            existing.extend(unmatched)

        # Write back atomically
        self._save()
        logger.info(
            "[advisor] Updated known_issues.json — batch=%s attempt=%d delta=%+.1f outcome=%s (%d fixes, %d unmatched)",
            batch_key, attempt, delta, outcome, len(fixes), len(unmatched),
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers for auto-update
    # ──────────────────────────────────────────────────────────────────────────

    def _match_fix_to_issue(self, fix: Dict) -> Optional[Dict]:
        """
        Match a single Haiku-generated fix to a known issue.
        Returns the issue dict (mutable reference) or None.
        """
        fix_file = fix.get("file", "").lower()
        fix_text = (fix.get("issue", "") + " " + fix.get("reason", "")).lower()

        best_score = 0
        best_issue: Optional[Dict] = None

        for issue in self._issues:
            score = 0

            # File match
            for af in issue.get("affected_files", []):
                if af.lower() in fix_file or fix_file in af.lower():
                    score += 5

            # Keyword match
            for kw in issue.get("grok_pattern_keywords", []):
                if kw.lower() in fix_text:
                    score += 3

            # Category keywords in fix text
            cat = issue.get("category", "")
            cat_signals = {
                "date_time_parsing": ["datum", "date", "wochentag", "mai", "uhrzeit", "montag"],
                "bot_loop": ["loop", "wiederholung", "gleiche", "repeated", "was darf"],
                "tool_not_firing": ["create_reservation", "tool", "execute_tool", "commit"],
                "phone_extraction": ["telefon", "phone", "rückruf", "unter", "nummer"],
                "name_extraction": ["name", "anna", "contamination", "strategy 4", "vorname"],
                "state_machine": ["state", "readback_pending", "correction_pending", "finalized"],
                "pre_commit_summary": ["pre_commit", "readback", "stimmt das so", "zusammenfassung"],
                "slot_persistence": ["slot", "persist", "state", "entity"],
                "python_scoping": ["cannot access", "unboundlocal", "scoping", "indent"],
                "code_quality": ["indentation", "indent", "syntax", "scoping"],
                "hallucination_prevention": ["hallucin", "grounding", "fabricat", "ohne tool"],
                "tiny_generator": ["tinygenerator", "tiny", "max_tokens", "fallback"],
            }
            for signal in cat_signals.get(cat, []):
                if signal in fix_text:
                    score += 2

            if score > best_score:
                best_score = score
                best_issue = issue

        return best_issue if best_score >= 5 else None

    @staticmethod
    def _derive_lesson(outcome: str, fix_desc: str, fix_reason: str) -> str:
        """Auto-generate a lesson string based on outcome."""
        if "regression" in outcome:
            return f"This change regressed the score — check for unintended side-effects in shared pipeline code."
        if "no improvement" in outcome:
            return f"Fix applied but no score change — the root cause may be elsewhere or fix was too narrow."
        if outcome == "partial":
            return f"Partial improvement — correct direction but fix incomplete or covers only some scenarios."
        if outcome == "worked":
            return f"Confirmed working in live run."
        return ""

    def _update_phase_summary(self, batch_key: str, passed: int, total: int, score: float) -> None:
        """Update phase_summary best_pass_rate if this run is an improvement."""
        phase_prefix = re.match(r"([A-Z]\d)", batch_key)
        if not phase_prefix:
            return
        prefix = phase_prefix.group(1)
        for phase_key, info in self._phase_summary.items():
            if phase_key.startswith(prefix):
                current_best = info.get("best_pass_rate", "0/7")
                try:
                    current_n = int(current_best.split("/")[0])
                except (ValueError, IndexError):
                    current_n = 0
                if passed > current_n:
                    info["best_pass_rate"] = f"{passed}/{total} (batch {batch_key}, score {score:.1f})"
                    logger.info("[advisor] Updated phase_summary[%s] best_pass_rate → %d/%d", phase_key, passed, total)
                break

    def _save(self) -> None:
        """Atomically write the updated database back to disk."""
        tmp_path = self._library_path.with_suffix(".json.tmp")
        try:
            tmp_path.write_text(
                json.dumps(self._db, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp_path.replace(self._library_path)
        except Exception as exc:
            logger.error("[advisor] Failed to save known_issues.json: %s", exc)
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

    @property
    def _library_path(self) -> Path:
        return _LIBRARY_PATH
