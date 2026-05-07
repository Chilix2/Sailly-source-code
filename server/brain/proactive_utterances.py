"""
Proactive Utterances — background state-triggered TTS without LLM.

FIX 4: When the bot is processing (extracting, waiting for LLM, etc.), emit short
canned German utterances to fill silence and reassure the caller that the system
is still active and working on their request.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

PROACTIVE_UTTERANCES = {
    "extraction_started_long_utterance": "Einen Moment, ich notiere alles...",
    "extraction_taking_longer": "Einen Augenblick noch, ich sortiere die Angaben...",
    "address_verification_started": "Ich prüfe die Adresse kurz...",
    "intent_completed_takeaway": "So, die Abholung ist notiert.",
    "intent_completed_delivery": "So, die Lieferung ist notiert.",
    "intent_completed_bulk_order": "So, die Sammelbestellung ist notiert.",
    "intent_completed_reservation": "So, die Reservierung ist notiert.",
    "menu_loading": "Einen Augenblick, ich hole die Menükarte...",
    "sms_sending": "Ich schicke Ihnen gleich die SMS-Bestätigung...",
}


async def emit_proactive(
    utterance_key: str,
    tts_service,
    logger_ref=None
) -> bool:
    """Immediately speak a canned utterance, bypassing the LLM."""
    text = PROACTIVE_UTTERANCES.get(utterance_key)
    if not text:
        if logger_ref:
            logger_ref.debug(f"[ProactiveUtterances] Unknown key: {utterance_key}")
        return False
    
    try:
        if hasattr(tts_service, 'speak'):
            await tts_service.speak(text, priority="interrupt_filler")
        elif hasattr(tts_service, 'push_frame'):
            from pipecat.frames.frames import TextFrame
            await tts_service.push_frame(TextFrame(text, priority="interrupt_filler"))
        
        if logger_ref:
            logger_ref.info(f"[ProactiveUtterances] Emitted: {utterance_key}")
        return True
    except Exception as e:
        if logger_ref:
            logger_ref.warning(f"[ProactiveUtterances] Failed to emit {utterance_key}: {e}")
        return False


def get_proactive_utterance(utterance_key: str) -> Optional[str]:
    """Get the text of a proactive utterance without speaking it."""
    return PROACTIVE_UTTERANCES.get(utterance_key)
