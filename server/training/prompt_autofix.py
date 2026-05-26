"""
prompt_autofix.py — AI-powered per-scenario prompt self-learning.

Called by audio_training_loop._per_scenario_fix_loop() for each failed scenario:
  1. Analyzes auditor failure_reasons + transcript samples + 10D scores
  2. Calls Gemini (Flash Lite for attempts 1-3, Flash for 4-5) to generate improved prompt
  3. Returns FixResult with the new prompt — caller replays and re-audits
"""

import asyncio
import logging
import os
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

AUTOFIX_MODEL_LITE = "gemini-2.5-flash"
AUTOFIX_MODEL_FULL = "gemini-2.5-flash"

MIN_FAILURES_TO_FIX = 1      # per-scenario mode: even 1 failure triggers
MAX_FIXES_PER_PHASE = 50     # generous cap for per-scenario fixes
AUTOFIX_COST_LIMIT  = 10.0   # $10 budget for self-learning

MAX_TRANSCRIPT_SAMPLES = 3


@dataclass
class FixRequest:
    phase: int
    failure_pattern: str
    failure_count: int
    failure_reasons: List[str]
    sample_transcripts: List[Dict]
    current_prompt: str
    dim_scores: Dict[str, float]
    attempt_number: int = 1
    prior_attempts: List[str] = None
    failure_kb_context: str = ""


@dataclass
class FixResult:
    success: bool
    improved_prompt: str
    explanation: str
    model_used: str
    tokens_used: int = 0
    cost_usd: float = 0.0


async def _call_gemini(prompt_text: str, project_id: str, creds_path: str,
                       model: str = AUTOFIX_MODEL_LITE) -> str:
    """Call Gemini model. Returns raw text response."""
    from google import genai
    from google.genai import types as genai_types
    from google.oauth2 import service_account as _sa

    credentials = _sa.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    region = os.environ.get("GEMINI_REGION", "europe-west4")
    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=region,
        credentials=credentials,
    )

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model=model,
            contents=[genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=prompt_text)],
            )],
            config=genai_types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2000,
                system_instruction=(
                    "Du bist ein Experte fuer Voice-AI-Systeme. "
                    "Du verbesserst System-Prompts fuer deutsche Restaurant-KI-Assistenten. "
                    "Antworte NUR mit dem verbesserten Prompt — kein Kommentar davor oder danach."
                ),
            ),
        ),
    )
    return response.text.strip()


def _build_fix_prompt(req: FixRequest) -> str:
    samples_text = ""
    for i, t in enumerate(req.sample_transcripts[:MAX_TRANSCRIPT_SAMPLES], 1):
        samples_text += f"\nBeispiel {i}:\n"
        for turn in t.get("turns", [])[:8]:
            caller = turn.get("user_utterance", "")
            bot = turn.get("llm_response", "")
            samples_text += f"  Anrufer: {caller}\n"
            samples_text += f"  Bot: {bot}\n"

    scores_text = "\n".join(
        f"  {k}: {v:.1f}/100"
        for k, v in sorted(req.dim_scores.items(), key=lambda x: x[1])
    )

    focus_map = {
        "loop":         "Wiederholung — der Bot gibt dieselbe Antwort in jedem Zug oder ruft get_menu immer wieder auf",
        "language":     "Sprachverletzung — der Bot antwortet auf Englisch oder nutzt 'du' statt 'Sie'",
        "task":         "Aufgabe nicht abgeschlossen — Bot hat benoetigte Tools NICHT aufgerufen. HÄUFIGSTE Ursache: Bot sammelt Infos aber ruft create_order/create_reservation/send_sms/technical_issues_callback NIEMALS auf. Bot MUSS Tools sofort aufrufen sobald genug Infos vorliegen!",
        "flow":         "Gespraechsfluss — Bot stellt keine Fragen, antwortet nicht auf Kontext",
        "instruction":  "Instruktionsfehler — zu kurze oder zu lange Antworten",
        "completeness": "Unvollstaendig — fehlende Begruessung oder fehlender Abschluss",
        "response":     "Qualitaet — der Bot weicht aus oder gibt inhaltsleere Antworten",
        "hallucination":"Halluzination — der Bot erfindet Fakten oder gibt sich als KI zu erkennen",
    }
    focus = focus_map.get(req.failure_pattern, req.failure_pattern)

    prior_text = ""
    if req.prior_attempts:
        prior_text = "\n\n## VORHERIGE FIX-VERSUCHE (haben NICHT funktioniert):\n"
        for pa in req.prior_attempts:
            prior_text += f"- {pa}\n"
        prior_text += "\nWICHTIG: Versuche einen ANDEREN Ansatz als die vorherigen Versuche!\n"

    task_hint = ""
    if req.failure_pattern == "task" or req.dim_scores.get("task", 100) < 40:
        task_hint = """
## KRITISCH — TOOL-FORMAT + AKTIONS-REGELN (MUSS im neuen Prompt stehen):
Der Bot gibt NUR Textantworten. Tools werden durch Text-Tags ausgeloest.
Der neue Prompt MUSS diese Regeln enthalten:

  TOOL-FORMAT (PFLICHT): Schreibe [TOOL:toolname] in jede Antwort wo ein Tool benoetigt wird.
  Beispiel: "Ich erstelle Ihre Bestellung. [TOOL:create_order] Bestätigung folgt per SMS. [TOOL:send_sms]"
  OHNE [TOOL:...] wird das Tool NICHT erkannt — Task-Score bleibt 0!

  BESTELLUNG: Sobald Artikel + Name + Telefon bekannt → SOFORT [TOOL:create_order] → dann [TOOL:send_sms]!
  RESERVIERUNG: Sobald Datum + Uhrzeit + Personen + Name bekannt → SOFORT [TOOL:create_reservation]!
  TECHNISCH: App kaputt, Fehler, Störung → SOFORT [TOOL:technical_issues_callback]! NIEMALS transfer_to_human!
  get_menu: MAXIMAL 1x pro Gespräch aufrufen, danach aus dem Gedächtnis antworten!
  NIEMALS [TOOL:transfer_to_ordering] fuer Bestellungen oder Reservierungen!
  Der Bot MUSS proaktiv handeln — NICHT endlos Fragen stellen oder get_menu wiederholen!

"""

    return f"""
Du analysierst einen fehlgeschlagenen KI-Assistenten fuer das Restaurant DOBOO in Bonn.

## FIX-VERSUCH {req.attempt_number}/5

## HAUPTPROBLEM ({req.failure_count} Fehler):
{focus}
{task_hint}
## AUDITOREN-BEFUNDE:
{chr(10).join(f"- {r}" for r in req.failure_reasons[:10])}

## DIMENSION-SCORES (niedrig = schlecht):
{scores_text}

## BEISPIEL-GESPRAECHE (zeigen das Problem):
{samples_text}
{prior_text}
## WISSENSBASIS — Bekannte Fehler und bisherige Fix-Versuche (RAG):
{req.failure_kb_context if req.failure_kb_context else "(keine bisherigen Eintraege)"}

REGELN fuer die Wissensbasis:
- Vermeide Ansaetze die oben als GESCHEITERT markiert sind
- Wenn ein aehnlicher Fehler GELOEST wurde, verwende denselben Ansatz
- HÄUFIGSTES PROBLEM: Bot sammelt alle Infos, ruft aber create_order/create_reservation NIEMALS auf!
  FIX: Prompt muss TRIGGER-BEDINGUNGEN enthalten: "Sobald X+Y+Z bekannt → SOFORT [TOOL:create_order]"
- Bot spammt get_menu 5+ mal statt zu handeln. FIX: get_menu MAXIMAL 1x pro Gespräch!
- send_sms MUSS nach JEDER Bestellung (create_order) gesendet werden — keine Ausnahme!
- technical_issues_callback bei technischen Problemen — NICHT transfer_to_human!
- NIEMALS transfer_to_ordering fuer Bestellungen/Reservierungen!

## AKTUELLER SYSTEM-PROMPT (der verbessert werden muss):
{req.current_prompt}

## AUFGABE:
Schreibe einen VERBESSERTEN System-Prompt der:
1. Das Hauptproblem ({focus}) behebt
2. TOOL-FORMAT-REGEL enthaelt: erklaere [TOOL:toolname] als Pflichtformat in jeder Tool-Antwort
3. Deutsch mit Sie-Form beibehält
4. Tool-Aufrufe korrekt anleitet: get_menu, check_availability, create_reservation, create_order,
   send_sms, technical_issues_callback, verify_address, update_state, transfer_to_human, end_call
   (send_sms nach jeder Bestellung! technical_issues_callback bei technischen Problemen!)
5. DOBOO Bonn (koreanische Kueche) als Kontext behält
6. Max 2 Saetze pro Antwort
7. NIEMALS dieselbe Antwort zweimal in einem Gespraech (anti-loop)
8. Auf jede Frage des Anrufers inhaltlich eingeht
9. Gespraechsfluss: Begruessung -> Bedarf verstehen -> Info sammeln -> Tools -> Bestaetigung -> Abschluss

Schreibe NUR den verbesserten Prompt!
"""


def detect_dominant_failure(failure_reasons: List[str]) -> str:
    patterns = {
        "loop":         ["loop", "wiederh", "repetit", "same response", "3+"],
        "language":     ["english", "language score", "englisch", "spoke english"],
        "task":         ["task score", "missing tool", "tools:", "expected tool"],
        "flow":         ["flow score", "dead-end", "no questions", "conversation loop"],
        "instruction":  ["instruction score", "too-short", "too-long", "verbose"],
        "completeness": ["completeness score", "no end_call", "greeting"],
        "response":     ["response score", "deflect", "empty"],
        "hallucination":["hallucination", "fabricat", "forbidden"],
        "latency":      ["latency score", "p90", "p50"],
        "audio":        ["audio score", "cut-off", "tts"],
        "stt":          ["stt", "wer"],
    }

    counts = Counter()
    for reason in failure_reasons:
        r = reason.lower()
        for pattern, keywords in patterns.items():
            if any(kw in r for kw in keywords):
                counts[pattern] += 1

    return counts.most_common(1)[0][0] if counts else "flow"


async def ai_autofix_prompt(
    phase: int,
    recent_records: List[Any],
    current_prompt: str,
    project_id: str,
    creds_path: str,
    fixes_done: int = 0,
    total_cost_spent: float = 0.0,
    model_override: Optional[str] = None,
    attempt_number: int = 1,
    prior_attempts: Optional[List[str]] = None,
    failure_kb_context: str = "",
) -> Optional[FixResult]:
    """
    Generate an improved prompt from auditor failures.
    failure_kb_context: RAG context from failure_report.json with known failures and fix outcomes
    """
    if fixes_done >= MAX_FIXES_PER_PHASE:
        return None

    if total_cost_spent >= AUTOFIX_COST_LIMIT:
        return None

    failed_records = [r for r in recent_records if not r.passed]
    if len(failed_records) < MIN_FAILURES_TO_FIX:
        return None

    all_reasons: List[str] = []
    for rec in failed_records:
        all_reasons.extend(getattr(rec, "failure_reasons", []))

    if not all_reasons:
        return None

    dominant = detect_dominant_failure(all_reasons)

    dim_keys = [
        "score_task", "score_language", "score_instruction", "score_latency",
        "score_audio", "score_stt", "score_flow", "score_response",
        "score_hallucination", "score_completeness",
    ]
    dim_scores: Dict[str, float] = {}
    for key in dim_keys:
        vals = [getattr(r, key, 0.0) for r in failed_records if hasattr(r, key)]
        if vals:
            dim_scores[key.replace("score_", "")] = sum(vals) / len(vals)

    sorted_fails = sorted(
        failed_records,
        key=lambda r: getattr(r, "composite_score", 100),
    )
    sample_transcripts = []
    for rec in sorted_fails[:MAX_TRANSCRIPT_SAMPLES]:
        turns = [
            {"user_utterance": t.user_utterance, "llm_response": t.llm_response}
            for t in getattr(rec, "turns", [])
        ]
        sample_transcripts.append({"scenario_id": rec.scenario_id, "turns": turns})

    req = FixRequest(
        phase=phase,
        failure_pattern=dominant,
        failure_count=len(failed_records),
        failure_reasons=list(set(all_reasons))[:15],
        sample_transcripts=sample_transcripts,
        current_prompt=current_prompt,
        dim_scores=dim_scores,
        attempt_number=attempt_number,
        prior_attempts=prior_attempts or [],
        failure_kb_context=failure_kb_context,
    )

    model = model_override or AUTOFIX_MODEL_LITE

    logger.warning(
        f"⚡ [SELF-LEARN] Phase {phase} attempt {attempt_number}: "
        f"{len(failed_records)} failures, dominant={dominant} -> {model}"
    )

    try:
        fix_prompt_text = _build_fix_prompt(req)
        improved = await _call_gemini(fix_prompt_text, project_id, creds_path, model=model)

        if len(improved) < 100:
            return FixResult(
                success=False, improved_prompt=current_prompt,
                explanation="Response too short", model_used=model,
            )

        # Ensure tool-format block is present (critical for T:0 failures)
        if "[TOOL:" not in improved:
            tool_format_block = (
                "\n\nTOOL-FORMAT (PFLICHT): Schreibe [TOOL:toolname] in jede Antwort wo ein Tool benoetigt wird. "
                "Beispiel: 'Ich erstelle Ihre Bestellung. [TOOL:create_order] Bestätigung per SMS. [TOOL:send_sms]'\n"
                "OHNE [TOOL:...] wird das Tool NICHT erkannt — Task-Score bleibt 0!\n"
                "SOFORT-REGELN: Artikel+Name+Telefon → [TOOL:create_order] → [TOOL:send_sms]. "
                "Datum+Uhrzeit+Personen+Name → [TOOL:create_reservation]. "
                "Technisches Problem → [TOOL:technical_issues_callback] (NICHT transfer_to_human!). "
                "get_menu MAXIMAL 1x pro Gespräch! "
                "NIEMALS [TOOL:transfer_to_ordering] fuer Bestellungen/Reservierungen!"
            )
            improved += tool_format_block
            logger.info("  Injected [TOOL:...] format block into AI-generated prompt")

        est_cost = 0.0003 if "lite" in model else (0.005 if "pro" in model else 0.001)

        return FixResult(
            success=True,
            improved_prompt=improved,
            explanation=f"Fix attempt {attempt_number}: {dominant} — {len(failed_records)} failures",
            model_used=model,
            cost_usd=est_cost,
        )

    except Exception as e:
        logger.error(f"⚡ [SELF-LEARN] {model} failed: {e}")
        # Try fallback if lite failed
        if "lite" in model:
            try:
                improved = await _call_gemini(
                    _build_fix_prompt(req), project_id, creds_path,
                    model=AUTOFIX_MODEL_FULL
                )
                if len(improved) >= 100:
                    return FixResult(
                        success=True, improved_prompt=improved,
                        explanation=f"Fix attempt {attempt_number} (fallback): {dominant}",
                        model_used=AUTOFIX_MODEL_FULL, cost_usd=0.001,
                    )
            except Exception as e2:
                logger.error(f"⚡ [SELF-LEARN] Fallback also failed: {e2}")

        return FixResult(
            success=False, improved_prompt=current_prompt,
            explanation=f"Error: {e}", model_used=model,
        )
