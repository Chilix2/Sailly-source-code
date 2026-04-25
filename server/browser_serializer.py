"""
Browser PCM16 frame serializer for Pipecat.

Wire format
-----------
Browser -> Server  (binary)  raw PCM16 LE, mono, 16 kHz audio chunks (no header)
Browser -> Server  (text)    JSON control message  {"type": "stop"}
Server  -> Browser (binary)  raw PCM16 LE, mono, 24 kHz audio chunks (bot speech)
Server  -> Browser (text)    JSON event:
    {"type": "transcript", "speaker": "user"|"bot", "text": "..."}
    {"type": "bot_text", "text": "..."}
"""

import json

from loguru import logger
from pipecat.frames.frames import (
    Frame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    OutputTransportMessageFrame,
    TranscriptionFrame,
)
from pipecat.serializers.base_serializer import FrameSerializer

BROWSER_INPUT_SAMPLE_RATE = 16_000
BROWSER_OUTPUT_SAMPLE_RATE = 24_000

_chunk_count = 0


class BrowserFrameSerializer(FrameSerializer):

    async def serialize(self, frame: Frame) -> str | bytes | None:
        if isinstance(frame, OutputAudioRawFrame):
            return bytes(frame.audio)

        if isinstance(frame, TranscriptionFrame) and frame.text:
            return json.dumps(
                {"type": "transcript", "speaker": "user", "text": frame.text},
                ensure_ascii=False,
            )

        if isinstance(frame, OutputTransportMessageFrame):
            msg = frame.message
            if isinstance(msg, str):
                return msg
            if isinstance(msg, dict):
                return json.dumps(msg, ensure_ascii=False)

        return None

    async def deserialize(self, data: str | bytes) -> Frame | None:
        global _chunk_count
        if isinstance(data, (bytes, bytearray)):
            audio_data = bytes(data)
            _chunk_count += 1
            if _chunk_count % 500 == 1:
                logger.debug(f"[BROWSER-AUDIO] chunk #{_chunk_count}: {len(audio_data)} bytes raw PCM16")

            return InputAudioRawFrame(
                audio=audio_data,
                sample_rate=BROWSER_INPUT_SAMPLE_RATE,
                num_channels=1,
            )

        try:
            msg = json.loads(data)
            logger.debug(f"[BrowserSerializer] control: {msg.get('type')}")
        except Exception:
            logger.warning(f"[BrowserSerializer] unparseable text: {str(data)[:80]}")

        return None
