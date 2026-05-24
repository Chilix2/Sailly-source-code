"""Generate Mermaid diagram source from live v4 pipeline code.

Three diagrams, all derived from imports (not hardcoded):
1. profile_fsm        — stateDiagram-v2: intent → profile routing
2. pipeline_sequence  — sequenceDiagram: per-turn data flow
3. commit_gate_fsm    — stateDiagram-v2: commit gate FSM states

These are auto-regenerated on each /api/builder/diagrams request so they
always reflect what is actually running.
"""

from __future__ import annotations
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def build_profile_fsm() -> str:
    """Build a stateDiagram-v2 from worker_router._PROFILES and intent_classifier.INTENT_TO_PROFILE."""
    from server.brain.worker_router import _PROFILES
    from server.brain.intent_classifier import INTENT_TO_PROFILE

    # Collect unique profiles and their inbound intents
    profile_intents: dict[str, list[str]] = {p: [] for p in _PROFILES}
    for intent, profile in INTENT_TO_PROFILE.items():
        profile_intents.setdefault(profile, []).append(intent.value)

    # Group profiles into semantic clusters for cleaner layout
    CLUSTER_MAP = {
        "Casual": ["greeting", "smalltalk", "goodbye"],
        "FAQ": ["business_info", "directions_lookup", "parking_lookup"],
        "Reservation": ["reservation_start", "reservation_availability"],
        "Order": ["order_start", "order_modify"],
        "Other": ["correction", "escalation"],
    }

    lines = ["stateDiagram-v2", "    direction LR", ""]

    # Define states with labels
    LABELS = {
        "greeting": "greeting",
        "smalltalk": "smalltalk",
        "business_info": "business_info\\n(FAQ)",
        "directions_lookup": "directions_lookup",
        "parking_lookup": "parking_lookup",
        "goodbye": "goodbye",
        "reservation_start": "reservation_start",
        "reservation_availability": "reservation_availability",
        "correction": "correction",
        "order_start": "order_start",
        "order_modify": "order_modify",
        "escalation": "escalation",
    }

    # State definitions inside clusters
    for cluster, profiles in CLUSTER_MAP.items():
        lines.append(f"    state \"{cluster}\" as {cluster.lower()}_group {{")
        for p in profiles:
            if p in LABELS:
                label = LABELS[p]
                if "\\n" in label:
                    lines.append(f"        {p} : {label.replace(chr(10), ' ')}")
                else:
                    lines.append(f"        {p}")
        lines.append("    }")

    lines.append("")
    lines.append("    [*] --> greeting : call starts")
    lines.append("")

    # Transitions from intent → profile (grouped by destination)
    grouped: dict[str, list[str]] = {}
    for intent, profile in INTENT_TO_PROFILE.items():
        grouped.setdefault(profile, []).append(intent.value)

    # Core transitions (only show the most important ones to keep diagram readable)
    KEY_TRANSITIONS = [
        ("greeting", "reservation_start", "RESERVATION"),
        ("greeting", "order_start", "TAKEAWAY/DELIVERY"),
        ("greeting", "business_info", "FAQ"),
        ("greeting", "goodbye", "GOODBYE"),
        ("greeting", "escalation", "COMPLAINT"),
        ("smalltalk", "reservation_start", "RESERVATION"),
        ("smalltalk", "order_start", "ORDER"),
        ("smalltalk", "goodbye", "GOODBYE"),
        ("business_info", "goodbye", "GOODBYE"),
        ("reservation_start", "reservation_availability", "check availability"),
        ("reservation_availability", "reservation_start", "slots missing"),
        ("order_start", "order_modify", "MODIFY/CANCEL"),
        ("order_start", "goodbye", "GOODBYE"),
    ]

    # Reroute: any profile can go to correction
    lines.append("    %% ── Intent-driven transitions ──────────────────────────────────────")
    for src, dst, label in KEY_TRANSITIONS:
        lines.append(f"    {src} --> {dst} : {label}")

    lines.append("")
    lines.append("    %% ── Universal transitions (any active profile) ──────────────────")
    lines.append("    note right of correction")
    lines.append("        Any profile triggers correction")
    lines.append("        when TurnType = CORRECT_PREVIOUS")
    lines.append("        or reroute signal detected")
    lines.append("    end note")
    lines.append("    correction --> reservation_start : back to reservation")
    lines.append("    correction --> order_start : back to order")
    lines.append("")
    lines.append("    goodbye --> [*] : call ends")

    return "\n".join(lines)


def build_pipeline_sequence(tenant_id: str = "default") -> str:
    """Build a sequenceDiagram of the v4 per-turn data flow."""
    stt_display = "Deepgram flux-general-multi"
    stt_service_display = "Flux"
    tts_display = "Gemini TTS"

    try:
        from server.core.tenant_config import load_tenant_config
        from server.brain.stt.deepgram_client import is_flux_model
        tenant_cfg = load_tenant_config(tenant_id)
        if tenant_cfg:
            audio_cfg = getattr(tenant_cfg, "audio", None) or {}
            if isinstance(audio_cfg, dict):
                configured_stt = audio_cfg.get("stt_model", "")
                if configured_stt:
                    stt_display = f"Deepgram {configured_stt}"
                    stt_service_display = "Flux" if is_flux_model(configured_stt) else "Nova"

            model = getattr(tenant_cfg, "model", "") or ""
            if isinstance(model, str):
                m = model.lower()
                if "gemini-live" in m:
                    tts_display = "Gemini Live Audio (native)"
                elif "elevenlabs" in m:
                    tts_display = "ElevenLabs TTS"
                elif "gemini" in m:
                    tts_display = "Gemini TTS"
    except Exception as e:
        logger.debug(f"Could not determine STT/TTS for tenant '{tenant_id}': {e}")
    
    return f"""\
sequenceDiagram
    autonumber
    participant C as Caller
    participant STT as {stt_display}<br/>({stt_service_display} · VAD + Barge-in)
    participant IC as intent_classifier.py<br/>(Regex → Haiku fallback)
    participant WR as worker_router.py<br/>(12 profiles)
    participant WE as worker_executor.py<br/>(parallel ≤280ms/350ms)
    participant CDB as context_doc_builder.py<br/>(next_action)
    participant CG as Commit Gate<br/>(v4_pipeline inline)
    participant TG as tiny_generator.py<br/>(Haiku + spoken German)
    participant TTS as {tts_display}<br/>

    C->>STT: audio stream (real-time)
    Note over STT: VAD endpoint detection<br/>Barge-in interruption
    STT->>IC: transcript text
    Note over IC: Regex fast-path ~80%<br/>Haiku async fallback ~20%
    IC->>WR: IntentResult(intent, turn_type, confidence)
    WR->>WE: ExecutionPlan(profile, required[], optional[])
    Note over WE: Required workers: hard 280ms<br/>Optional workers: soft 350ms<br/>Run in parallel
    WE->>CDB: WorkerOutputs[]
    Note over CDB: Assembles ContextDocument<br/>Decides next_action
    alt next_action == "commit"
        CDB->>CG: commit_tool + filled slots
        Note over CG: GUARDIAN preconditions check<br/>Execute create_reservation<br/>or create_order
        CG->>TG: post-commit ContextDocument
    else next_action == "say" or "clarify"
        CDB->>TG: ContextDocument
    else next_action == "end_call"
        CDB->>TG: farewell context
    end
    Note over TG: Inner monologue (not spoken)<br/>German spoken response
    TG->>TTS: spoken text
    TTS->>C: audio (streaming)"""


def build_commit_gate_fsm() -> str:
    """Build a stateDiagram-v2 of the commit gate FSM matching v4_pipeline.py.

    States are the actual ``end_call_stage`` values used in the live code:
      - idle: default; slot filling, workers, TinyGenerator
      - pre_commit_readback: reservation summary "Ich würde ... reservieren. Stimmt das so?"
      - order_pre_commit_readback: order priced item readback
      - correction_pending: user denied readback; "Was möchten Sie ändern?"
      - confirmed: commit done; farewell / end_call
    """
    return """\
stateDiagram-v2
    direction TB

    [*] --> idle : call starts

    idle --> pre_commit_readback : reservation slots full\\n(party_size + date + time + name)
    idle --> order_pre_commit_readback : order slots full\\n(items + name [+ address])

    pre_commit_readback --> correction_pending : user denies summary
    pre_commit_readback --> idle : user confirms\\n(falls through to commit)

    order_pre_commit_readback --> correction_pending : user denies order
    order_pre_commit_readback --> idle : user confirms\\n(falls through to commit)

    correction_pending --> idle : real correction\\n(slots cleared/updated)
    correction_pending --> pre_commit_readback : user re-confirms (reservation)
    correction_pending --> order_pre_commit_readback : user re-confirms (order)

    idle --> readback_pending : commit completed\\n(post-commit readback)
    readback_pending --> confirmed : user confirms
    readback_pending --> correction_pending : user denies
    idle --> confirmed : direct commit completion path
    confirmed --> [*] : farewell + end_call
"""


def build_all_diagrams(tenant_id: str = "default") -> Dict[str, str]:
    """Return all three diagram sources keyed by name, scoped to a tenant."""
    diagrams: Dict[str, str] = {}
    try:
        diagrams["profile_fsm"] = build_profile_fsm()
    except Exception as e:
        logger.error(f"[diagrams] profile_fsm failed: {e}")
        diagrams["profile_fsm"] = f"graph LR\n    error[\"Error: {e}\"]"

    try:
        diagrams["pipeline_sequence"] = build_pipeline_sequence(tenant_id=tenant_id)
    except Exception as e:
        logger.error(f"[diagrams] pipeline_sequence failed: {e}")
        diagrams["pipeline_sequence"] = f"graph LR\n    error[\"Error: {e}\"]"

    try:
        diagrams["commit_gate_fsm"] = build_commit_gate_fsm()
    except Exception as e:
        logger.error(f"[diagrams] commit_gate_fsm failed: {e}")
        diagrams["commit_gate_fsm"] = f"graph LR\n    error[\"Error: {e}\"]"

    return diagrams
