"""
Call audio recording — captures both sides of a demo call and produces:

  combined.wav  — stereo WAV (L = caller 16 kHz, R = agent resampled to 16 kHz)
                  → stored as caller_audio_url  (main playback recording)
  agent.wav     — agent TTS audio only (24 kHz mono)
                  → stored as agent_audio_url   (for debugging)

CallerAudioRecorder
    Registered as a callback on BrowserFrameSerializer.  Fires synchronously
    for every incoming binary WebSocket message before it enters the Pipecat
    pipeline queue.  This is race-free.

AgentAudioCapture
    Pipecat FrameProcessor that buffers OutputAudioRawFrame chunks.
    Unlike CallerAudioRecorder it does NOT upload by itself; the main
    websocket_demo handler calls finalize_all() at the end of the call.

finalize_all()
    Called from the websocket_demo finally-block.  Uploads agent.wav, builds
    the stereo combined.wav via audioop.ratecv + struct interleaving, uploads
    it, and writes both URLs back to google_calls.
"""

from __future__ import annotations

import audioop
import io
import struct
import wave
from datetime import timedelta
from typing import Awaitable, Callable, Optional

from loguru import logger
from pipecat.frames.frames import EndFrame, OutputAudioRawFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

GCS_BUCKET = "sailly-recordings-eu"
SIGNED_URL_TTL = timedelta(days=7)
CALLER_RATE = 16_000
AGENT_RATE  = 24_000
TARGET_RATE = 16_000        # both channels resampled to this rate in combined.wav


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_wav_mono(pcm_chunks: list[bytes], sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for chunk in pcm_chunks:
            wf.writeframes(chunk)
    return buf.getvalue()


def _build_stereo_wav(
    caller_chunks: list[bytes],   # PCM16 mono 16 kHz
    agent_chunks:  list[bytes],   # PCM16 mono 24 kHz
) -> bytes:
    """Return a stereo WAV with caller on L and agent on R, both at 16 kHz."""
    caller_pcm = b"".join(caller_chunks)
    agent_pcm  = b"".join(agent_chunks)

    # Resample agent from 24 kHz → 16 kHz
    if agent_pcm:
        agent_pcm_16k, _ = audioop.ratecv(
            agent_pcm, 2, 1, AGENT_RATE, TARGET_RATE, None
        )
    else:
        agent_pcm_16k = b""

    # Align lengths (pad shorter side with silence)
    caller_n = len(caller_pcm) // 2    # samples
    agent_n  = len(agent_pcm_16k) // 2
    max_n    = max(caller_n, agent_n)

    caller_samples = struct.unpack(f"<{caller_n}h", caller_pcm)
    agent_samples  = struct.unpack(f"<{agent_n}h",  agent_pcm_16k)

    # Pad with zeros
    caller_samples = caller_samples + (0,) * (max_n - caller_n)
    agent_samples  = agent_samples  + (0,) * (max_n - agent_n)

    # Interleave into stereo: [L0, R0, L1, R1, ...]
    stereo = bytearray(max_n * 4)   # 2 channels × 2 bytes
    for i, (l, r) in enumerate(zip(caller_samples, agent_samples)):
        struct.pack_into("<hh", stereo, i * 4, l, r)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(TARGET_RATE)
        wf.writeframes(bytes(stereo))
    return buf.getvalue()


def _gcs_client(credentials_path: str):
    from google.cloud import storage
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return storage.Client(project="sailly-voice-agent-eu", credentials=creds), creds


async def _upload_and_sign(
    wav_bytes:        bytes,
    call_sid:         str,
    filename:         str,
    credentials_path: str,
) -> str:
    client, creds = _gcs_client(credentials_path)
    bucket = client.bucket(GCS_BUCKET)
    blob   = bucket.blob(f"{call_sid}/{filename}")
    blob.upload_from_string(wav_bytes, content_type="audio/wav")
    url = blob.generate_signed_url(
        expiration=SIGNED_URL_TTL,
        method="GET",
        credentials=creds,
        version="v4",
    )
    logger.info(f"[AudioRecorder] {filename} uploaded ({len(wav_bytes) // 1024} KB)")
    return url


# ---------------------------------------------------------------------------
# CallerAudioRecorder  (callback-based, wired into BrowserFrameSerializer)
# ---------------------------------------------------------------------------

class CallerAudioRecorder:
    """Captures raw PCM16 from the browser synchronously during deserialization."""

    def __init__(self, call_sid: str, credentials_path: str):
        self._call_sid          = call_sid
        self._credentials_path  = credentials_path
        self.chunks: list[bytes] = []

    def on_audio(self, raw_bytes: bytes) -> None:
        """Called for every incoming binary WebSocket message."""
        if raw_bytes:
            self.chunks.append(raw_bytes)


# ---------------------------------------------------------------------------
# AgentAudioCapture  (FrameProcessor — buffers OutputAudioRawFrame)
# ---------------------------------------------------------------------------

class AgentAudioCapture(FrameProcessor):
    """Passthrough processor that collects agent TTS audio chunks."""

    def __init__(self):
        super().__init__()
        self.chunks: list[bytes] = []

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, OutputAudioRawFrame):
            if frame.audio:
                self.chunks.append(frame.audio)
        await self.push_frame(frame, direction)


# ---------------------------------------------------------------------------
# finalize_all  (called from websocket_demo finally-block)
# ---------------------------------------------------------------------------

async def finalize_all(
    call_sid:         str,
    credentials_path: str,
    caller_recorder:  CallerAudioRecorder,
    agent_capture:    AgentAudioCapture,
) -> tuple[str | None, str | None]:
    """
    Upload agent.wav and combined.wav to GCS.

    Returns
    -------
    (combined_url, agent_url)
        Signed GCS URLs valid for 7 days, or None if the upload failed or had
        no data.  The caller is responsible for persisting these to the DB
        *after* the brain session has been written, to avoid a race condition
        where the UPDATE runs before the INSERT.
    """
    caller_chunks = caller_recorder.chunks
    agent_chunks  = agent_capture.chunks

    logger.info(
        f"[AudioRecorder] finalizing call={call_sid} "
        f"caller_chunks={len(caller_chunks)} agent_chunks={len(agent_chunks)}"
    )

    combined_url: str | None = None
    agent_url:    str | None = None

    # Upload agent-only WAV
    if agent_chunks:
        try:
            agent_wav = _build_wav_mono(agent_chunks, AGENT_RATE)
            agent_url = await _upload_and_sign(agent_wav, call_sid, "agent.wav", credentials_path)
        except Exception as e:
            logger.warning(f"[AudioRecorder] agent.wav upload failed: {e}")

    # Build and upload stereo combined recording
    if caller_chunks or agent_chunks:
        try:
            combined_wav = _build_stereo_wav(caller_chunks, agent_chunks)
            combined_url = await _upload_and_sign(combined_wav, call_sid, "combined.wav", credentials_path)
            logger.info(
                f"[AudioRecorder] combined.wav ready "
                f"({len(combined_wav) // 1024} KB, "
                f"caller={len(caller_chunks)} chunks, "
                f"agent={len(agent_chunks)} chunks)"
            )
        except Exception as e:
            logger.warning(f"[AudioRecorder] combined.wav upload failed: {e}")

    return combined_url, agent_url
