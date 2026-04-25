"""
Memory manager for Gemini Live API constraints.

Gemini Live API:
- 128k token context window
- Audio burns 25 tokens/sec (15 min call = 22,500 tokens)
- Each node prompt: ~100-200 tokens

Strategy: keep total non-audio context under 2,000 tokens per turn.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from server.brain.conversation_state import ConversationState

logger = logging.getLogger(__name__)

# ── Phase 4 — PromptSlot enum (8 layers) ─────────────────────────────────────


class PromptSlot(str, Enum):
    """
    The 8 ordered layers assembled into the LLM prompt each turn.
    Rendering order: L1 → L8 (L1 is anchored first, L8 is history).
    """
    NODE_PROMPT      = "l1_node_prompt"       # node-owned system instruction
    LAST_UTTERANCE   = "l2_last_utterance"    # caller's verbatim utterance
    EXTRACTOR_STATUS = "l3_extractor_status"  # degraded-mode warning if extractor lagged
    VALIDATION       = "l4_validation"        # VERIFIED + PENDING slot indicators
    ANTI_REPETITION  = "l5_anti_repetition"   # last-4 bot responses to avoid
    SLOT_CONTEXT     = "l6_slot_context"      # known / validated / missing structure
    MULTI_INTENT     = "l7_multi_intent"      # current intent focus + queued summary
    HISTORY          = "l8_history"           # 5 verbatim turns + 300-word older summary


# ── Token budget constants ─────────────────────────────────────────────────────
WARN_TOKEN_BUDGET    = 3_000   # log warning above this
TRIM_TOKEN_BUDGET    = 5_000   # drop oldest history turns above this
RECENT_TURNS         = 5       # verbatim turns to keep in L8
SUMMARY_WORD_BUDGET  = 300     # max words in the older-turns summary
ANTI_REPETITION_DEPTH = 4      # last N bot responses injected in L5


def estimate_tokens(text_or_layers) -> int:
    """
    Cheap token estimate: 1 token ≈ 4 chars (GPT/Gemini average).

    Accepts either a plain string or a dict[PromptSlot, str].
    """
    if isinstance(text_or_layers, dict):
        total = sum(len(v) for v in text_or_layers.values())
    else:
        total = len(str(text_or_layers))
    return total // 4


def trim_to_budget(
    layers: Dict[PromptSlot, str],
    recent_turns_store: List[dict],
    context_summary: str,
) -> Dict[PromptSlot, str]:
    """
    If assembled prompt exceeds TRIM_TOKEN_BUDGET, drop the oldest verbatim
    history turns from L8 one at a time until under budget.
    All other layers are preserved.  Mutates `layers[HISTORY]` in place.
    """
    while estimate_tokens(layers) > TRIM_TOKEN_BUDGET:
        history = layers.get(PromptSlot.HISTORY, "")
        if not history:
            logger.warning("[MemoryManager] trim_to_budget: history empty but still over budget")
            break
        # History is formatted as "\n---\n"-separated turn blocks
        turns = history.split("\n---\n")
        if len(turns) > 1:
            layers[PromptSlot.HISTORY] = "\n---\n".join(turns[1:])
        else:
            logger.warning("[MemoryManager] trim_to_budget: cannot trim further — single turn block")
            break
    return layers


class MemoryManager:
    def __init__(self, max_recent_turns: int = 5, max_summary_words: int = 300):
        self.recent_turns: List[dict] = []
        self.context_summary: str = ""
        self.max_recent_turns = max_recent_turns
        self.max_summary_words = max_summary_words

    # ── Phase 4 Layer renderers (L1–L8) ───────────────────────────────────────

    @staticmethod
    def render_l1_node_prompt(node_prompt: str) -> str:
        """
        L1 — Node prompt. Always first (per layer-1-node-prompt: l1-first-always).
        The node owns its own prompt (3–8 lines focused instruction).
        """
        return node_prompt.strip()

    @staticmethod
    def render_l2_last_utterance(state: ConversationState) -> str:
        """
        L2 — Caller's last utterance with explicit German header
        (per layer-2-last-utterance: l2-explicit-header).
        """
        last_utt = getattr(state, "last_user_utterance", "") or ""
        last_utt = last_utt.strip()
        if not last_utt:
            return ""
        return (
            "DAS SAGT DER ANRUFER GERADE:\n"
            f"«{last_utt}»\n"
            "\nWICHTIG: Wenn der Anrufer hier etwas erwähnt hat, das NICHT in "
            "den BEKANNTEN DATEN erscheint, prüfe die gecachten Menüdaten direkt, "
            "bevor du das Produkt ablehnst. Bei Produktfragen ('habt ihr X?') "
            "immer aus dem gecachten Menü antworten — niemals ablehnen ohne zu prüfen."
        )

    @staticmethod
    def render_l3_extractor_status(state: ConversationState) -> str:
        """
        L3 — Extractor status (per layer-3-extractor-status: l3-explicit-degraded).
        Emits actionable warning only when extractor lagged or failed.
        Also surfaces validation-registry failures per Sprint 2.4 Rule 2.
        """
        parts = []

        _status = getattr(state, "_slot_extractor_status", None)
        _timed_out = getattr(state, "last_extraction_timed_out", False)
        if _status in ("timeout", "429", "error") or _timed_out:
            _reason = "timed_out" if _timed_out else _status
            parts.append(
                "EXTRAKTOR HINWEIS: Die automatische Slot-Erkennung ist im "
                f"vorherigen Turn ausgefallen ({_reason}). Frage bei Unsicherheit "
                "nochmal nach — spekuliere nicht. Arbeite direkt mit der LETZTEN "
                "AUSSAGE und dem gecachten Menü."
            )

        registry_ref = getattr(state, "validation_registry_ref", None)
        if registry_ref is not None:
            try:
                if hasattr(registry_ref, "failed_slot_names"):
                    _failed = registry_ref.failed_slot_names()
                    if _failed:
                        parts.append(
                            f"EXTRAKTOR HINWEIS: Hintergrund-Validierung für "
                            f"{', '.join(_failed)} fehlgeschlagen. Erfrage "
                            "diese Werte explizit vom Anrufer zur Bestätigung."
                        )
            except Exception:
                pass

        return "\n\n".join(parts)

    # Phase 5.5 — German display labels for slot names (per status-labels decision)
    _SLOT_LABEL_DE: dict = {
        "phone": "Telefon",
        "address": "Adresse",
        "name": "Name",
        "party_size": "Personenzahl",
        "items": "Bestellung",
        "pickup_time": "Abholzeit",
        "reservation_date": "Reservierungsdatum",
        "reservation_time": "Reservierungszeit",
    }

    _STATUS_LABEL_DE: dict = {
        "verified": "verifiziert",
        "pending": "wird geprüft",
        "stale": "muss neu geprüft werden",
        "unvalidated": "ungeprüft",
        # "failed" and "error" are hidden per l4-verified-and-pending decision
    }

    @staticmethod
    def render_l4_validation(state: ConversationState) -> str:
        """
        L4 — Validation indicators (per layer-4-validation-indicators: l4-verified-and-pending).

        Phase 5.5: Uses new ValidationRegistry.snapshot_for_prompt() with German
        status labels. Shows VERIFIED, PENDING, STALE, UNVALIDATED.
        Hides FAILED and ERROR — bot response handles those, not the prompt.

        Falls back to the legacy validation_registry_ref API if the new registry
        is not yet attached (backward compatible for Phase 5 live calls).
        """
        # Try new Phase 5.5 registry first
        new_registry = getattr(state, "_validation_registry", None)
        if new_registry is not None:
            try:
                snapshot = new_registry.snapshot_for_prompt()
            except Exception:
                snapshot = {}

            rows = []
            for slot_path, info in snapshot.items():
                status = info.get("status", "")
                if status in {"failed", "error"}:
                    continue
                slot_name = slot_path.split(".")[-1]
                slot_label = MemoryManager._SLOT_LABEL_DE.get(slot_name, slot_name)
                status_label = MemoryManager._STATUS_LABEL_DE.get(status, status)
                rows.append(f"  - {slot_label}: {status_label}")

            if rows:
                return "VALIDIERUNGSSTATUS:\n" + "\n".join(rows)

        # Legacy fallback: old registry with verified_slot_names / pending_slot_names
        registry_ref = getattr(state, "validation_registry_ref", None)
        if registry_ref is None:
            return ""

        lines = []
        try:
            if hasattr(registry_ref, "verified_slot_names"):
                for name in registry_ref.verified_slot_names():
                    lines.append(f"  {name}: verifiziert ✓")
            if hasattr(registry_ref, "pending_slot_names"):
                for name in registry_ref.pending_slot_names():
                    lines.append(f"  {name}: wird geprüft …")
        except Exception:
            return ""

        if not lines:
            return ""
        return "VALIDIERTE DATEN:\n" + "\n".join(lines)

    def render_l5_anti_repetition(self) -> str:
        """
        L5 — Anti-repetition guard (per layer-5-anti-repetition: l5-last-4).
        Lists last ANTI_REPETITION_DEPTH bot responses with instruction to vary phrasing.
        Combined with post-LLM rotator (response_variations.py) per memory-anti-repetition:
        prompt-and-rotator.
        """
        recent_bot = [
            t["bot"]
            for t in self.recent_turns[-ANTI_REPETITION_DEPTH:]
            if t.get("bot") and not t.get("injected")
        ]
        if not recent_bot:
            return ""
        return (
            "WIEDERHOLUNG VERMEIDEN — du hast diese Formulierungen kürzlich verwendet, "
            "wähle alternative Phrasierungen:\n"
            + "\n".join(f"  - «{r[:120]}»" for r in recent_bot)
        )

    @staticmethod
    def render_l6_slot_context(state: ConversationState) -> str:
        """
        L6 — Three-layer slot context (per layer-6-slot-context: l6-keep-three-layer).
        Known (filled) / Validated / Missing — explicit structure.
        Works for CapturedIntent path (Phase 2+) and legacy OrderSlots path.
        """
        ci_list = getattr(state, "captured_intents", [])
        ci_idx = getattr(state, "current_intent_idx", None)

        if ci_list and ci_idx is not None and ci_idx < len(ci_list):
            # ── Phase 2+ CapturedIntent path ─────────────────────────────────
            current = ci_list[ci_idx]
            known: List[str] = []
            validated: List[str] = []
            missing: List[str] = []

            try:
                from server.brain.captured_intents import SlotStatus, REQUIRED_SLOTS, IntentKind
                required = REQUIRED_SLOTS.get(IntentKind(current.kind.value if hasattr(current.kind, 'value') else current.kind), set())
            except Exception:
                required = set()

            filled_names: set = set()
            for slot_name, sv in (current.slots or {}).items():
                if hasattr(sv, "status"):
                    try:
                        from server.brain.captured_intents import SlotStatus
                        if sv.status in (SlotStatus.FILLED, SlotStatus.CONFIRMED):
                            confirm_mark = " ✓" if sv.status == SlotStatus.CONFIRMED else ""
                            known.append(f"  {slot_name}: {sv.value}{confirm_mark}")
                            filled_names.add(slot_name)
                            if getattr(sv, "validated", False):
                                validated.append(f"  {slot_name}: verifiziert ✓")
                    except Exception:
                        pass

            # Shared slots (name, phone — inherited by all intents)
            for slot_name, sv in getattr(state, "shared_slots", {}).items():
                if hasattr(sv, "status"):
                    try:
                        from server.brain.captured_intents import SlotStatus
                        if sv.status in (SlotStatus.FILLED, SlotStatus.CONFIRMED):
                            confirm_mark = " ✓" if sv.status == SlotStatus.CONFIRMED else ""
                            known.append(f"  {slot_name} (geteilt): {sv.value}{confirm_mark}")
                            filled_names.add(slot_name)
                    except Exception:
                        pass

            for req in required:
                if req not in filled_names:
                    missing.append(f"  {req}")

            intent_label = getattr(current, "label_de", str(getattr(current, "kind", "?")))
            sections = [f"=== BEKANNTE DATEN — {intent_label.upper()} (NICHT ERNEUT ERFRAGEN) ==="]
            sections.extend(known or ["  (noch keine Daten erfasst)"])

            if validated:
                sections.append("\n=== VERIFIZIERT ===")
                sections.extend(validated)

            if missing:
                sections.append("\n=== NOCH FEHLEND ===")
                sections.extend(missing)

            return "\n".join(sections)

        else:
            # ── Legacy OrderSlots path ─────────────────────────────────────────
            slots = getattr(state, "order_slots_ref", None)
            if slots is None:
                state_info = MemoryManager._format_state(state)
                if state_info:
                    return f"Bekannte Daten: {state_info}"
                return ""

            known_text = slots.known_summary_de()
            missing_text = slots.missing_summary_de()
            registry_ref = getattr(state, "validation_registry_ref", None)

            lines = [
                "=== BEKANNTE DATEN (NICHT ERNEUT ERFRAGEN) ===",
                known_text,
            ]
            if registry_ref is not None:
                lines += ["\n=== VALIDIERUNGSSTATUS ===", registry_ref.summary_for_prompt_de()]
            lines += ["\n=== NOCH FEHLEND ===", missing_text]
            next_step = MemoryManager._compose_next_step_instruction(slots, registry_ref, state)
            lines += ["\n=== NÄCHSTER SCHRITT ===", next_step]

            # Hard warnings for pending/failed
            if registry_ref is not None:
                pending = registry_ref.pending_slot_names()
                failed = registry_ref.failed_slot_names()
                if pending:
                    lines.append(
                        f"\nHINWEIS: {', '.join(pending)} werden noch geprüft. "
                        "NICHT erneut erfragen."
                    )
                if failed:
                    lines.append(
                        f"\nWICHTIG: {', '.join(failed)} konnte nicht automatisch "
                        "validiert werden. Bitte frage den Anrufer höflich nach Bestätigung."
                    )

            return "\n".join(lines)

    @staticmethod
    def render_l7_multi_intent(state: ConversationState) -> str:
        """
        L7 — Multi-intent readback (per layer-7-multi-intent-readback: l7-current-active-focus).
        Emphasizes the current intent; summarizes queued ones briefly.
        Returns empty string for single-intent calls.
        """
        ci_list = getattr(state, "captured_intents", [])
        ci_idx = getattr(state, "current_intent_idx", None)

        if not ci_list or len(ci_list) <= 1 or ci_idx is None:
            return ""

        if ci_idx >= len(ci_list):
            return ""

        current = ci_list[ci_idx]
        cur_label = getattr(current, "label_de", str(getattr(current, "kind", "?")))
        cur_status = getattr(current, "status", "?")
        if hasattr(cur_status, "value"):
            cur_status = cur_status.value

        cur_lines = [f"AKTUELLES ANLIEGEN: {cur_label} (Status: {cur_status})"]
        for slot_name, sv in (current.slots or {}).items():
            if hasattr(sv, "value") and sv.value:
                cur_lines.append(f"  ✓ {slot_name}: {sv.value}")

        total = len(ci_list)
        queued_lines = [f"WEITERE ANLIEGEN ({total - 1} warten):"]
        for i, q in enumerate(ci_list):
            if i == ci_idx:
                continue
            q_label = getattr(q, "label_de", str(getattr(q, "kind", "?")))
            slot_names = [n for n, sv in (q.slots or {}).items() if hasattr(sv, "value") and sv.value]
            slot_summary = ", ".join(slot_names) or "(keine Daten)"
            queued_lines.append(f"  - {q_label}: {slot_summary}")

        return "\n".join(cur_lines) + "\n\n" + "\n".join(queued_lines)

    def render_l8_history(self) -> str:
        """
        L8 — Compressed history (per layer-8-history: l8-5-turns-300-words).
        Last RECENT_TURNS verbatim + older-turns summary (≤ SUMMARY_WORD_BUDGET words).
        """
        regular_turns = [t for t in self.recent_turns if not t.get("injected")]
        injected_turns = [t for t in self.recent_turns if t.get("injected")]

        out: List[str] = []

        if self.context_summary:
            out.append(
                f"FRÜHERE GESPRÄCHSPHASE (Zusammenfassung):\n{self.context_summary}"
            )

        if injected_turns:
            injected_lines = []
            for turn in injected_turns:
                if turn.get("bot"):
                    injected_lines.append(f"[SYSTEM] {turn['bot']}")
                elif turn.get("customer"):
                    injected_lines.append(f"[INFO] {turn['customer']}")
            if injected_lines:
                out.append("INJIZIERTE INFORMATIONEN:\n" + "\n".join(injected_lines))

        if regular_turns:
            out.append("LETZTE TURNS:")
            for t in regular_turns:
                customer = t.get("customer") or ""
                bot = t.get("bot") or ""
                out.append(f"  Anrufer: {customer}")
                out.append(f"  Sailly:  {bot}")
                out.append("---")

        return "\n".join(out)

    def build_context(
        self,
        node_prompt: str,
        state: ConversationState,
        prereq_results: Optional[List[str]] = None,
    ) -> str:
        """
        Build memory-efficient context string for Gemini using 8 ordered PromptSlots.

        Layer order: L1 (node prompt) → L2 (utterance) → L3 (extractor status) →
        L4 (validation) → L5 (anti-repetition) → L6 (slot context) →
        L7 (multi-intent) → L8 (history).  Budget trimming applied after assembly.
        """
        # ── Render all 8 layers ───────────────────────────────────────────────
        l1 = self.render_l1_node_prompt(node_prompt)
        l2 = self.render_l2_last_utterance(state)
        l3 = self.render_l3_extractor_status(state)
        l4 = self.render_l4_validation(state)
        l5 = self.render_l5_anti_repetition()
        l6 = self.render_l6_slot_context(state)
        l7 = self.render_l7_multi_intent(state)
        l8 = self.render_l8_history()

        # ── Lunch-menu metadata (appended to L6) ──────────────────────────────
        menu_metadata = getattr(state, "cached_menu_metadata", {}) or {}
        if menu_metadata:
            if menu_metadata.get("lunch_menu_available"):
                l6 += (
                    "\n\n=== MITTAGSANGEBOT VERFÜGBAR ===\n"
                    f"Aktuelle Zeit (CEST): {menu_metadata.get('current_time_cest', 'unbekannt')}\n"
                    "Mittagsangebot und Mittagsmenüs sind jetzt verfügbar (11:30–14:00, Mo–Fr)."
                )
            else:
                l6 += (
                    "\n\n=== MITTAGSANGEBOT NICHT VERFÜGBAR ===\n"
                    f"Aktuelle Zeit (CEST): {menu_metadata.get('current_time_cest', 'unbekannt')}\n"
                    "Mittagsangebot und Mittagsmenüs sind NICHT verfügbar. Biete NUR die Abendkarte an."
                )

        # ── PR-16b: Sticky menu injection ────────────────────────────────────
        # get_menu fires once in T0/T1. Its result is cached in state.cached_menu
        # but the actual item data is NOT visible in subsequent turn contexts —
        # build_history() only includes the [TOOL:get_menu] tag in the bot turn,
        # not the tool's return value. This means from T2 onward the LLM has no
        # data to answer "habt ihr X?" correctly, causing incorrect denials.
        # Fix: re-inject the cached menu as a named section in L6 on every turn
        # so the LLM can always look up items regardless of conversation length.
        _cached_menu = getattr(state, "cached_menu", None)
        if _cached_menu and isinstance(_cached_menu, dict):
            _menu_lines = ["=== GECACHTE SPEISEKARTE (aus get_menu) ==="]
            _menu_lines.append("Nutze diese Daten für ALLE Produkt- und Preisfragen:")
            for _cat, _items in _cached_menu.items():
                if isinstance(_items, list):
                    _menu_lines.append(f"\n{_cat}:")
                    for _item in _items:
                        if isinstance(_item, dict):
                            _name = _item.get("name", "?")
                            _price = _item.get("price", "")
                            _desc = _item.get("description", "")
                            _line = f"  - {_name}"
                            if _price:
                                _line += f" — {_price}"
                            if _desc:
                                _line += f" ({_desc[:60]})"
                            _menu_lines.append(_line)
                        elif isinstance(_item, str):
                            _menu_lines.append(f"  - {_item}")
            l6 += "\n\n" + "\n".join(_menu_lines)

        # ── Prereq tool results (appended to L1) ─────────────────────────────
        if prereq_results:
            l1 += "\n\nErgebnis: " + " ".join(prereq_results)

        layers: Dict[PromptSlot, str] = {
            PromptSlot.NODE_PROMPT:      l1,
            PromptSlot.LAST_UTTERANCE:   l2,
            PromptSlot.EXTRACTOR_STATUS: l3,
            PromptSlot.VALIDATION:       l4,
            PromptSlot.ANTI_REPETITION:  l5,
            PromptSlot.SLOT_CONTEXT:     l6,
            PromptSlot.MULTI_INTENT:     l7,
            PromptSlot.HISTORY:          l8,
        }

        # ── Token budget & trim ───────────────────────────────────────────────
        est_tokens = estimate_tokens(layers)
        if est_tokens > TRIM_TOKEN_BUDGET:
            logger.warning(
                "[MemoryManager] prompt is HUGE (%d est. tokens) — trimming history.",
                est_tokens,
            )
            layers = trim_to_budget(layers, self.recent_turns, self.context_summary)
            est_tokens = estimate_tokens(layers)
        elif est_tokens > WARN_TOKEN_BUDGET:
            logger.warning(
                "[MemoryManager] prompt >%d est. tokens (%d). Consider trimming.",
                WARN_TOKEN_BUDGET,
                est_tokens,
            )

        # ── Assemble: emit non-empty layers in order, separated by blank lines ─
        ordered_keys = [
            PromptSlot.NODE_PROMPT,
            PromptSlot.LAST_UTTERANCE,
            PromptSlot.EXTRACTOR_STATUS,
            PromptSlot.VALIDATION,
            PromptSlot.ANTI_REPETITION,
            PromptSlot.SLOT_CONTEXT,
            PromptSlot.MULTI_INTENT,
            PromptSlot.HISTORY,
        ]
        assembled_parts = [layers[k] for k in ordered_keys if layers.get(k, "").strip()]
        built = "\n\n".join(assembled_parts)

        return built, est_tokens

    def build_history(self) -> List[dict]:
        """Return recent turns formatted for Gemini's contents array."""
        history = []
        for turn in self.recent_turns:
            history.append({"role": "user", "content": turn["customer"]})
            history.append({"role": "model", "content": turn["bot"]})
        return history

    def record_turn(self, customer: str, bot: str, node_name: str):
        """Record a turn and compress old ones."""
        self.recent_turns.append({
            "customer": customer,
            "bot": bot,
            "node": node_name,
        })
        while len(self.recent_turns) > self.max_recent_turns:
            old = self.recent_turns.pop(0)
            self._compress(old)

    def inject_context(self, role: str, message: str):
        """Inject a synthetic message into conversation history.
        
        Used for CRM context, availability, item status, special instructions.
        The message appears in LLM context but is NOT spoken to caller.
        
        Args:
            role: "user" or "agent"
            message: Text to inject (max 500 chars)
        """
        if len(message) > 500:
            message = message[:497] + "..."
        
        # Add to recent_turns with a marker
        self.recent_turns.append({
            "customer": message if role == "user" else None,
            "bot": message if role == "agent" else None,
            "node": "[INJECTED_CONTEXT]",
            "injected": True,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # If we exceed max_recent_turns, compress oldest into summary
        if len(self.recent_turns) > self.max_recent_turns:
            self._compress(self.recent_turns.pop(0))
        
        logger.info(f"[INJECT] {role}: {message[:50]}...")

    def _compress(self, old_turn: dict):
        """Compress an old turn into a summary sentence.
        1000 chars: generous headroom for data-rich T0 utterances (name + dishes +
        address + phone in one sentence is ~200-250 chars; 1000 covers the worst case).
        """
        node = old_turn["node"]
        customer = (old_turn.get("customer") or "")[:1000]  # was [:50]
        self.context_summary += f" [{node}] Kunde: '{customer}...'"

        words = self.context_summary.split()
        if len(words) > self.max_summary_words:
            self.context_summary = " ".join(words[-self.max_summary_words:])

    @staticmethod
    def _compose_next_step_instruction(slots, registry, state) -> str:
        """
        Turn the current slot + validation + confirmation state into a single
        explicit sentence that the LLM follows for this turn.

        Priority order (highest first):
          1. Failed validation → ask caller to re-confirm
          2. Missing required slot → ask for it (one field per turn)
          3. Address unconfirmed → read back address, ask "Korrekt?"
          4. Phone unconfirmed → read back phone NATO-style, ask "Richtig?"
          5. Order summary unconfirmed → batch confirmation of items/name/delivery
          6. All confirmed → fire create_order
        """
        # Priority 1: Failed validations need caller action
        if registry is not None and registry.has_any_failed():
            failed = registry.failed_slot_names()
            if failed:
                return (
                    f"Erkläre dem Anrufer, dass {', '.join(failed)} nicht automatisch "
                    "bestätigt werden konnte. Bitte um erneute Angabe."
                )

        # Priority 2: Any required slot still missing → ask for it
        # Bridge: if slots don't have items yet but legacy state does (extractor lag),
        # synthesize an items slot entry so the bot can do the dish summary now.
        if slots is not None:
            _missing = slots.missing_required()
            if "items" in _missing:
                _legacy_dish = getattr(state, "selected_dish", None)
                _legacy_extras = getattr(state, "order_items_extras", []) or []
                if _legacy_dish:
                    _all_items = [_legacy_dish] + [e for e in _legacy_extras if e and e != _legacy_dish]
                    slots.items.value = ", ".join(_all_items)
                    try:
                        from server.brain.captured_intents import SlotStatus
                    except ImportError:
                        from server.brain.order_slots import SlotStatus
                    slots.items.status = SlotStatus.FILLED
                    slots.items.confidence = "medium"
                    logger.debug(f"[MemMgr] bridged legacy items→slot: {slots.items.value!r}")

        # Sprint 1.5: filter out slots the caller has explicitly confirmed
        # so the NÄCHSTER SCHRITT block doesn't re-ask a confirmed slot
        # (fixes demo-6cf65e58003d name-loop at T3/T4/T5).
        def _is_confirmed(slot_name: str) -> bool:
            if slot_name == "name" and getattr(state, "name_confirmed", False):
                return True
            if slot_name == "items" and getattr(state, "items_confirmed", False):
                return True
            if slot_name == "delivery_type" and getattr(state, "delivery_type_confirmed", False):
                return True
            if slot_name.startswith("address_") and getattr(state, "address_confirmed", False):
                return True
            if slot_name == "phone" and getattr(state, "phone_confirmed", False):
                return True
            return False

        missing = [s for s in slots.missing_required() if not _is_confirmed(s)]
        if missing:
            next_slot = missing[0]
            # Sprint 2.5: phone retry mode — use slower, explicit instruction
            # when phone_attempts >= 3. Fixes demo-6cf65e58003d cascade where
            # phone collection failures auto-escalated into confused prompt.
            if next_slot == "phone" and getattr(state, "phone_retry_mode", False):
                return (
                    "FRAGE ALS NÄCHSTES NUR NACH: phone\n"
                    "HINWEIS: Die Telefonnummer war mehrfach unklar. Bitte den "
                    "Anrufer, die Nummer LANGSAM und in EINER Ziffergruppe zu "
                    "nennen (z.B. 'null eins fünf zwei – drei vier fünf sechs – "
                    "sieben acht neun null'). Wiederhole jede Ziffer sofort nach "
                    "dem Hören, damit der Anrufer bei Bedarf korrigieren kann.\n"
                    'Beispiel: "Entschuldigen Sie, die Verbindung war schwierig. '
                    'Könnten Sie Ihre Telefonnummer bitte LANGSAM und Ziffer für '
                    'Ziffer nennen?"'
                )
            # Special case: phone from caller-ID only needs confirmation, not fresh input
            if next_slot == "phone" and slots.is_phone_from_caller_id():
                phone_val = slots.phone.value or ""
                return (
                    f"FRAGE ALS NÄCHSTES NUR NACH: phone\n"
                    f"HINWEIS: Telefonnummer ist bereits vorbefüllt von der Anrufer-Caller-ID ({phone_val}).\n"
                    f"Bitte den Anrufer, diese Nummer für den Zahlungslink zu BESTÄTIGEN — nicht neu zu nennen.\n"
                    f'Beispiel: "Ich sehe, Sie rufen gerade von {phone_val} an — darf ich den '
                    f"Zahlungslink an genau diese Nummer schicken?\"\n"
                    "Bei JA: Nummer übernehmen. Bei NEIN: Nach alternativer Handynummer fragen."
                )
            _slot_labels = {
                "name": "Name",
                "phone": "Telefonnummer",
                "delivery_type": "Lieferung oder Abholung",
                "items": "Bestellung",
                "address_street": "Straße",
                "address_number": "Hausnummer",
                "address_city": "Ort",
                "party_size": "Personenzahl",
                "reservation_date": "Datum",
                "reservation_time": "Uhrzeit",
            }
            label = _slot_labels.get(next_slot, next_slot)
            return f"Frage genau nach: {label}. Nur diese eine Sache pro Turn."

        # Priority 3: Address unconfirmed (delivery only)
        delivery_is_delivery = (
            slots.delivery_type.is_usable() and slots.delivery_type.value == "delivery"
        )
        address_known = slots.address_street.is_usable()
        addr_confirmed = getattr(state, "address_confirmed", False)
        if delivery_is_delivery and address_known and not addr_confirmed:
            # Build display address from slots
            addr_parts = [slots.address_street.value]
            if slots.address_number.is_usable():
                addr_parts.append(slots.address_number.value)
            if slots.address_city.is_usable():
                addr_parts.append(slots.address_city.value)
            addr_str = " ".join(addr_parts)
            # Optionally wait briefly if validation is still pending
            if registry is not None and registry.is_pending("address"):
                return (
                    "Sage dem Anrufer: 'Einen Moment, ich prüfe die Adresse kurz.' "
                    "Dann warte auf nächste Äußerung."
                )
            return (
                f"Alle Pflichtdaten vorhanden. Lies die Adresse zur Bestätigung zurück: "
                f"'{addr_str}'. Frage 'Korrekt?'."
            )

        # Priority 4: Phone unconfirmed
        phone_known = slots.phone.is_usable()
        phone_confirmed = getattr(state, "phone_confirmed", False)
        if phone_known and not phone_confirmed:
            phone_val = slots.phone.value or ""
            # Format NATO-style: chunk into pairs/triples
            _grouped = " — ".join(
                phone_val[i:i+3] for i in range(0, len(phone_val), 3)
            ) if phone_val else ""
            return (
                f"Adresse bestätigt. Lies die Telefonnummer zur Bestätigung zurück "
                f"— in Zifferngruppen, deutlich: '{_grouped}'. Frage 'Richtig?'."
            )

        # Priority 5: Order summary unconfirmed
        order_summary_confirmed = getattr(state, "order_summary_confirmed", False)
        if not order_summary_confirmed and slots.items.is_usable():
            return (
                "Adresse und Telefonnummer bestätigt. Fasse die restliche Bestellung "
                "(Name, Art, Gerichte) in EINEM Satz zusammen und frage 'Alles korrekt?'."
            )

        # Priority 6: All confirmed → commit
        return "Alles bestätigt. Rufe [TOOL:create_order] auf."

    @staticmethod
    def _format_state(state: ConversationState) -> str:
        """Format known state data for the LLM's context."""
        parts = []
        if state.selected_dish:
            try:
                from server.brain.conversation_state import get_cached_dish_price
                # FIX 2: Use current intent items in multi-intent mode, fall back to cart in single-intent
                cart = state.current_intent_items()  # routes through captured_intents or falls back
                lines = []
                subtotal = 0.0
                for item in cart:
                    p = get_cached_dish_price(state, item)
                    if p:
                        lines.append(f"{item} {p:.2f} Euro")
                        subtotal += p
                    else:
                        lines.append(item)
                if lines:
                    parts.append("Warenkorb: " + ", ".join(lines))
                if subtotal > 0:
                    _is_delivery = state.delivery_address_mentioned or bool(getattr(state, "delivery_address", ""))
                    _surcharge = 5.0 if (_is_delivery and subtotal < 20.0) else 0.0
                    _total = subtotal + _surcharge
                    parts.append(f"Zwischensumme: {subtotal:.2f} Euro")
                    if _surcharge > 0:
                        parts.append(f"Lieferpauschale: {_surcharge:.2f} Euro (unter 20 Euro Mindestwert)")
                    parts.append(f"Gesamtpreis: {_total:.2f} Euro")
            except Exception:
                parts.append(f"Gericht: {state.selected_dish}")
        # Name surfacing: full name preferred; fall back to first name only.
        # LLM uses "Vorname: X" to know it should ask for last name personally.
        _cname = getattr(state, "customer_name", None)
        _fname = getattr(state, "first_name", None)
        if _cname:
            parts.append(f"Name: {_cname}")
        elif _fname:
            parts.append(f"Vorname: {_fname}")
        if state.delivery_intended is True:
            if getattr(state, "delivery_address", None):
                parts.append(f"Lieferadresse: {state.delivery_address}")
        elif state.delivery_intended is False:
            parts.append("Abholung: ja")
        if state.phone_number:
            parts.append(f"Telefon: {state.phone_number}")
        # Sprint 0 — caller-ID prefill surfaces here so the LLM can propose it
        # to the caller and ask for confirmation before we use it as the SMS
        # destination. We explicitly tag the state (bestätigt/unbestätigt) so
        # the model doesn't quietly reuse an unverified number.
        _cid = getattr(state, "caller_id_phone", None)
        if _cid and not state.phone_number:
            _cid_state = "bestätigt" if getattr(state, "caller_id_confirmed", False) else "unbestätigt"
            parts.append(f"Anrufernummer_Caller_ID: {_cid} ({_cid_state})")
        if state.party_size:
            parts.append(f"Personen: {state.party_size}")
        if state.reservation_date:
            parts.append(f"Datum: {state.reservation_date}")
        if state.reservation_time:
            parts.append(f"Uhrzeit: {state.reservation_time}")
        if state.order_created:
            parts.append("Bestellung: aufgegeben")
        if state.reservation_created:
            parts.append("Reservierung: bestätigt")
        # Rush-path signal: all order fields present → LLM can jump straight to summary.
        try:
            if state.order_intent and not state.order_created and state.has_all_order_fields():
                parts.append("ALLE_FELDER_VORHANDEN: ja")
        except Exception:
            pass
        return ", ".join(parts) if parts else ""
