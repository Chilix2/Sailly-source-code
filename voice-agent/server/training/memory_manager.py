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
from typing import List, Optional

from server.training.conversation_state import ConversationState

logger = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, max_recent_turns: int = 5, max_summary_words: int = 80):
        self.recent_turns: List[dict] = []
        self.context_summary: str = ""
        self.max_recent_turns = max_recent_turns
        self.max_summary_words = max_summary_words

    def build_context(
        self,
        node_prompt: str,
        state: ConversationState,
        prereq_results: Optional[List[str]] = None,
    ) -> str:
        """Build memory-efficient context string for Gemini, including injected context."""
        parts = [node_prompt]

        state_info = self._format_state(state)
        if state_info:
            parts.append(f"\nBekannte Daten: {state_info}")

        if self.context_summary:
            parts.append(f"\nBisheriger Verlauf: {self.context_summary}")

        # Include any injected context (marked with "injected" flag)
        injected_items = [turn for turn in self.recent_turns if turn.get("injected")]
        if injected_items:
            injected_lines = []
            for turn in injected_items:
                if turn.get("bot"):
                    injected_lines.append(f"[SYSTEM] {turn['bot']}")
                elif turn.get("customer"):
                    injected_lines.append(f"[INFO] {turn['customer']}")
            
            if injected_lines:
                parts.append(f"\nInjizierte Kontextinformationen:\n" + "\n".join(injected_lines))

        if prereq_results:
            parts.append(f"\nErgebnis: {' '.join(prereq_results)}")

        return "\n".join(parts)

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
        """Compress an old turn into a summary sentence."""
        node = old_turn["node"]
        customer = old_turn["customer"][:50]
        self.context_summary += f" [{node}] Kunde: '{customer}...'"

        words = self.context_summary.split()
        if len(words) > self.max_summary_words:
            self.context_summary = " ".join(words[-self.max_summary_words:])

    @staticmethod
    def _format_state(state: ConversationState) -> str:
        """Format known state data for the LLM's context."""
        parts = []
        if state.selected_dish:
            parts.append(f"Gericht: {state.selected_dish}")
        if state.phone_number:
            parts.append(f"Telefon: {state.phone_number}")
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
        return ", ".join(parts) if parts else ""
