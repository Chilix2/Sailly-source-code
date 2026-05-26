"""
CallerAgent -- Adaptive caller for all phases.

GPT-5.4 nano (cheap, fast) as caller LLM.
OpenAI tts-1 (cheap, lower quality) for caller audio synthesis.
Supports personas (adversarial, dialect), barge-in simulation, noise.
"""

import asyncio
import logging
import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class CallerPersona(Enum):
    """Caller persona difficulty levels."""
    FRIENDLY = "friendly"  # Standard German speaker
    DIALECTAL = "dialectal"  # Bavarian, Northern German accents
    IMPATIENT = "impatient"  # Rushing, interrupting
    ADVERSARIAL = "adversarial"  # Rude, skeptical, AI-hostile
    OFF_TOPIC = "off_topic"  # Jokes, tangents, off-topic questions


@dataclass
class CallerConfig:
    """Configuration for caller agent."""
    persona: CallerPersona
    language: str = "de"  # German
    noise_profile: Optional[str] = None  # "restaurant", "street", "speakerphone"
    barge_in_enabled: bool = False
    barge_in_truncation_pct: float = 0.5  # 40-70% of bot audio before barge-in
    max_turns: int = 35
    temperature: float = 0.7  # More varied for realistic caller behavior


@dataclass
class CallerTurn:
    """Single turn from caller."""
    turn_number: int
    text: str
    audio: Optional[bytes] = None  # Audio synthesized via tts-1
    audio_duration_ms: float = 0.0
    is_barge_in: bool = False  # True if this turn interrupts bot


class CallerAgent:
    """
    Adaptive caller agent using GPT-5.4 nano + tts-1.
    Generates next caller line based on scenario and bot response.
    """

    def __init__(
        self,
        openai_api_key: str,
        model: str = "gpt-5.4-nano",
        temperature: float = 0.7,
    ):
        """
        Args:
            openai_api_key: OpenAI API key
            model: OpenAI model (gpt-5.4-nano for cheap caller)
            temperature: LLM temperature (0.7 for varied caller behavior)
        """
        self.openai_api_key = openai_api_key
        self.model = model
        self.temperature = temperature
        self.openai_client = None
        self.tts_client = None

    def _init_openai(self):
        """Initialize OpenAI client."""
        if self.openai_client is None:
            try:
                from openai import AsyncOpenAI

                self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
                logger.info(f"✓ OpenAI {self.model} client initialized for caller")
            except Exception as e:
                logger.error(f"Failed to init OpenAI client: {e}")
                raise

    async def generate_next_caller_line(
        self,
        scenario_context: str,
        bot_response: str,
        turn_number: int,
        persona: CallerPersona,
    ) -> str:
        """
        Generate next caller line using GPT-5.4 nano.

        Args:
            scenario_context: Scenario description + history
            bot_response: What the bot just said
            turn_number: Current turn number
            persona: Caller persona

        Returns:
            Next caller line (German text)
        """
        self._init_openai()

        persona_desc = self._get_persona_description(persona)
        system_prompt = f"""Du bist ein Anrufer beim Restaurant DOBOO in Bonn.
Deine Persönlichkeit: {persona_desc}

Antworte IMMER auf Deutsch mit 1-2 Sätzen.
Halte dich natürlich, nicht scripted.
Wenn Kunde fragt, antworte oder stelle Gegenfrage.
Nach Bestätigung einer Bestellung: bedanke dich und hänge ein."""

        user_prompt = f"""Szenario: {scenario_context}

Der Rezeptionist hat gerade gesagt:
"{bot_response}"

Deine nächste Reaktion (Turn {turn_number}):"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=100,
                timeout=10.0,
            )
            caller_line = response.choices[0].message.content.strip()
            logger.debug(f"[Caller] Turn {turn_number}: {caller_line}")
            return caller_line
        except Exception as e:
            logger.error(f"Failed to generate caller line: {e}")
            return "Moment, ich muss kurz nachdenken."

    def _get_persona_description(self, persona: CallerPersona) -> str:
        """Get personality description for system prompt."""
        descriptions = {
            CallerPersona.FRIENDLY: "Freundlich, geduldig, klar. Standard Deutsch.",
            CallerPersona.DIALECTAL: "Bayrischer Akzent. Nutze 'Servus', 'Grüß Gott'. Aussprache charakteristisch.",
            CallerPersona.IMPATIENT: "Ungeduldig, gehetzt. Unterbreche wenn nötig. Kurze Sätze.",
            CallerPersona.ADVERSARIAL: "Skeptisch, misstrauisch gegenüber KI. Sarkastische Kommentare. Manchmal unhöflich.",
            CallerPersona.OFF_TOPIC: "Witzig, off-topic. Erzähle Anekdoten. Lenke ab von Bestellung.",
        }
        return descriptions.get(persona, descriptions[CallerPersona.FRIENDLY])

    async def synthesize_caller_audio(
        self,
        text: str,
        voice: str = "alloy",  # tts-1 default voice
        sample_rate: int = 8000,
    ) -> bytes:
        """
        Synthesize caller audio using OpenAI tts-1 (cheap TTS).

        Args:
            text: German text to synthesize
            voice: tts-1 voice name
            sample_rate: Target sample rate (Linear16)

        Returns:
            Audio bytes (Linear16 PCM)
        """
        self._init_openai()

        try:
            response = await self.openai_client.audio.speech.create(
                model="tts-1",  # Cheap, lower quality
                voice=voice,
                input=text,
                response_format="wav",  # Will be PCM Linear16
            )
            audio_bytes = response.content
            logger.debug(f"[Caller TTS] Synthesized {len(audio_bytes)} bytes")
            return audio_bytes
        except Exception as e:
            logger.error(f"Failed to synthesize caller audio: {e}")
            return b"" # Fallback to silent audio

    async def get_caller_turn(
        self,
        scenario_context: str,
        bot_response: str,
        turn_number: int,
        config: CallerConfig,
    ) -> CallerTurn:
        """
        Generate a complete caller turn: text + synthesized audio.

        Args:
            scenario_context: Scenario description
            bot_response: What the bot just said
            turn_number: Current turn number
            config: Caller configuration (persona, noise, barge-in)

        Returns:
            CallerTurn with text + audio
        """
        # Generate caller text
        caller_text = await self.generate_next_caller_line(
            scenario_context,
            bot_response,
            turn_number,
            config.persona,
        )

        # Synthesize audio
        audio_bytes = await self.synthesize_caller_audio(caller_text)

        # Calculate audio duration (rough estimate: 16-bit Linear16, 8kHz)
        # PCM 16-bit, 8kHz = 2 bytes per sample at 8000 samples/sec
        audio_duration_ms = (len(audio_bytes) / 2) / 8 * 1000  # 8kHz → ms

        turn = CallerTurn(
            turn_number=turn_number,
            text=caller_text,
            audio=audio_bytes,
            audio_duration_ms=audio_duration_ms,
            is_barge_in=config.barge_in_enabled and turn_number > 1,
        )

        return turn

    def apply_barge_in(
        self,
        bot_audio: bytes,
        truncation_pct: float = 0.5,
    ) -> bytes:
        """
        Simulate barge-in by truncating bot audio.

        Args:
            bot_audio: Complete bot audio
            truncation_pct: Fraction of audio to keep before truncation

        Returns:
            Truncated audio (simulating caller talking over bot)
        """
        truncation_point = int(len(bot_audio) * truncation_pct)
        logger.debug(f"[Caller] Barge-in: truncating audio at {truncation_pct*100}%")
        return bot_audio[:truncation_point]

    async def should_call_end(
        self,
        turn_number: int,
        max_turns: int,
        conversation_resolved: bool,
    ) -> bool:
        """
        Decide if caller should end the call.

        Args:
            turn_number: Current turn number
            max_turns: Maximum turns allowed
            conversation_resolved: Whether order/reservation is complete

        Returns:
            True if call should end
        """
        # Hard cap: if we hit max_turns, end
        if turn_number >= max_turns:
            logger.info(f"[Caller] Reached max turns ({max_turns}), ending call")
            return True

        # If order/reservation resolved, caller can end naturally
        if conversation_resolved and turn_number > 3:
            # Randomly decide to end (with 40% probability after 3 turns)
            import random
            if random.random() < 0.4:
                logger.info("[Caller] Conversation resolved, ending call")
                return True

        return False

    async def get_goodbye_line(self, persona: CallerPersona) -> str:
        """Get natural goodbye from caller based on persona."""
        goodbyes = {
            CallerPersona.FRIENDLY: "Vielen Dank, auf Wiederhören!",
            CallerPersona.DIALECTAL: "Servus, danke schön!",
            CallerPersona.IMPATIENT: "Ok, tschüss!",
            CallerPersona.ADVERSARIAL: "Naja, bis dann.",
            CallerPersona.OFF_TOPIC: "Haha, tschüss zusammen!",
        }
        return goodbyes.get(persona, goodbyes[CallerPersona.FRIENDLY])
