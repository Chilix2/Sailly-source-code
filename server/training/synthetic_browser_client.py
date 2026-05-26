"""
Synthetic browser client for RealBrowserRun validation.

Connects to the browser demo WebSocket (same endpoint as the real browser),
sends synthesized caller audio (Google TTS → resample to 16kHz → PCM16 chunks),
collects bot transcript JSON messages, and returns a ConvResult compatible with
the existing call_auditor_de.py auditor via _conv_result_to_audit_turns.

Wire protocol (from browser_serializer.py):
  Handshake: JSON text   {"tenant": "doboo", "voice": "Kore", "style": "warm"}
  Audio in:  binary      [4-byte uint32 LE chunk counter] + PCM16 LE mono 16kHz
  Audio out: binary      PCM16 LE mono 24kHz (ignored by synthetic client)
  JSON out:  text        {"type": "transcript",   "speaker": "bot", "text": "..."}
                         {"type": "bot_text",      "text": "..."}
                         {"type": "tools_called",  "tools": ["get_date_info", ...]}
                         {"type": "KeepAlive"}

Usage:
    injector = AudioInjector(google_project_id=..., deepgram_api_key=...)
    scenario = AudioScenario(id="p1-faq-01", ...)
    client = SyntheticBrowserClient(
        ws_url="ws://localhost:3003/ws/demo",
        scenario=scenario,
        audio_injector=injector,
    )
    result = await client.run()   # returns ConvResult
"""

import asyncio
import json
import logging
import os
import re
import struct
import time
from typing import List, Optional

import numpy as np
import websockets
import websockets.exceptions

from server.scenarios.base import AudioScenario
from server.training.conversation_loop import ConvResult, ConvTurn

logger = logging.getLogger(__name__)


# ── Reactive caller LLM ───────────────────────────────────────────────────────

_PERSONA_INSTRUCTIONS = {
    "neutral":      "You are a normal, polite German-speaking customer.",
    "impatient":    "You are an impatient German caller. Keep answers very short. "
                    "Respond curtly, skip pleasantries, demand speed.",
    "angry":        "You are a frustrated, slightly irritated German caller. "
                    "Express mild dissatisfaction if things take too long.",
    "sleepy":       "You are a tired, slow-speaking German caller. "
                    "Sometimes trail off mid-sentence, use filler words like 'ähm'.",
    "accent":       "You are a caller with a heavy non-native German accent. "
                    "Mix in occasional English words or short English phrases.",
    "hard_to_hear": "You are calling from a noisy place. Keep utterances very short.",
    "chaos":        "You are a disorganised German caller. You change your mind, "
                    "contradict yourself, and ask the same thing twice.",
    "elderly":      "You are an elderly German caller. Speak slowly, sometimes "
                    "repeat yourself, and ask for clarification often.",
}

_CALLER_SYSTEM_TEMPLATE = """\
You are playing the role of a HUMAN CALLER phoning a German restaurant voice agent.

PERSONA: {persona_instruction}

YOUR GOAL: {goal}

CALLER DETAILS (provide these ONLY when the agent explicitly asks — do not volunteer them all at once):
{caller_details}

CRITICAL RULES:
1. You are the CALLER.  The "[AGENT]" prefix in the conversation marks what the restaurant
   agent says.  Your job is to respond naturally to whatever the agent just said.
2. Keep each turn SHORT — 1–2 sentences at most.  Real callers talk in short bursts.
3. FIRST TURN (when the agent just greeted you): Immediately state your PRIMARY GOAL.
   For orders: "Ich möchte [dish] bestellen." — say the dish and delivery/takeaway.
   For reservations: "Ich möchte einen Tisch für [N] Personen reservieren."
   Do NOT start with pleasantries, questions, or tangential topics on your first turn.
4. After the first turn, do NOT volunteer information the agent has not asked for yet.
   - If the agent asks "Darf ich Ihren Namen?" → give your name.
   - If the agent asks "Lieferadresse?" → give your address.
   - If the agent asks "Telefonnummer?" → give your phone number.
5. If the agent confirms your order/reservation, say "Ja, genau." or similar.
6. When the goal is fully achieved and confirmed, say a short goodbye such as
   "Super, danke! Tschüss." and nothing else.
7. NEVER break character.  NEVER mention you are an AI or a simulator.
8. Output ONLY your next spoken line — no stage directions, no quotes, no labels.
9. ALWAYS speak in German. The restaurant agent speaks German.
"""


class ReactiveCallerLLM:
    """
    Uses Claude Haiku to generate the next caller utterance in real-time,
    reacting to the bot's actual response instead of reading a fixed script.

    This makes scenarios realistic: the bot can ask for name/address/phone in
    any order and the simulated caller will answer correctly each time.
    """

    def __init__(self, scenario: "AudioScenario"):
        self.scenario = scenario
        self._history: List[dict] = []
        self._system_prompt = self._build_system_prompt()
        self._client = self._make_client()

    def _build_system_prompt(self) -> str:
        s = self.scenario
        persona_instr = _PERSONA_INSTRUCTIONS.get(
            s.persona or "neutral",
            _PERSONA_INSTRUCTIONS["neutral"],
        )
        details_parts = []
        if s.caller_name:
            details_parts.append(f"- Name: {s.caller_name}")
        if s.caller_phone:
            details_parts.append(f"- Phone: {s.caller_phone}")
        if s.caller_address:
            details_parts.append(f"- Address: {s.caller_address}")
        if not details_parts:
            details_parts.append("- (no specific details — improvise plausible ones)")
        return _CALLER_SYSTEM_TEMPLATE.format(
            persona_instruction=persona_instr,
            goal=s.goal,
            caller_details="\n".join(details_parts),
        )

    @staticmethod
    def _make_client():
        """Return an Anthropic client, raising clearly if the key is missing."""
        try:
            import anthropic  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError(
                "anthropic package not installed — run: pip install anthropic"
            ) from exc
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set in the environment.")
        return anthropic.Anthropic(api_key=api_key)

    def add_bot_turn(self, bot_text: str) -> None:
        """
        Record the bot's latest response.

        Anthropic role convention used here (reversed from intuition):
          "user"      → BOT messages (these are the inputs the caller reacts to)
          "assistant" → CALLER messages (the API generates these)

        This means the API always generates the caller's next utterance as the
        "assistant" turn, which is what we want.
        """
        self._history.append({"role": "user", "content": f"[AGENT] {bot_text}"})

    async def next_utterance(self) -> str:
        """
        Generate the caller's next utterance asynchronously.
        Runs the blocking Anthropic call in a thread-pool executor.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_sync)

    def _generate_sync(self) -> str:
        """
        Synchronous Anthropic call (run inside executor).

        Role convention (see add_bot_turn docstring):
          "user"      = BOT messages  (what the API "receives" as input)
          "assistant" = CALLER turns  (what the API generates for us)

        The API is asked to generate the next caller utterance as the next
        "assistant" turn, reacting to the latest "user" (bot) message.
        """
        if not self._history:
            # Should not normally happen — add_bot_turn is called before us.
            # Fallback: start the call.
            self._history.append({
                "role": "user",
                "content": "[AGENT] Hallo! Wie kann ich Ihnen helfen?",
            })

        response = self._client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=100,
            system=self._system_prompt,
            messages=self._history,
            stop_sequences=["[AGENT]", "<<"],
        )
        if not response.content:
            text = "Moment bitte."
        else:
            text = response.content[0].text.strip()

        # Strip any accidental meta-markers
        for marker in ("[AGENT]", "<<", "Human:", "Assistant:"):
            if marker in text:
                text = text.split(marker)[0].strip()
        if not text:
            text = "Ja."

        # Record the caller's utterance as an "assistant" turn
        self._history.append({"role": "assistant", "content": text})
        return text

    def is_done(self, utterance: str) -> bool:
        """Detect if the caller has said goodbye (goal achieved)."""
        goodbye_signals = ["tschüss", "auf wiederhören", "bye", "danke", "ciao"]
        low = utterance.lower()
        return any(g in low for g in goodbye_signals) and len(utterance) < 80

# Audio format constants
_BOT_SILENCE_GAP_S = 2.0   # seconds of no new message = bot is done
_SEND_SAMPLE_RATE   = 16_000
_SEND_BYTES_PER_SAMPLE = 2  # PCM16
_CHUNK_BYTES        = 4096  # audio bytes per WebSocket binary frame
_TOOL_RE            = re.compile(r"\[TOOL:(\w+)\]")


def _strip_wav_header(raw: bytes) -> bytes:
    """Remove the 44-byte WAV/RIFF header from Google TTS LINEAR16 output."""
    if raw[:4] == b"RIFF":
        idx = raw.find(b"data")
        if idx >= 0:
            import struct as _s
            data_size = _s.unpack_from("<I", raw, idx + 4)[0]
            return raw[idx + 8 : idx + 8 + data_size]
        return raw[44:]
    return raw


def _resample_8k_to_16k(pcm8k: bytes) -> bytes:
    """Upsample 8kHz PCM16 LE mono to 16kHz using soxr (high quality)."""
    try:
        import soxr
        samples = np.frombuffer(pcm8k, dtype=np.int16).astype(np.float32)
        resampled = soxr.resample(samples, 8_000, 16_000)
        return np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()
    except ImportError:
        try:
            import resampy
            samples = np.frombuffer(pcm8k, dtype=np.int16).astype(np.float32)
            resampled = resampy.resample(samples, 8_000, 16_000)
            return np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()
        except ImportError:
            # Fallback: simple nearest-neighbour 2x upsample
            samples = np.frombuffer(pcm8k, dtype=np.int16)
            return np.repeat(samples, 2).tobytes()


def _extract_tools(text: str) -> List[str]:
    """Extract [TOOL:name] tags from a bot response string."""
    return _TOOL_RE.findall(text)


class SyntheticBrowserClient:
    """
    Headless WebSocket client that replays a scripted AudioScenario through the
    real browser demo pipeline and captures the bot's responses.

    Returns a ConvResult directly usable by _conv_result_to_audit_turns +
    call_auditor_de.audit_call, enabling apples-to-apples comparison with Phase A.
    """

    def __init__(
        self,
        ws_url: str,
        scenario: AudioScenario,
        audio_injector,               # AudioInjector instance
        tenant_id: str = "doboo",
        voice: str = "Kore",
        style: str = "warm",
        bot_silence_gap_s: float = _BOT_SILENCE_GAP_S,
        bot_turn_timeout_s: float = 90.0,   # TurnAnalyzer(20s) + ADK brain(30s) + TTS(5s) = up to 55s
        greeting_timeout_s: float = 25.0,
        inter_turn_silence_s: float = 3.0,  # silence streamed between turns (keeps Deepgram VAD warm)
        post_utterance_tail_s: float = 1.5, # silence tail after each utterance (triggers VAD end-of-speech)
    ):
        self.ws_url = ws_url
        self.scenario = scenario
        self.audio_injector = audio_injector
        self.tenant_id = tenant_id
        self.voice = voice
        self.style = style
        self._silence_gap = bot_silence_gap_s
        self._turn_timeout = bot_turn_timeout_s
        self._greeting_timeout = greeting_timeout_s
        self._inter_turn_silence_s = inter_turn_silence_s
        self._post_utterance_tail_s = post_utterance_tail_s

    # ── Public API ────────────────────────────────────────────────────────────

    async def run(self) -> ConvResult:
        """
        Execute the scenario end-to-end and return a ConvResult.

        Raises asyncio.TimeoutError or websockets.exceptions.WebSocketException
        on connectivity failures — the runner handles these.
        """
        scenario = self.scenario
        t_start = time.monotonic()
        turns: List[ConvTurn] = []
        all_tools: List[str] = []
        end_reason = "max_turns"

        try:
            async with websockets.connect(
                self.ws_url,
                open_timeout=10,
                ping_interval=None,   # server sends KeepAlives; disable client pings
            ) as ws:
                # ── Handshake ───────────────────────────────────────────────
                await ws.send(json.dumps({
                    "tenant": self.tenant_id,
                    "voice": self.voice,
                    "style": self.style,
                }))
                logger.debug(f"[SynBrowser:{scenario.id}] Handshake sent")

                # ── Wait for greeting ───────────────────────────────────────
                t_greet_start = time.monotonic()
                greeting = await self._wait_for_bot_done(ws, timeout=self._greeting_timeout)
                greet_latency = (time.monotonic() - t_greet_start) * 1000

                logger.info(
                    f"[SynBrowser:{scenario.id}] Greeting: "
                    f"{greeting['text'][:70]!r} (tools={greeting['tools']})"
                )

                if greeting.get("call_ended"):
                    end_reason = "early_end"
                    return self._build_result(turns, all_tools, end_reason, t_start)

                # Capture tools fired during Turn-0 init (ai_greeting, get_menu etc.)
                all_tools.extend(greeting.get("tools", []))

                # ── Turn loop ───────────────────────────────────────────────
                chunk_counter = 0
                reactive = ReactiveCallerLLM(scenario) if scenario.goal else None
                # Feed the bot greeting into the reactive caller's history
                if reactive:
                    reactive.add_bot_turn(greeting["text"])

                max_turns = scenario.max_turns if scenario.goal else len(scenario.turns)
                for i in range(max_turns):
                    # ── Determine user utterance ─────────────────────────────
                    if reactive:
                        user_text = await reactive.next_utterance()
                        logger.info(
                            f"[SynBrowser:{scenario.id}] T{i} [reactive]: "
                            f"LLM caller → {user_text!r:.70}"
                        )
                    else:
                        if i >= len(scenario.turns):
                            break
                        user_text = scenario.turns[i].user_utterance

                    t_turn_start = time.monotonic()

                    # Inter-turn gap: stream silence frames instead of sleeping.
                    #
                    # A real browser microphone always sends audio (even silence),
                    # so Deepgram has continuous VAD context. Sending NOTHING during
                    # the gap means Deepgram has no state when speech restarts, and
                    # the first partial transcript races ahead of VAD — hitting the
                    # TurnAnalyzerUserTurnStopStrategy fallback path (no-VAD + stt_timeout=0)
                    # which fires user_turn_stopped in 2ms with empty text, absorbing
                    # the aggregation cycle before the real word is transcribed.
                    chunk_counter = await self._send_silence_frames(
                        ws, duration_s=self._inter_turn_silence_s, chunk_counter=chunk_counter
                    )

                    # Synthesize + prepare caller audio
                    t_tts_start = time.monotonic()
                    pcm16k = await asyncio.get_event_loop().run_in_executor(
                        None, self._prepare_audio, user_text
                    )
                    caller_latency_ms = (time.monotonic() - t_tts_start) * 1000

                    logger.debug(
                        f"[SynBrowser:{scenario.id}] Turn {i}: "
                        f"synthesized {len(pcm16k)} bytes for {user_text!r:.50}"
                    )

                    # Send audio to the pipeline
                    chunk_counter = await self._send_audio_frames(ws, pcm16k, chunk_counter)

                    # Wait for bot response
                    t_bot_start = time.monotonic()
                    bot_resp = await self._wait_for_bot_done(ws, timeout=self._turn_timeout)
                    bot_latency_ms = (time.monotonic() - t_bot_start) * 1000
                    total_latency_ms = (time.monotonic() - t_turn_start) * 1000

                    tools_this_turn = bot_resp["tools"]
                    all_tools.extend(tools_this_turn)

                    logger.info(
                        f"[SynBrowser:{scenario.id}] T{i}: "
                        f"user={user_text!r:.40} | "
                        f"bot={bot_resp['text']!r:.50} | "
                        f"tools={tools_this_turn} | "
                        f"latency={total_latency_ms:.0f}ms"
                    )

                    turns.append(ConvTurn(
                        turn_idx=i,
                        caller_text=user_text,
                        stt_transcript=user_text,  # we sent clean audio; treat as perfect STT
                        wer=0.0,
                        bot_response=bot_resp["text"],
                        tts_bytes=len(pcm16k),
                        tools_called=tools_this_turn,
                        caller_latency_ms=caller_latency_ms,
                        bot_latency_ms=bot_latency_ms,
                        total_latency_ms=total_latency_ms,
                        passed=True,  # auditor decides final pass/fail
                    ))

                    # Feed bot response into reactive caller's memory
                    if reactive:
                        reactive.add_bot_turn(bot_resp["text"])

                    # Detect call end via:
                    # 1. WebSocket ConnectionClosed (caught in _wait_for_bot_done)
                    # 2. end_call tool in bot response — server session ended, WS may
                    #    linger for 60-100s due to dangling Pipecat tasks; don't wait.
                    # 3. Reactive caller said goodbye (goal achieved)
                    call_ended_by_tool = "end_call" in tools_this_turn
                    caller_said_bye = reactive and reactive.is_done(user_text)
                    if bot_resp["call_ended"] or call_ended_by_tool or caller_said_bye:
                        if not bot_resp["text"] and not turns:
                            end_reason = "early_end"
                        elif caller_said_bye:
                            end_reason = "goal_achieved"
                        else:
                            end_reason = "end_call_tool"
                        # Close WS from our side so the server pipeline cleans up
                        # promptly rather than keeping the socket open for ~100s
                        try:
                            await ws.close()
                        except Exception:
                            pass
                        break

        except asyncio.TimeoutError:
            logger.warning(f"[SynBrowser:{scenario.id}] Timeout during scenario")
            end_reason = "timeout"
        except (websockets.exceptions.WebSocketException, OSError) as e:
            logger.error(f"[SynBrowser:{scenario.id}] WebSocket error: {e}")
            end_reason = "error"
            return self._build_result(turns, all_tools, f"error:{e}", t_start)

        return self._build_result(turns, all_tools, end_reason, t_start)

    # ── Audio helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_pcm(pcm16: bytes, min_rms_fraction: float = 0.20) -> bytes:
        """
        Boost-only normalization: amplify audio ONLY if it is too quiet for
        SileroVAD to detect. Loud audio is left unchanged.

        SileroVAD (min_volume=0.2, EBU R128) fails to detect short quiet words
        such as English "Goodbye." synthesized by a German TTS voice. Amplifying
        only quiet audio to a minimum RMS ensures reliable VAD detection without
        over-amplifying naturally loud words (e.g. German "Tschüss."), which would
        REDUCE their volume and push them below the same threshold.

        min_rms_fraction=0.20 → minimum RMS = 20% of int16 max ≈ -14 dBFS, which
        reliably clears the SileroVAD EBU R128 min_volume=0.2 threshold.
        """
        samples = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32)
        rms = float(np.sqrt(np.mean(samples ** 2)))
        min_rms = min_rms_fraction * 32767.0
        if 0 < rms < min_rms:
            gain = min_rms / rms
            samples = np.clip(samples * gain, -32767.0, 32767.0)
            return samples.astype(np.int16).tobytes()
        return pcm16

    def _prepare_audio(self, text: str) -> bytes:
        """
        Convert scripted text to 16kHz PCM16 mono bytes suitable for the
        browser demo WebSocket (after stripping WAV header and resampling).
        """
        seg = self.audio_injector.synthesize_speech(text)
        raw = _strip_wav_header(seg.audio_bytes)   # strip RIFF header if present
        if seg.sample_rate == 8_000:
            raw = _resample_8k_to_16k(raw)
        # If AudioInjector returns a different rate, let soxr handle it
        elif seg.sample_rate != 16_000:
            try:
                import soxr
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
                raw = np.clip(
                    soxr.resample(samples, seg.sample_rate, 16_000),
                    -32768, 32767
                ).astype(np.int16).tobytes()
            except ImportError:
                pass  # Use as-is; Deepgram may still decode it
        return raw

    async def _send_silence_frames(
        self, ws, duration_s: float, chunk_counter: int
    ) -> int:
        """
        Stream silence (zero-valued PCM) for `duration_s` seconds at real-time
        pace, maintaining a continuous audio stream over the WebSocket.

        A real browser microphone always sends audio — even between turns.
        Streaming silence keeps the Deepgram VAD in a known state so that when
        speech starts, VAD fires *before* the first partial transcript, avoiding
        the TurnAnalyzerUserTurnStopStrategy no-VAD fallback (timeout=0, 2ms
        phantom turn).
        """
        real_time_s_per_chunk = _CHUNK_BYTES / (_SEND_SAMPLE_RATE * _SEND_BYTES_PER_SAMPLE)
        silence = b"\x00" * _CHUNK_BYTES
        n_chunks = int(duration_s / real_time_s_per_chunk)
        for _ in range(n_chunks):
            header = struct.pack("<I", chunk_counter & 0xFFFFFFFF)
            await ws.send(header + silence)
            chunk_counter += 1
            await asyncio.sleep(real_time_s_per_chunk)
        return chunk_counter

    async def _send_audio_frames(
        self, ws, pcm16k: bytes, chunk_counter: int
    ) -> int:
        """
        Send PCM16 16kHz audio over the WebSocket in chunks matching the
        BrowserFrameSerializer wire format: [4-byte uint32 LE counter] + PCM.

        Paces sends at real-time rate so Deepgram VAD detects end-of-speech
        naturally (same as a real browser client).
        """
        real_time_s_per_chunk = _CHUNK_BYTES / (_SEND_SAMPLE_RATE * _SEND_BYTES_PER_SAMPLE)

        for offset in range(0, len(pcm16k), _CHUNK_BYTES):
            chunk = pcm16k[offset : offset + _CHUNK_BYTES]
            header = struct.pack("<I", chunk_counter & 0xFFFFFFFF)
            await ws.send(header + chunk)
            chunk_counter += 1
            await asyncio.sleep(real_time_s_per_chunk)

        # Send a silence tail so Deepgram VAD reliably fires end-of-utterance.
        # TurnAnalyzerUserTurnStopStrategy waits for VAD + then calls LLM for turn analysis;
        # insufficient silence causes the analyzer to keep waiting.
        silence = b"\x00" * _CHUNK_BYTES
        silence_chunks = int(self._post_utterance_tail_s / real_time_s_per_chunk) + 1
        for _ in range(silence_chunks):
            header = struct.pack("<I", chunk_counter & 0xFFFFFFFF)
            await ws.send(header + silence)
            chunk_counter += 1
            await asyncio.sleep(real_time_s_per_chunk)

        return chunk_counter

    # ── Response collection ───────────────────────────────────────────────────

    async def _wait_for_bot_done(self, ws, timeout: float) -> dict:
        """
        Collect bot transcript/text from WebSocket messages until a silence gap
        of `_silence_gap` seconds with no new message, a call_ended event, or
        `timeout` seconds elapse.

        Returns:
            {
                "text":       str  — concatenated bot transcript text
                "tools":      list — [TOOL:name] tags found in bot text
                "call_ended": bool
            }
        """
        text_parts: List[str] = []
        tools: List[str] = []
        call_ended = False
        deadline = time.monotonic() + timeout
        last_message_time = time.monotonic()
        last_tts_audio_time: float = 0.0  # last binary TTS frame received

        while True:
            now = time.monotonic()
            remaining = deadline - now
            silence_waited = now - last_message_time
            # Also require TTS audio to have stopped — otherwise sending the next
            # user turn while the bot is mid-speech causes a barge-in that can
            # confuse the Pipecat pipeline and cause no response on the next turn.
            tts_silent = (now - last_tts_audio_time) >= self._silence_gap

            if remaining <= 0:
                logger.debug(f"[SynBrowser] Bot turn timeout ({timeout}s)")
                break
            if silence_waited >= self._silence_gap and text_parts and tts_silent:
                # Received some text, no new text OR TTS audio for silence_gap — bot done
                break

            # Dynamic wait: if we have text AND TTS is done, wait up to silence_gap
            # for more; otherwise wait up to the full remaining deadline.
            text_gap_left = self._silence_gap - silence_waited
            tts_gap_left = self._silence_gap - (time.monotonic() - last_tts_audio_time) if last_tts_audio_time else remaining
            recv_timeout = min(
                remaining,
                max(text_gap_left, tts_gap_left) if text_parts else remaining,
            )
            recv_timeout = max(0.1, recv_timeout)

            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=recv_timeout)
            except asyncio.TimeoutError:
                if text_parts and tts_silent:
                    break  # silence gap elapsed and TTS done
                continue
            except websockets.exceptions.ConnectionClosed:
                call_ended = True
                break

            last_message_time = time.monotonic()

            if isinstance(msg, bytes):
                # Bot TTS audio — track last audio time so we can wait for TTS
                # to fully finish before sending the next user turn.
                last_tts_audio_time = time.monotonic()
                continue

            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")

            if msg_type == "call_ended":
                call_ended = True
                break

            elif msg_type == "transcript" and data.get("speaker") == "bot":
                chunk = data.get("text", "").strip()
                if chunk:
                    text_parts.append(chunk)
                    tools.extend(_extract_tools(chunk))

            elif msg_type == "tools_called":
                # Explicit tool list sent by BrowserToolsBroadcaster in the pipeline.
                # This is authoritative — no regex needed, no clean-text limitation.
                fired = data.get("tools", [])
                tools.extend(fired)

            elif msg_type == "bot_text":
                chunk = data.get("text", "").strip()
                if chunk:
                    # bot_text is incremental LLM output; deduplicate if
                    # transcript also arrives (TranscriptCaptureProcessor may
                    # send both). We only add if no transcript seen yet.
                    if not text_parts:
                        text_parts.append(chunk)
                    # Also check for legacy [TOOL:name] tags (Vertex LLM path)
                    tools.extend(_extract_tools(chunk))

            elif msg_type == "KeepAlive":
                # Heartbeat — reset silence timer so we don't exit prematurely
                # during the first greeting before any text arrives.
                if not text_parts:
                    last_message_time = time.monotonic()

        full_text = " ".join(text_parts).strip()
        return {
            "text": full_text,
            "tools": list(dict.fromkeys(tools)),  # deduplicate preserving order
            "call_ended": call_ended,
        }

    # ── Result builder ────────────────────────────────────────────────────────

    def _build_result(
        self,
        turns: List[ConvTurn],
        all_tools: List[str],
        end_reason: str,
        t_start: float,
    ) -> ConvResult:
        total_ms = (time.monotonic() - t_start) * 1000
        total_bytes = sum(t.tts_bytes for t in turns)

        # Deduplicate tools preserving first-occurrence order
        seen: dict = {}
        for tool in all_tools:
            seen[tool] = None
        unique_tools = list(seen.keys())

        expected = self.scenario.expected_tools or []
        passed = all(t in unique_tools for t in expected)

        phase_str = self.scenario.phase  # e.g. "phase1"
        try:
            phase_int = int(phase_str.replace("phase", ""))
        except (ValueError, AttributeError):
            phase_int = 0

        return ConvResult(
            scenario_id=self.scenario.id,
            phase=phase_int,
            run_number=1,
            turns=turns,
            tools_called=unique_tools,
            expected_tools=expected,
            total_latency_ms=total_ms,
            total_audio_bytes=total_bytes,
            passed=passed,
            end_reason=end_reason,
        )
