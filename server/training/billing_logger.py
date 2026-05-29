"""
Daily billing and usage logger for cost backtracking and 4-stack failure analysis.

Logs per-call usage (TTS chars, LLM tokens, STT seconds) with timestamps,
run IDs, call_id, tenant_id, FSM phase, and model names so daily totals can be 
reconciled against Google Cloud invoice SKU lines. Enables cross-component tracing:
- Stack 1 (Telephony): SIP/WebRTC connection, call setup
- Stack 2 (Audio): VAD/ASR codec, voice activity
- Stack 3 (Intelligence): LLM, FSM phase transitions
- Stack 4 (Output): TTS encoding

Example output (JSONL):
```json
{"timestamp":"2026-04-12T10:15:30Z","run_id":"val_iter8_001","event_type":"call_complete","call_id":"conv_abc123","tenant_id":"doboo","user_id":"user_xyz","fsm_phase":"ORDER","tts_engine":"gemini-flash","tts_chars":1250,"gemini_in":450,"gemini_out":120,"deepgram_seconds":15.3,"cost_usd":0.0412}
{"timestamp":"2026-04-12T10:16:45Z","run_id":"val_iter8_001","event_type":"daily_summary","date":"2026-04-12","total_tts_chars":125000,"total_gemini_in":45000,"total_gemini_out":12000,"total_deepgram_sec":300.5,"total_cost_usd":4.56}
```
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BillingLogger:
    """Logs API usage (TTS chars, LLM tokens, STT seconds) with full context for backtracking."""

    def __init__(
        self,
        log_dir: str = "/var/log/sailly/billing",
        run_id: str = "default",
        tts_engine: str = "gemini-flash",
    ):
        """
        Args:
            log_dir: Directory for JSONL logs (created if missing).
            run_id: Identifier for this validation/training run (e.g., "val_iter8_001").
            tts_engine: TTS engine in use ("gemini-flash", "neural2", "gemini-pro", etc.).
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.run_id = run_id
        self.tts_engine = tts_engine
        
        # Daily accumulator for summary at end of day
        self.daily_totals: Dict[str, Any] = {
            "tts_chars": 0,
            "tts_char_count": 0,  # number of TTS calls
            "gemini_input_tokens": 0,
            "gemini_output_tokens": 0,
            "gemini_calls": 0,
            "deepgram_seconds": 0.0,
            "deepgram_requests": 0,
            "cost_usd": 0.0,
            "calls_logged": 0,
        }
        
        # Get today's log file (in UTC)
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.log_file = self.log_dir / f"billing_{today_utc}.jsonl"

    def log_call(
        self,
        tts_chars: int = 0,
        gemini_input_tokens: int = 0,
        gemini_output_tokens: int = 0,
        deepgram_seconds: float = 0.0,
        cost_usd: float = 0.0,
        call_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        fsm_phase: Optional[str] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a single API call with usage details (4-stack tracing enabled).

        Args:
            tts_chars: Number of characters synthesized (TTS).
            gemini_input_tokens: LLM input tokens (Gemini).
            gemini_output_tokens: LLM output tokens (Gemini).
            deepgram_seconds: Duration of audio processed (STT).
            cost_usd: Estimated USD cost for this call.
            call_id: Unique call identifier (for cross-component tracing).
            tenant_id: Tenant identifier (doboo, pizzeria_napoli, etc.).
            user_id: User/customer identifier.
            fsm_phase: Current FSM phase (GREETING, INFO, ORDER, etc.).
            extra_fields: Additional context (e.g., {"scenario_id": "p1-order-01"}).
        """
        timestamp_utc = datetime.now(timezone.utc).isoformat() + "Z"
        
        record = {
            "timestamp": timestamp_utc,
            "run_id": self.run_id,
            "event_type": "call_complete",
            "tts_engine": self.tts_engine,
            "tts_chars": tts_chars,
            "gemini_input_tokens": gemini_input_tokens,
            "gemini_output_tokens": gemini_output_tokens,
            "deepgram_seconds": round(deepgram_seconds, 2),
            "cost_usd": round(cost_usd, 5),
        }
        
        # Add 4-stack tracing fields (for observability)
        if call_id:
            record["call_id"] = call_id
        if tenant_id:
            record["tenant_id"] = tenant_id
        if user_id:
            record["user_id"] = user_id
        if fsm_phase:
            record["fsm_phase"] = fsm_phase
        
        if extra_fields:
            record.update(extra_fields)
        
        # Append to JSONL
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record) + "\n")
        
        # Update daily totals
        self.daily_totals["tts_chars"] += tts_chars
        if tts_chars > 0:
            self.daily_totals["tts_char_count"] += 1
        self.daily_totals["gemini_input_tokens"] += gemini_input_tokens
        self.daily_totals["gemini_output_tokens"] += gemini_output_tokens
        if gemini_input_tokens > 0 or gemini_output_tokens > 0:
            self.daily_totals["gemini_calls"] += 1
        self.daily_totals["deepgram_seconds"] += deepgram_seconds
        if deepgram_seconds > 0:
            self.daily_totals["deepgram_requests"] += 1
        self.daily_totals["cost_usd"] += cost_usd
        self.daily_totals["calls_logged"] += 1

    def log_daily_summary(self) -> None:
        """
        Write daily summary record (for easy aggregation).
        Call this at end of day or end of run.
        """
        timestamp_utc = datetime.now(timezone.utc).isoformat() + "Z"
        date_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        summary = {
            "timestamp": timestamp_utc,
            "run_id": self.run_id,
            "event_type": "daily_summary",
            "date": date_utc,
            "tts_engine": self.tts_engine,
            "total_tts_chars": self.daily_totals["tts_chars"],
            "total_tts_calls": self.daily_totals["tts_char_count"],
            "total_gemini_input_tokens": self.daily_totals["gemini_input_tokens"],
            "total_gemini_output_tokens": self.daily_totals["gemini_output_tokens"],
            "total_gemini_calls": self.daily_totals["gemini_calls"],
            "total_deepgram_seconds": round(self.daily_totals["deepgram_seconds"], 2),
            "total_deepgram_requests": self.daily_totals["deepgram_requests"],
            "total_cost_usd": round(self.daily_totals["cost_usd"], 2),
            "total_calls_logged": self.daily_totals["calls_logged"],
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(summary) + "\n")
        
        logger.info(
            f"Daily billing summary written to {self.log_file}: "
            f"TTS={self.daily_totals['tts_chars']} chars, "
            f"Gemini in={self.daily_totals['gemini_input_tokens']} out={self.daily_totals['gemini_output_tokens']} tokens, "
            f"Cost=${self.daily_totals['cost_usd']:.2f}"
        )

    def get_daily_totals(self) -> Dict[str, Any]:
        """Return current daily accumulator (useful for mid-run reporting)."""
        return self.daily_totals.copy()


# Singleton instance for app-wide access
_billing_logger: Optional[BillingLogger] = None


def init_billing_logger(
    log_dir: str = "/var/log/sailly/billing",
    run_id: str = "default",
    tts_engine: str = "chirp3hd",
) -> BillingLogger:
    """
    Initialize the global billing logger (call once at app startup).

    Args:
        log_dir: Directory for logs.
        run_id: Run identifier.
            tts_engine: Active TTS engine (default: "gemini-flash"). Chirp3 HD is deprecated.

    Returns:
        The initialized BillingLogger instance.
    """
    global _billing_logger
    _billing_logger = BillingLogger(log_dir=log_dir, run_id=run_id, tts_engine=tts_engine)
    logger.info(f"Billing logger initialized: {_billing_logger.log_file}")
    return _billing_logger


def get_billing_logger() -> BillingLogger:
    """Get the global billing logger (must be initialized first)."""
    if _billing_logger is None:
        raise RuntimeError("Billing logger not initialized. Call init_billing_logger() first.")
    return _billing_logger
