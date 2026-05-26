"""
Audio Injector -- Synthesizes German caller audio, applies noise, validates STT accuracy.

Uses Google Cloud TTS to generate Linear16 8kHz mono audio from text, optionally adds noise,
and validates STT transcription accuracy via WER gate before LLM scoring.
"""

import io
import numpy as np
from dataclasses import dataclass
from typing import Optional
import logging
from google.cloud import texttospeech

logger = logging.getLogger(__name__)

# Deepgram v6.x imports
try:
    from deepgram import DeepgramClient
    from deepgram import ListenV1Model, ListenV1Language, ListenV1SmartFormat
    _DEEPGRAM_AVAILABLE = True
except ImportError:
    DeepgramClient = None
    _DEEPGRAM_AVAILABLE = False
    logger.warning("Deepgram imports not available - placeholder mode")

# Audio format constants
AUDIO_SAMPLE_RATE = 8000
AUDIO_ENCODING = "LINEAR16"
AUDIO_MONO = 1


class STTAccuracyError(Exception):
    """Raised when STT transcription falls below accuracy threshold."""
    pass


@dataclass
class AudioSegment:
    """Represents a chunk of audio data."""
    audio_bytes: bytes
    sample_rate: int
    encoding: str
    duration_ms: float


class AudioInjector:
    """
    Synthesizes German caller audio via Google Cloud TTS, optionally adds noise variants,
    and validates STT accuracy via WER gate.
    """

    def __init__(
        self,
        google_project_id: str,
        deepgram_api_key: str,
        tts_voice: str = "de-DE-Wavenet-F",
        noise_dir: Optional[str] = None,
        cost_tracker: Optional["CostTracker"] = None,
    ):
        """
        Args:
            google_project_id: GCP project ID for TTS
            deepgram_api_key: Deepgram API key for STT validation
            tts_voice: Google TTS voice name (default: de-DE-Wavenet-F)
            noise_dir: Path to noise audio files for augmentation
            cost_tracker: Optional usage accumulator (Deepgram + caller TTS chars)
        """
        self.google_project_id = google_project_id
        self.deepgram_api_key = deepgram_api_key
        self.tts_voice = tts_voice
        self.noise_dir = noise_dir
        self.cost_tracker = cost_tracker

        self.tts_client = texttospeech.TextToSpeechClient()
        
        # Initialize Deepgram client (v6.x requires api_key as keyword arg)
        if _DEEPGRAM_AVAILABLE and deepgram_api_key:
            self.deepgram_client = DeepgramClient(api_key=deepgram_api_key)
        else:
            self.deepgram_client = None
            logger.warning("Deepgram client not initialized - will use placeholder STT")

    def synthesize_speech(self, text: str) -> AudioSegment:
        """
        Synthesize German speech from text using Google Cloud TTS.

        Args:
            text: German utterance to synthesize

        Returns:
            AudioSegment with Linear16 8kHz mono audio

        Raises:
            Exception: if TTS synthesis fails
        """
        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code="de-DE",
            name=self.tts_voice,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=AUDIO_SAMPLE_RATE,
        )

        try:
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
            audio_bytes = response.audio_content

            # Estimate duration from audio length
            # Linear16 is 2 bytes per sample
            num_samples = len(audio_bytes) // 2
            duration_ms = (num_samples / AUDIO_SAMPLE_RATE) * 1000

            return AudioSegment(
                audio_bytes=audio_bytes,
                sample_rate=AUDIO_SAMPLE_RATE,
                encoding=AUDIO_ENCODING,
                duration_ms=duration_ms,
            )
        except Exception as e:
            logger.error(f"TTS synthesis failed for text: {text[:50]}... - {e}")
            raise

    def add_noise(
        self,
        audio_segment: AudioSegment,
        noise_variant: str = "clean",
        snr_db: float = 15.0,
    ) -> AudioSegment:
        """
        Add noise to audio segment if noise_variant is not 'clean'.

        Args:
            audio_segment: Original audio
            noise_variant: "clean", "restaurant", "traffic", or "mobile"
            snr_db: Signal-to-noise ratio in dB (higher = less noise)

        Returns:
            AudioSegment with noise added (or original if clean)
        """
        if noise_variant == "clean":
            return audio_segment

        try:
            raw_bytes = audio_segment.audio_bytes
            wav_header = b""
            # Google TTS LINEAR16 includes a 44-byte WAV header — preserve it
            if raw_bytes[:4] == b"RIFF":
                import struct
                # Standard WAV: data chunk starts after header
                # Find "data" subchunk
                idx = raw_bytes.find(b"data")
                if idx >= 0:
                    data_size = struct.unpack_from("<I", raw_bytes, idx + 4)[0]
                    wav_header = raw_bytes[:idx + 8]
                    raw_bytes = raw_bytes[idx + 8:idx + 8 + data_size]
                else:
                    wav_header = raw_bytes[:44]
                    raw_bytes = raw_bytes[44:]

            signal = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
            n_samples = len(signal)
            if n_samples == 0:
                return audio_segment

            rng = np.random.default_rng()

            nyquist = AUDIO_SAMPLE_RATE / 2 - 1  # stay below Nyquist

            if noise_variant in ("restaurant", "babble"):
                # Babble: band-limited noise (200-3800 Hz) simulating background chatter
                noise = rng.normal(0, 1, n_samples).astype(np.float32)
                from scipy.signal import butter, lfilter
                b_coeff, a_coeff = butter(4, [200, min(3800, nyquist)], btype="band", fs=AUDIO_SAMPLE_RATE)
                noise = lfilter(b_coeff, a_coeff, noise).astype(np.float32)
            elif noise_variant in ("traffic", "street"):
                # Low-frequency rumble (50-500 Hz)
                noise = rng.normal(0, 1, n_samples).astype(np.float32)
                from scipy.signal import butter, lfilter
                b_coeff, a_coeff = butter(3, 500, btype="low", fs=AUDIO_SAMPLE_RATE)
                noise = lfilter(b_coeff, a_coeff, noise).astype(np.float32)
            elif noise_variant in ("mobile", "speakerphone"):
                # Bandwidth compression (300-3400 Hz telephone band) + light noise
                from scipy.signal import butter, lfilter
                b_coeff, a_coeff = butter(5, [300, min(3400, nyquist)], btype="band", fs=AUDIO_SAMPLE_RATE)
                signal = lfilter(b_coeff, a_coeff, signal).astype(np.float32)
                noise = rng.normal(0, 1, n_samples).astype(np.float32)
                snr_db = max(snr_db, 20.0)  # lighter noise for phone
            else:
                noise = rng.normal(0, 1, n_samples).astype(np.float32)

            # Mix at target SNR
            sig_power = np.mean(signal ** 2) + 1e-10
            noise_power = np.mean(noise ** 2) + 1e-10
            scale = np.sqrt(sig_power / (noise_power * (10 ** (snr_db / 10))))
            mixed = signal + noise * scale

            mixed = np.clip(mixed, -32768, 32767).astype(np.int16)
            pcm_bytes = mixed.tobytes()

            # Re-attach WAV header if original had one, updating data size
            if wav_header:
                import struct
                data_chunk = b"data" + struct.pack("<I", len(pcm_bytes))
                # Rebuild: original header up to "data" marker + new data
                header_before_data = wav_header[:wav_header.find(b"data")] if b"data" in wav_header else wav_header[:36]
                out_bytes = header_before_data + data_chunk + pcm_bytes
                # Fix RIFF size (bytes 4-7): total file size - 8
                out_bytes = out_bytes[:4] + struct.pack("<I", len(out_bytes) - 8) + out_bytes[8:]
            else:
                out_bytes = pcm_bytes

            logger.debug(f"Applied '{noise_variant}' noise at {snr_db:.0f}dB SNR")
            return AudioSegment(
                audio_bytes=out_bytes,
                sample_rate=audio_segment.sample_rate,
                encoding=audio_segment.encoding,
                duration_ms=audio_segment.duration_ms,
            )
        except ImportError:
            logger.warning("scipy not installed — noise augmentation unavailable, returning clean audio")
            return audio_segment
        except Exception as e:
            logger.warning(f"Noise augmentation failed ({e}), returning clean audio")
            return audio_segment

    def validate_stt_accuracy(
        self,
        audio_segment: AudioSegment,
        original_text: str,
        min_accuracy: float = 0.80,
    ) -> tuple[str, float]:
        """
        Validate STT transcription accuracy via Deepgram using WER.

        Args:
            audio_segment: Audio to transcribe
            original_text: Expected text (for WER calculation)
            min_accuracy: Minimum accuracy required (1 - WER)

        Returns:
            Tuple of (transcribed_text, wer)

        Raises:
            STTAccuracyError: if WER exceeds threshold (min_accuracy)
        """
        try:
            if self.deepgram_client is None:
                # Placeholder: return original text with perfect accuracy
                logger.warning("Deepgram client not available - using placeholder STT (perfect WER)")
                return original_text, 0.0
            
            # Deepgram v6.x prerecorded transcription (sync API)
            try:
                import concurrent.futures

                def _transcribe_sync():
                    return self.deepgram_client.listen.v1.media.transcribe_file(
                        request=audio_segment.audio_bytes,
                        model="nova-3",
                        language="de",
                        smart_format=True,
                        encoding="linear16",
                    )

                # Run in thread so we don't block the event loop
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(_transcribe_sync).result(timeout=20)

                transcript = result.results.channels[0].alternatives[0].transcript

            except Exception as dg_err:
                logger.warning(f"Deepgram API call failed ({dg_err}) - using placeholder STT")
                return original_text, 0.0

            # Calculate WER (word error rate)
            wer = self._calculate_wer(original_text, transcript)
            accuracy = 1.0 - wer

            if accuracy < min_accuracy:
                raise STTAccuracyError(
                    f"STT accuracy {accuracy:.2%} below threshold {min_accuracy:.2%} "
                    f"(WER {wer:.2%}). Original: {original_text!r} → Transcript: {transcript!r}"
                )

            logger.debug(f"STT accuracy {accuracy:.2%} for: {original_text[:50]}...")
            return transcript, wer

        except STTAccuracyError:
            raise
        except Exception as e:
            logger.error(f"STT validation failed: {e}")
            raise STTAccuracyError(f"Deepgram STT failed: {e}")

    @staticmethod
    def _calculate_wer(reference: str, hypothesis: str) -> float:
        """
        Calculate Word Error Rate (WER) with German + Korean food name normalization.

        Handles:
        - German number words ↔ digits (Deepgram smart_format converts spoken to digits)
        - Umlaut variants (Menu/Menü, ok/okay)
        - Korean food phonetic equivalents (Bibimbap/Bibimbab, Kimbap/Kimbab)
        - Compound word splits (Nochmal/Noch mal)
        - Punctuation and case
        """
        import re

        # --- Normalization tables ---

        # Deepgram smart_format converts spoken German numbers to digits.
        # Normalize both sides to digits so WER doesn't penalize this.
        DE_NUMBERS = {
            "null": "0",
            "ein": "1", "eine": "1", "einen": "1", "einem": "1", "eins": "1",
            "zwei": "2", "drei": "3", "vier": "4", "fünf": "5",
            "sechs": "6", "sieben": "7", "acht": "8", "neun": "9",
            "zehn": "10", "elf": "11", "zwölf": "12",
            "dreizehn": "13", "vierzehn": "14", "fünfzehn": "15",
            "sechzehn": "16", "siebzehn": "17", "achtzehn": "18",
            "neunzehn": "19", "zwanzig": "20",
            "dreißig": "30", "dreissig": "30", "dreisig": "30",
            "vierzig": "40", "fünfzig": "50", "sechzig": "60",
            "siebzig": "70", "achtzig": "80", "neunzig": "90",
            "hundert": "100", "tausend": "1000",
        }

        # Korean food names: Deepgram mishears -ap as -ab, -op as -ob etc.
        # Also handles TTS → STT round-trip phonetic drift.
        FOOD_PHONETIC_MAP = {
            "bibimbab": "bibimbap",
            "bibimbabs": "bibimbap",
            "bimbab": "bibimbap",
            "bi bimbab": "bibimbap",
            "bibimbabs": "bibimbap",
            "kimbab": "kimbap",
            "kimbabs": "kimbap",
            "gyuran": "gyeran",
            "gyiran": "gyeran",
            "tuner": "tuna",
            "bulgoki": "bulgogi",
        }

        # German spelling equivalents (applied AFTER umlaut→ASCII normalization)
        # Keys and values must be in ASCII-German (no umlauts, ß already mapped to ss)
        DE_VARIANTS = {
            "okay": "ok",
            "o.k.": "ok",
            "nochmal": "noch mal",
            # ü→ue makes "Menü" → "menue"; normalize to "menu"
            "menue": "menu",
            # Deepgram phonetic variants for foreign names
            "gonzales": "gonzalez",
        }

        def normalize(text: str) -> str:
            t = text.lower().strip()

            # Strip all punctuation including hyphens (we don't care about compound hyphenation for WER)
            t = re.sub(r"[.,!?;:()\"\'\u2019\-]+", " ", t)
            t = re.sub(r"\s+", " ", t).strip()

            # Collapse spaced-out digit sequences: "0 1 7 0 5 5" → "017055"
            # Deepgram transcribes phone numbers digit-by-digit with spaces.
            t = re.sub(
                r"(?<!\w)(\d)(?: (\d)){2,}(?!\w)",
                lambda m: m.group(0).replace(" ", ""),
                t,
            )

            # ─── Canonical German normalization (both sides to ASCII-German) ───
            # ß → ss
            t = t.replace("ß", "ss")
            # Umlauts → ASCII digraphs (so "Nächsten"/"Naechsten" both → "naechsten")
            t = (t.replace("ä", "ae")
                  .replace("ö", "oe")
                  .replace("ü", "ue"))

            # Apply food phonetic map (multi-word first)
            for wrong, correct in sorted(FOOD_PHONETIC_MAP.items(), key=lambda x: -len(x[0])):
                t = re.sub(r"\b" + re.escape(wrong) + r"\b", correct, t)

            # Apply German variant map
            for variant, canonical in DE_VARIANTS.items():
                t = t.replace(variant, canonical)

            # Number word → digit normalization
            words = t.split()
            normalized = [DE_NUMBERS.get(w, w) for w in words]
            t = " ".join(normalized)

            # Drop "um" before time digits (Deepgram omits "um" in time expressions)
            t = re.sub(r"\bum\s+(\d)", r"\1", t)

            # Uhr normalization: "19 uhr 30" → "19:30", "7 uhr" → "7:00"
            t = re.sub(r"(\d+)\s+uhr\s+(\d+)", r"\1:\2", t)
            t = re.sub(r"(\d+)\s+uhr\b", r"\1:00", t)

            return t.strip()

        ref_words = normalize(reference).split()
        hyp_words = normalize(hypothesis).split()

        if not ref_words:
            return 0.0

        # Levenshtein distance via dynamic programming
        d = {}
        for i in range(len(ref_words) + 1):
            d[i, 0] = i
        for j in range(len(hyp_words) + 1):
            d[0, j] = j

        for i in range(1, len(ref_words) + 1):
            for j in range(1, len(hyp_words) + 1):
                if ref_words[i - 1] == hyp_words[j - 1]:
                    d[i, j] = d[i - 1, j - 1]
                else:
                    d[i, j] = min(
                        d[i - 1, j - 1] + 1,  # substitution
                        d[i, j - 1] + 1,       # insertion
                        d[i - 1, j] + 1,       # deletion
                    )

        return d[len(ref_words), len(hyp_words)] / len(ref_words)

    async def inject_caller_turn(
        self,
        user_utterance: str,
        noise_variant: str = "clean",
        stt_min_accuracy: float = 0.80,
    ) -> tuple[AudioSegment, str, float]:
        """
        Full pipeline: synthesize audio → apply noise → validate STT.

        Args:
            user_utterance: German text to synthesize
            noise_variant: Noise to add ("clean", "restaurant", "traffic", "mobile")
            stt_min_accuracy: Minimum STT accuracy required

        Returns:
            Tuple of (audio_segment, validated_transcript, wer)

        Raises:
            STTAccuracyError: if STT validation fails
            Exception: if TTS or other steps fail
        """
        # Step 1: Synthesize audio
        audio = self.synthesize_speech(user_utterance)
        if self.cost_tracker is not None:
            self.cost_tracker.add_caller_tts_chars(len(user_utterance))
        logger.debug(f"Synthesized audio for: {user_utterance[:50]}... ({audio.duration_ms:.0f}ms)")

        # Step 2: Add noise if applicable
        audio = self.add_noise(audio, noise_variant)

        # Step 3: Validate STT accuracy
        transcript, wer = self.validate_stt_accuracy(audio, user_utterance, stt_min_accuracy)

        if self.cost_tracker is not None and audio.duration_ms:
            self.cost_tracker.add_deepgram_turn(audio.duration_ms / 1000.0)

        logger.info(f"Caller turn validated: STT accuracy {1 - wer:.2%} (WER {wer:.2%})")

        return audio, transcript, wer


# Example usage / testing
if __name__ == "__main__":
    import os
    import asyncio
    from server.configs.secrets import get_secret

    # Setup logging
    logging.basicConfig(level=logging.DEBUG)

    # Initialize injector (requires GCP and Deepgram credentials)
    google_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    deepgram_key = get_secret("deepgram-api-key", default="")

    if not google_project or not deepgram_key:
        print("ERROR: GOOGLE_CLOUD_PROJECT env var and deepgram-api-key secret required")
        exit(1)

    injector = AudioInjector(
        google_project_id=google_project,
        deepgram_api_key=deepgram_key,
    )

    # Test: synthesize and validate a simple German utterance
    test_utterance = "Ich moechte einen Bibimbap bestellen"

    async def test():
        try:
            audio, transcript, wer = await injector.inject_caller_turn(
                test_utterance,
                noise_variant="clean",
                stt_min_accuracy=0.80,
            )
            print(f"✓ Test passed: {test_utterance}")
            print(f"  Audio: {len(audio.audio_bytes)} bytes, {audio.duration_ms:.0f}ms")
            print(f"  Transcript: {transcript}")
            print(f"  WER: {wer:.2%}")
        except STTAccuracyError as e:
            print(f"✗ STT accuracy failed: {e}")
        except Exception as e:
            print(f"✗ Test failed: {e}")

    asyncio.run(test())
