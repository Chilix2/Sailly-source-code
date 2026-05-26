"""
src/persona.py — Claude Haiku caller persona (German restaurant caller simulator)

Uses Anthropic Claude Haiku 4.5 for deterministic JSON responses.
Falls back gracefully to simple scripted responses if API is unavailable.
"""
import json
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PersonaResponse:
    speech: str
    end_politely: bool = False
    abandon: bool = False
    internal_note: str = ""


class CallerPersona:
    """LLM-driven caller persona using Anthropic Claude Haiku."""

    def __init__(self, api_key: str, system_prompt_path: str):
        """Initialize with Anthropic API key and system prompt file."""
        # Accept both OPENAI and ANTHROPIC keys — we use Anthropic now
        self._anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip() or api_key

        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self._anthropic_key)
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        self.system_prompt_base = self._load_system_prompt(system_prompt_path)
        self.turn_count = 0

    @staticmethod
    def _load_system_prompt(path: str) -> str:
        """Load the system prompt from file."""
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning(f"System prompt file not found: {path}")
            return ""

    def build_system_prompt(
        self,
        scenario_goal: str,
        caller_identity: dict,
        confirmation_phrases: list[str],
        patience_turns: int,
    ) -> str:
        """Build full system prompt for this scenario."""
        identity_str = self._format_identity(caller_identity)
        confirmation_str = ", ".join(confirmation_phrases[:5])

        scenario_block = f"""
SCENARIO GOAL (this call only):
{scenario_goal}

CALLER IDENTITY (only reveal if asked):
{identity_str}

CONFIRMATION PHRASES (use when confirming):
{confirmation_str}

TURN BUDGET:
- You have approximately {patience_turns} turns of patience
- If the assistant repeats the same question 3+ times, show mild frustration
- After {patience_turns} turns, end the call politely

CURRENT TURN: {{turn_count}}

Respond ONLY with valid JSON in this exact format:
{{"speech": "<German text to say>", "end_politely": false, "abandon": false, "internal_note": "<optional>"}}
"""
        return (
            self.system_prompt_base
            .replace("{SCENARIO}", "")
            + "\n" + scenario_block
        )

    @staticmethod
    def _format_identity(identity: dict) -> str:
        """Format caller identity for prompt."""
        lines = []
        if "name" in identity:
            lines.append(f"  Name: {identity['name']}")
        if "phone" in identity:
            lines.append(f"  Phone: {identity['phone']}")
        if "address" in identity:
            lines.append(f"  Address: {identity['address']}")
        return "\n".join(lines) if lines else "  (standard caller)"

    async def generate_utterance(
        self,
        scenario_goal: str,
        caller_identity: dict,
        confirmation_phrases: list[str],
        patience_turns: int,
        conversation_history: list[dict],
    ) -> PersonaResponse:
        """Generate next caller utterance via Claude Haiku JSON-mode."""
        import asyncio

        self.turn_count += 1
        system_prompt = self.build_system_prompt(
            scenario_goal, caller_identity, confirmation_phrases, patience_turns
        )
        system_prompt = system_prompt.replace("{turn_count}", str(self.turn_count))

        # Build messages — Anthropic requires alternating user/assistant starting with user.
        # The history starts with the bot greeting (assistant role), so we need to fix ordering.
        messages = [{"role": m["role"], "content": m["content"]} for m in conversation_history]

        # Ensure first message is "user" (Anthropic requirement)
        if not messages or messages[0]["role"] != "user":
            messages.insert(0, {"role": "user", "content": "(Anruf startet)"})

        # If adjacent same-role messages exist, deduplicate/merge them
        deduped: list[dict] = []
        for msg in messages:
            if deduped and deduped[-1]["role"] == msg["role"]:
                deduped[-1]["content"] += " " + msg["content"]
            else:
                deduped.append(dict(msg))
        messages = deduped

        try:
            # Run synchronous Anthropic client in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.messages.create(
                    model="claude-haiku-4-5",
                    max_tokens=256,
                    system=system_prompt,
                    messages=messages,
                ),
            )

            content = response.content[0].text if response.content else ""
            if not content:
                logger.warning("[Persona] Empty response from Claude — using fallback")
                return PersonaResponse(speech="Ja, bitte.", end_politely=False)

            logger.debug(f"[Persona] Raw response: {content[:120]!r}")

            # Extract JSON — handle various wrappers the model may add
            import re as _re
            content_clean = content.strip()
            # Remove any <<HUMAN_CONVERSATION_END>> or similar artifacts
            content_clean = _re.sub(r"<<[A-Z_]+>>", "", content_clean).strip()
            # Strip markdown fences
            if content_clean.startswith("```"):
                parts = content_clean.split("```")
                content_clean = parts[1] if len(parts) > 1 else content_clean
                if content_clean.startswith("json"):
                    content_clean = content_clean[4:]
                content_clean = content_clean.strip()
            # Find first complete JSON object
            m_json = _re.search(r"\{.*\}", content_clean, _re.DOTALL)
            if m_json:
                content_clean = m_json.group(0)

            try:
                data = json.loads(content_clean)
            except json.JSONDecodeError:
                # Fallback: extract any German text present
                logger.warning(f"[Persona] Failed to parse JSON: {content[:100]!r}")
                data = {"speech": content_clean[:200], "abandon": False}

            return PersonaResponse(
                speech=data.get("speech", ""),
                end_politely=data.get("end_politely", False),
                abandon=data.get("abandon", False),
                internal_note=data.get("internal_note", ""),
            )

        except Exception as e:
            logger.error(f"[Persona] Claude call failed: {e}")
            raise


def precheck_openai_api_key() -> bool:
    """Check if an API key is set (ANTHROPIC or OPENAI). Raises if neither."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not anthropic_key and not openai_key:
        raise ValueError(
            "Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY set in environment."
        )
    return True
