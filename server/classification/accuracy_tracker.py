"""
LLM Accuracy Monitoring for Scenario Classification.

Tracks:
- Haiku classification confidence calibration
- Confusion matrix (predicted vs actual scenario)
- Rules refinement metrics (confidence before/after rules)

Stored in Redis for real-time dashboarding. Data persisted to Postgres weekly.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ClassificationMetric:
    """Per-call classification accuracy tracking."""

    call_sid: str
    timestamp: float
    llm_confidence: float  # Pre-rules confidence
    final_confidence: float  # Post-rules confidence
    primary_scenario: str  # Predicted
    actual_scenario: Optional[str] = None  # Ground truth (filled by user feedback)
    confidence_calibrated: bool = False  # Did confidence match reality?
    modifiers_count: int = 0
    rules_applied: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for Redis/JSON."""
        return {
            **asdict(self),
            "timestamp": self.timestamp,
            "rules_applied": self.rules_applied,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ClassificationMetric:
        """Deserialize from Redis/JSON."""
        return cls(**data)


class ScenarioAccuracyTracker:
    """
    Track classification accuracy over time.
    
    Data stored in Redis for fast queries, periodic batch to Postgres.
    """

    _REDIS_KEY = "scenario_classifier:accuracy"  # Sorted set by timestamp
    _REDIS_CONFUSION_KEY = "scenario_classifier:confusion_matrix"  # Hash

    def __init__(self, redis_client=None):
        """Initialize with optional Redis client."""
        self.redis = redis_client
        self.metrics: Dict[str, ClassificationMetric] = {}

    async def record_classification(
        self,
        call_sid: str,
        llm_confidence: float,
        final_confidence: float,
        primary_scenario: str,
        modifiers_count: int = 0,
        rules_applied: Optional[List[str]] = None,
    ) -> None:
        """Record a classification event."""
        metric = ClassificationMetric(
            call_sid=call_sid,
            timestamp=time.time(),
            llm_confidence=llm_confidence,
            final_confidence=final_confidence,
            primary_scenario=primary_scenario,
            modifiers_count=modifiers_count,
            rules_applied=rules_applied or [],
        )

        self.metrics[call_sid] = metric

        # Store in Redis for real-time queries
        if self.redis:
            try:
                await self.redis.hset(
                    self._REDIS_KEY,
                    call_sid,
                    json.dumps(metric.to_dict()),
                )
                logger.debug(f"[AccuracyTracker] Recorded {call_sid}")
            except Exception as e:
                logger.warning(f"[AccuracyTracker] Redis store failed: {e}")

    async def record_feedback(
        self,
        call_sid: str,
        actual_scenario: str,
        notes: str = "",
    ) -> None:
        """Record ground-truth feedback (from user or validator)."""
        if call_sid in self.metrics:
            metric = self.metrics[call_sid]
            metric.actual_scenario = actual_scenario
            metric.notes = notes

            # Check if confidence was calibrated
            if metric.primary_scenario == actual_scenario:
                metric.confidence_calibrated = True

            # Update confusion matrix
            if self.redis:
                matrix_key = f"{metric.primary_scenario}_vs_{actual_scenario}"
                try:
                    count = await self.redis.hget(
                        self._REDIS_CONFUSION_KEY, matrix_key
                    )
                    await self.redis.hset(
                        self._REDIS_CONFUSION_KEY,
                        matrix_key,
                        int(count or 0) + 1,
                    )
                except Exception as e:
                    logger.warning(f"[AccuracyTracker] Confusion matrix update failed: {e}")

            logger.info(
                f"[AccuracyTracker] Feedback recorded {call_sid}: "
                f"predicted={metric.primary_scenario}, actual={actual_scenario}"
            )

    async def get_accuracy_report(
        self, window_hours: int = 24
    ) -> Dict[str, Any]:
        """Generate accuracy report for the last N hours."""
        cutoff_time = time.time() - (window_hours * 3600)

        # Filter recent metrics
        recent = [
            m for m in self.metrics.values() if m.timestamp >= cutoff_time
        ]

        if not recent:
            return {"total": 0, "message": "No data in window"}

        # Calculate stats
        with_feedback = [m for m in recent if m.actual_scenario is not None]
        correct = sum(
            1
            for m in with_feedback
            if m.primary_scenario == m.actual_scenario
        )
        accuracy = (correct / len(with_feedback)) if with_feedback else None

        avg_llm_conf = sum(m.llm_confidence for m in recent) / len(recent)
        avg_final_conf = sum(m.final_confidence for m in recent) / len(recent)

        # Confidence improvement from rules
        conf_improvement = avg_final_conf - avg_llm_conf

        return {
            "window_hours": window_hours,
            "total_classifications": len(recent),
            "with_feedback": len(with_feedback),
            "accuracy": accuracy,
            "avg_llm_confidence": round(avg_llm_conf, 3),
            "avg_final_confidence": round(avg_final_conf, 3),
            "confidence_improvement": round(conf_improvement, 3),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_confusion_matrix(self) -> Dict[str, int]:
        """Fetch confusion matrix (predicted vs actual)."""
        if not self.redis:
            return {}

        try:
            matrix = await self.redis.hgetall(self._REDIS_CONFUSION_KEY)
            # Convert bytes to dict if needed
            return {
                k.decode() if isinstance(k, bytes) else k: int(
                    v.decode() if isinstance(v, bytes) else v
                )
                for k, v in matrix.items()
            }
        except Exception as e:
            logger.warning(f"[AccuracyTracker] Confusion matrix fetch failed: {e}")
            return {}

    async def export_to_postgres(self, session) -> None:
        """Batch export metrics to Postgres for persistence."""
        # Note: Requires google_classifier_metrics table
        # Would implement table creation + upsert here
        logger.info(
            f"[AccuracyTracker] Would export {len(self.metrics)} metrics to Postgres"
        )


# ────────────────────────────────────────────────────────────────────────────
# SINGLETON INSTANCE (initialized on app startup)
# ────────────────────────────────────────────────────────────────────────────

_accuracy_tracker: Optional[ScenarioAccuracyTracker] = None


def get_accuracy_tracker() -> ScenarioAccuracyTracker:
    """Get or create the accuracy tracker singleton."""
    global _accuracy_tracker
    if _accuracy_tracker is None:
        _accuracy_tracker = ScenarioAccuracyTracker()
    return _accuracy_tracker


async def init_accuracy_tracker(redis_client) -> None:
    """Initialize tracker with Redis connection (call from app startup)."""
    global _accuracy_tracker
    _accuracy_tracker = ScenarioAccuracyTracker(redis_client=redis_client)
    logger.info("[AccuracyTracker] Initialized with Redis")
