"""
Finalized 15 situation styles per Phase 7 Task 7.6.

Each entry is a plain dict with three keys:
  tag        — Gemini inline emotion tag (e.g. "[warm]"), injected by tts_client.py.
  rate       — per-situation speaking rate multiplier (before baseline × mood).
  prompt_add — German prompt fragment appended to the LLM system prompt for
               this situation. Layer 2 inlines this into the style_instruction.

Per tts-situations: keep-15 — these 15 keys are the agreed surface.
Per tts-emotion-tags: gemini-only — tags are injected only for Gemini voices;
   tts_client.prepare_text_for_tts() strips them for non-Gemini voices.

These rate values are situation-relative; the final speaking rate is:
   final = baseline × rate × mood_rate_mul   (clamped 0.75–2.0)
Baseline is tenant-specific (from tenant YAML tts.speed_multiplier).
"""
from __future__ import annotations

SITUATION_STYLES: dict[str, dict] = {
    "GREETING_FIRST": {
        "tag": "[warm]",
        "rate": 1.05,
        "prompt_add": "Beginne mit hörbarem Lächeln. Begrüße kurz und freundlich.",
    },
    "GREETING_RETURNING": {
        "tag": "[warm]",
        "rate": 1.0,
        "prompt_add": "Persönlicher Ton, kurz: «Schön, dass Sie wieder anrufen.»",
    },
    "INFO_NEUTRAL": {
        "tag": "[friendly]",
        "rate": 1.0,
        "prompt_add": "Sachlich freundlich, klar, gleichmäßiges Tempo.",
    },
    "INFO_READBACK": {
        "tag": "[attentive]",
        "rate": 0.88,
        "prompt_add": (
            "Bewusst langsamer und deutlich artikuliert. "
            "Pausiere zwischen Zifferngruppen."
        ),
    },
    "CLARIFY_PATIENT": {
        "tag": "[patient]",
        "rate": 0.93,
        "prompt_add": (
            "Ruhig und freundlich, kein Vorwurf — der Anrufer wird verstanden."
        ),
    },
    "CONFIRM_SUCCESS": {
        "tag": "[cheerful]",
        "rate": 1.0,
        "prompt_add": "Aufrichtig, zurückhaltend fröhlich. Nicht überschwänglich.",
    },
    "UPSELL_CURIOUS": {
        "tag": "[inviting]",
        "rate": 1.02,
        "prompt_add": "Einladend, wie ein guter Vorschlag — nicht aufdringlich.",
    },
    "APOLOGY_SOFT": {
        "tag": "[empathetic]",
        "rate": 0.92,
        "prompt_add": "Aufrichtige Entschuldigung für eine Kleinigkeit, ruhig.",
    },
    "APOLOGY_SERIOUS": {
        "tag": "[sympathetic]",
        "rate": 0.88,
        "prompt_add": "Ernsthaft, verantwortungsvoll, deutlich langsamer.",
    },
    "HANDOFF_CALM": {
        "tag": "[calm]",
        "rate": 0.95,
        "prompt_add": "Ruhig und kompetent. «Sie sind in guten Händen.»",
    },
    "ESCALATION_REASSURING": {
        "tag": "[reassuring]",
        "rate": 0.92,
        "prompt_add": (
            "Beruhigend und kompetent, nicht zu süß. "
            "Der Anrufer wird ernstgenommen."
        ),
    },
    "URGENT_CLEAR": {
        "tag": "[urgent]",
        "rate": 1.05,
        "prompt_add": "Etwas zügiger, klar, kein Druck.",
    },
    "WAITING_FILLER": {
        "tag": "[thoughtful]",
        "rate": 1.0,
        "prompt_add": "Kurze Brücke: «Einen Moment, ich prüfe das.»",
    },
    "REPROMPT_UNDERSTOOD_NONE": {
        "tag": "[understanding]",
        "rate": 0.90,
        "prompt_add": (
            "Geduldig und verständnisvoll. Keine Frustration in der Stimme."
        ),
    },
    "FAREWELL_WARM": {
        "tag": "[warm]",
        "rate": 0.98,
        "prompt_add": "Freundlich entspannt. «Vielen Dank für Ihren Anruf.»",
    },
}

# Convenience sets for validation
ALL_SITUATIONS: frozenset[str] = frozenset(SITUATION_STYLES)
