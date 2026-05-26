"""
Call Summary Manager for cross-call history persistence.

Saves compressed summaries of calls to Redis keyed by phone number.
When a repeat caller connects, their history is loaded and injected into the new call.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class CallSummary:
    """Store and retrieve compressed call summaries per phone number."""
    
    def __init__(self, redis_client):
        """
        Args:
            redis_client: Async Redis client instance
        """
        self.redis = redis_client
    
    async def get_caller_history(self, phone: str) -> Optional[dict]:
        """Load previous call summaries for this phone number.
        
        Args:
            phone: Caller's phone number (format: with or without +49, etc.)
        
        Returns:
            Dictionary with keys: timestamp, summary, nodes, tools, duration, outcome
            or None if no history found
        """
        key = f"caller_history:{phone}"
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"[CALL_SUMMARY] Failed to retrieve history for {phone}: {e}")
        
        return None
    
    async def save_call_summary(
        self,
        phone: str,
        summary: str,
        nodes_visited: list,
        tools_used: list,
        duration_seconds: int,
        outcome: str  # "completed", "transferred", "abandoned"
    ):
        """Save a compressed summary of this call for future reference.
        
        Args:
            phone: Caller's phone number
            summary: 1-2 sentence summary (e.g., "Ordered Bibimbap for delivery")
            nodes_visited: List of node names traversed during call
            tools_used: List of tools called
            duration_seconds: Call length in seconds
            outcome: How the call ended (completed/transferred/abandoned)
        
        Storage: Redis key expires after 30 days
        """
        history_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": summary,
            "nodes": nodes_visited,
            "tools": tools_used,
            "duration": duration_seconds,
            "outcome": outcome
        }
        
        key = f"caller_history:{phone}"
        try:
            await self.redis.set(
                key,
                json.dumps(history_entry),
                ex=30 * 24 * 3600  # 30-day retention
            )
            logger.info(f"[CALL_SUMMARY] {phone}: {summary[:60]}...")
        except Exception as e:
            logger.error(f"[CALL_SUMMARY] Failed to save summary for {phone}: {e}")
