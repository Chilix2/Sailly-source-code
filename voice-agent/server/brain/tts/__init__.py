"""
server.brain.tts — Phase 7 TTS output pipeline.

Modules:
    tts_client       — Gemini TTS streaming, emotion-tag injection/stripping
    tts_conditioning — rate computation (baseline × situation × mood + clamp)
    situation_styles — 15 SITUATION_STYLES dicts with tag, rate, prompt_add
    caller_mirrors   — 6 CALLER_MIRRORS dicts with rate_mul, prompt_add, skip_chitchat
    streaming        — TTSStreamCoordinator: sentence-streaming with fast-cut barge-in
    pronunciation    — SSML phoneme hints for menu items (Korean dishes etc.)
"""
