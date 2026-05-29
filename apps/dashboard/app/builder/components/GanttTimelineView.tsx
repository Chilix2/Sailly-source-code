'use client';

import React from 'react';
import { TurnRow } from '@/types/sailly-debugger';

interface GanttBar {
  name: string;
  start: number; // relative to turn start
  duration: number;
  stage: string;
  color: string;
  metadata?: Record<string, any>;
}

/**
 * Gantt timeline view: wall-clock visualization of all turns
 * Shows stage concurrency (even if approximated) and relative latencies
 */
export function GanttTimelineView({ turns }: { turns: TurnRow[] }) {
  const maxLatencyMs = React.useMemo(() => {
    return Math.max(...turns.map((t) => t.total_latency_ms || 0), 1000);
  }, [turns]);

  const stageColors: Record<string, string> = {
    stt: '#3b82f6', // blue
    extract: '#a855f7', // purple
    l2: '#ea580c', // orange
    tool: '#dc2626', // red
    tts: '#16a34a', // green
  };

  const getGanttBars = (turn: TurnRow): GanttBar[] => {
    const bars: GanttBar[] = [];
    let offset = 0;

    if (turn.stt_ms) {
      bars.push({
        name: 'STT',
        start: offset,
        duration: turn.stt_ms,
        stage: 'stt',
        color: stageColors.stt,
        metadata: { confidence: turn.stt_confidence },
      });
      offset += turn.stt_ms;
    }

    if (turn.extract_ms) {
      bars.push({
        name: 'Extract',
        start: offset,
        duration: turn.extract_ms,
        stage: 'extract',
        color: stageColors.extract,
        metadata: {
          slots: `${turn.slots_filled_count}/${turn.slots_confirmed_count}`,
        },
      });
      offset += turn.extract_ms;
    }

    if (turn.l2_ms) {
      bars.push({
        name: 'LLM',
        start: offset,
        duration: turn.l2_ms,
        stage: 'l2',
        color: stageColors.l2,
        metadata: {
          tokens: `${turn.prompt_tokens_in} → ${turn.prompt_tokens_out}`,
        },
      });
      offset += turn.l2_ms;
    }

    if (turn.tool_ms && turn.tool_ms > 0) {
      bars.push({
        name: 'Tools',
        start: offset,
        duration: turn.tool_ms,
        stage: 'tool',
        color: stageColors.tool,
        metadata: { count: turn.tools_called?.length || 0 },
      });
      offset += turn.tool_ms;
    }

    if (turn.tts_ttfb_ms) {
      bars.push({
        name: 'TTS',
        start: offset,
        duration: turn.tts_ttfb_ms,
        stage: 'tts',
        color: stageColors.tts,
        metadata: { textLen: turn.bot_text?.length || 0 },
      });
    }

    return bars;
  };

  if (turns.length === 0) {
    return (
      <div className="p-6 text-center text-brand-muted text-sm">
        No turns available for Gantt visualization
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-brand-navy mb-2">
          Call Timeline (Gantt)
        </h2>
        <p className="text-xs text-brand-muted">
          Wall-clock concurrency view: each bar represents a stage duration
        </p>
      </div>

      {/* Timeline grid */}
      <div className="space-y-2 font-mono text-xs">
        {/* Header with time markers */}
        <div className="flex items-center gap-2">
          <div className="w-20 flex-shrink-0 text-brand-muted">Time</div>
          <div className="flex-1 relative h-6 bg-slate-50 rounded border border-brand-cream">
            {/* Time markers */}
            {[0, 25, 50, 75, 100].map((pct) => {
              const ms = (pct / 100) * maxLatencyMs;
              return (
                <div
                  key={pct}
                  className="absolute h-full flex items-center text-xs text-brand-muted"
                  style={{ left: pct + '%', transform: 'translateX(-50%)' }}
                >
                  <span className="border-l border-brand-cream pl-1">
                    {ms.toFixed(0)}ms
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Gantt bars for each turn */}
        {turns.map((turn) => {
          const bars = getGanttBars(turn);
          return (
            <div key={`turn-${turn.turn_number}`} className="flex items-center gap-2">
              <div className="w-20 flex-shrink-0 text-brand-muted">
                T{turn.turn_number}
              </div>
              <div className="flex-1 relative h-12 bg-slate-50 rounded border border-brand-cream overflow-hidden">
                {/* Render bars */}
                {bars.map((bar, idx) => {
                  const leftPct = (bar.start / maxLatencyMs) * 100;
                  const widthPct = (bar.duration / maxLatencyMs) * 100;
                  return (
                    <div
                      key={`${turn.turn_number}-${idx}`}
                      className="absolute h-full flex items-center justify-center text-xs font-semibold text-brand-navy transition-opacity hover:opacity-80 cursor-help"
                      style={{
                        left: leftPct + '%',
                        width: Math.max(widthPct, 3) + '%',
                        backgroundColor: bar.color,
                      }}
                      title={`${bar.name}: ${bar.duration.toFixed(0)}ms`}
                    >
                      {widthPct > 8 && (
                        <span className="truncate px-1">{bar.name}</span>
                      )}
                    </div>
                  );
                })}

                {/* Turn metadata */}
                <div className="absolute inset-0 flex items-end pb-0.5 px-2 text-xs text-brand-muted pointer-events-none">
                  <span>{turn.node_name}</span>
                </div>
              </div>
              <div className="w-16 text-right text-brand-muted">
                {turn.total_latency_ms?.toFixed(0)}ms
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="text-xs text-brand-muted space-y-1 border-t border-brand-cream pt-4">
        <h4 className="font-semibold text-slate-700 mb-2">Stage Legend:</h4>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(stageColors).map(([stage, color]) => (
            <div key={stage} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded"
                style={{ backgroundColor: color }}
              />
              <span>{stage.toUpperCase()}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Statistics */}
      <div className="bg-slate-50 p-4 rounded border border-brand-cream">
        <h4 className="text-sm font-semibold text-brand-navy mb-3">Statistics</h4>
        <div className="grid grid-cols-3 gap-4 text-xs">
          <div>
            <span className="text-brand-muted">Total Turns</span>
            <p className="text-lg font-semibold text-brand-navy">{turns.length}</p>
          </div>
          <div>
            <span className="text-brand-muted">Max Latency</span>
            <p className="text-lg font-semibold text-brand-navy">
              {Math.max(...turns.map((t) => t.total_latency_ms || 0)).toFixed(0)}ms
            </p>
          </div>
          <div>
            <span className="text-brand-muted">Avg Latency</span>
            <p className="text-lg font-semibold text-brand-navy">
              {(
                turns.reduce((sum, t) => sum + (t.total_latency_ms || 0), 0) /
                turns.length
              ).toFixed(0)}ms
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
