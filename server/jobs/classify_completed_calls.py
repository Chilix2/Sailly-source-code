"""
Background job: Classify completed calls with scenario tags (OPTIONAL - fallback only).

NOTE: Per-call classification is now triggered immediately in monitoring.py when
finalize_call_monitoring() is called. This job runs every 5 minutes as a fallback
to catch any calls that failed auto-classification or were missed.

Runs every 5 minutes:
1. Query Postgres for calls completed in the last 5 min without scenario_tags
2. Fetch transcripts + metadata from Postgres
3. Call classify_call_scenario() for each
4. Store result in CallMetric.extra["scenario_tags"]
5. Upsert back to Postgres

Typically <100ms per call (async LLM batch processing), non-blocking.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


async def classify_pending_calls_batch(max_batch_size: int = 50) -> None:
    """
    Classify calls completed in the last 5 minutes without scenario_tags.
    
    Args:
        max_batch_size: Max calls to process per run (default 50)
    """
    try:
        from server.db.postgres import get_async_session
        from sqlalchemy import text
        from server.classification.scenario_classifier import classify_call_scenario

        # Get database connection
        async_session = await get_async_session()

        # Query: Calls completed in last 5 min, no scenario_tags yet
        cutoff_time = (datetime.utcnow() - timedelta(minutes=5)).isoformat()

        query = f"""
            SELECT 
                call_sid,
                call_id,
                tenant_id,
                fulfilled,
                turn_count,
                duration_secs,
                end_reason,
                layer2_raw_output,
                layer3_changes
            FROM google_calls
            WHERE 
                created_at > '{cutoff_time}'
                AND (extra IS NULL OR extra->>'scenario_tags' IS NULL)
                AND call_sid IS NOT NULL
            ORDER BY created_at DESC
            LIMIT {max_batch_size}
        """

        async with async_session() as session:
            result = await session.execute(text(query))
            pending_calls = result.fetchall()

            if not pending_calls:
                logger.debug("[ClassifyJob] No pending calls to classify")
                return

            logger.info(f"[ClassifyJob] Classifying {len(pending_calls)} pending calls")

            # Process each call
            for call_row in pending_calls:
                call_sid = call_row[0]
                call_id = call_row[1]
                tenant_id = call_row[2]
                fulfilled = call_row[3]
                turn_count = call_row[4]
                duration_secs = call_row[5]
                end_reason = call_row[6]
                layer2_raw = call_row[7]
                layer3_changes = call_row[8]

                try:
                    # Fetch full transcript from google_transcripts
                    transcript_query = """
                        SELECT user_text, bot_text
                        FROM google_transcripts
                        WHERE call_id = :call_id
                        ORDER BY turn_number ASC
                    """

                    trans_result = await session.execute(
                        text(transcript_query), {"call_id": call_id}
                    )
                    transcript_rows = trans_result.fetchall()

                    # Build transcript string
                    transcript_text = "\n".join(
                        [
                            f"User: {row[0] or ''}\nBot: {row[1] or ''}"
                            for row in transcript_rows
                        ]
                    )

                    # Fetch tools_called from google_turn_metrics
                    tools_query = """
                        SELECT COALESCE(forced_tools, '[]'::jsonb)
                        FROM google_turn_metrics
                        WHERE call_id = :call_id
                        LIMIT 1
                    """
                    tools_result = await session.execute(
                        text(tools_query), {"call_id": call_id}
                    )
                    tools_row = tools_result.fetchone()
                    tools_called = tools_row[0] if tools_row else []

                    # Classify
                    scenario_tags = await classify_call_scenario(
                        call_sid=call_sid,
                        transcript_text=transcript_text,
                        tools_called=tools_called,
                        turn_count=turn_count,
                        duration_secs=duration_secs,
                        fulfilled=fulfilled,
                        end_reason=end_reason,
                        layer3_changes=layer3_changes,
                    )

                    # Update Postgres: upsert scenario_tags into extra
                    update_query = """
                        UPDATE google_calls
                        SET extra = JSONB_SET(
                            COALESCE(extra, '{}'::jsonb),
                            '{scenario_tags}',
                            :scenario_tags::jsonb
                        ),
                        updated_at = NOW()
                        WHERE call_sid = :call_sid
                    """

                    import json

                    await session.execute(
                        text(update_query),
                        {
                            "call_sid": call_sid,
                            "scenario_tags": json.dumps(scenario_tags),
                        },
                    )

                    logger.info(
                        f"[ClassifyJob] Classified {call_sid}: "
                        f"{scenario_tags['primary_scenario']} "
                        f"(phase {scenario_tags['scenario_phase']})"
                    )

                except Exception as e:
                    logger.error(
                        f"[ClassifyJob] Failed to classify {call_sid}: {e}",
                        exc_info=True,
                    )
                    continue

            # Commit all updates
            await session.commit()

    except Exception as e:
        logger.error(f"[ClassifyJob] Batch processing failed: {e}", exc_info=True)


async def run_classify_job_loop(interval_secs: int = 300) -> None:
    """
    Run the classification job on a loop.
    
    Args:
        interval_secs: Run interval in seconds (default 300 = 5 minutes)
    """
    logger.info(
        f"[ClassifyJob] Starting background job loop (interval={interval_secs}s)"
    )

    while True:
        try:
            await classify_pending_calls_batch()
        except Exception as e:
            logger.error(f"[ClassifyJob] Loop error: {e}", exc_info=True)

        await asyncio.sleep(interval_secs)


# ────────────────────────────────────────────────────────────────────────────
# STARTUP HOOK (called from server/main.py on app startup)
# ────────────────────────────────────────────────────────────────────────────


def start_classify_job_background() -> None:
    """Start the classification job as a background task."""
    import asyncio

    loop = asyncio.get_event_loop()
    
    # Start the job loop in the background
    task = loop.create_task(run_classify_job_loop())
    
    logger.info("[ClassifyJob] Background job started (PID: async task)")
