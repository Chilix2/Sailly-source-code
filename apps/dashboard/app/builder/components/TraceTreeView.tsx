'use client';

import React from 'react';
import { TurnRow } from '@/types/sailly-debugger';
import { ChevronRight } from 'lucide-react';

interface TraceSpan {
  id: string;
  name: string;
  startMs: number;
  endMs?: number;
  durationMs?: number;
  stage: 'stt' | 'extract' | 'l2' | 'tool' | 'tts' | 'total';
  children?: TraceSpan[];
  metadata?: Record<string, any>;
}

/**
 * Convert TurnRow into a hierarchical trace span tree.
 * Maps TurnTimings stage boundaries into a parent-child relationship.
 */
function turnRowToSpanTree(turn: TurnRow): TraceSpan {
  const spans: TraceSpan[] = [];
  let currentMs = 0;

  // STT stage
  if (turn.stt_ms) {
    spans.push({
      id: `stt-${turn.turn_number}`,
      name: 'STT',
      startMs: currentMs,
      durationMs: turn.stt_ms,
      endMs: currentMs + turn.stt_ms,
      stage: 'stt',
      metadata: {
        confidence: turn.stt_confidence,
        text: turn.user_text?.substring(0, 50) || '(silence)',
      },
    });
    currentMs += turn.stt_ms;
  }

  // Extraction stage (slot + entity extraction)
  if (turn.extract_ms) {
    spans.push({
      id: `extract-${turn.turn_number}`,
      name: 'Extract',
      startMs: currentMs,
      durationMs: turn.extract_ms,
      endMs: currentMs + turn.extract_ms,
      stage: 'extract',
      metadata: {
        slotsFilled: turn.slots_filled_count,
        slotsConfirmed: turn.slots_confirmed_count,
      },
    });
    currentMs += turn.extract_ms;
  }

  // Layer 2 (LLM) stage
  if (turn.l2_ms) {
    spans.push({
      id: `l2-${turn.turn_number}`,
      name: 'LLM',
      startMs: currentMs,
      durationMs: turn.l2_ms,
      endMs: currentMs + turn.l2_ms,
      stage: 'l2',
      metadata: {
        promptTokens: turn.prompt_tokens_in,
        outputTokens: turn.prompt_tokens_out,
        model: 'gemini-2.5',
      },
    });
    currentMs += turn.l2_ms;
  }

  // Tool execution stage
  if (turn.tool_ms && turn.tool_ms > 0) {
    const toolSpan: TraceSpan = {
      id: `tool-${turn.turn_number}`,
      name: 'Tools',
      startMs: currentMs,
      durationMs: turn.tool_ms,
      endMs: currentMs + turn.tool_ms,
      stage: 'tool',
      metadata: {
        toolsCount: turn.tools_called?.length || 0,
      },
      children: [],
    };

    // Add child spans for individual tools if tool_durations available
    if (turn.tool_durations && typeof turn.tool_durations === 'object') {
      let toolOffsetMs = 0;
      Object.entries(turn.tool_durations).forEach(([toolName, durationMs]) => {
        toolSpan.children?.push({
          id: `tool-${turn.turn_number}-${toolName}`,
          name: toolName,
          startMs: toolOffsetMs,
          durationMs: durationMs as number,
          endMs: toolOffsetMs + (durationMs as number),
          stage: 'tool',
          metadata: { tool: toolName },
        });
        toolOffsetMs += (durationMs as number);
      });
    }

    spans.push(toolSpan);
    currentMs += turn.tool_ms;
  }

  // TTS stage (time to first byte)
  if (turn.tts_ttfb_ms) {
    spans.push({
      id: `tts-${turn.turn_number}`,
      name: 'TTS',
      startMs: currentMs,
      durationMs: turn.tts_ttfb_ms,
      endMs: currentMs + turn.tts_ttfb_ms,
      stage: 'tts',
      metadata: {
        textLength: turn.bot_text?.length || 0,
      },
    });
    currentMs += turn.tts_ttfb_ms;
  }

  return {
    id: `turn-${turn.turn_number}`,
    name: `Turn ${turn.turn_number}`,
    startMs: 0,
    durationMs: turn.total_latency_ms || currentMs,
    endMs: turn.total_latency_ms || currentMs,
    stage: 'total',
    children: spans,
    metadata: {
      turnNumber: turn.turn_number,
      node: turn.node_name,
      intent: turn.intent,
    },
  };
}

interface TraceNodeProps {
  span: TraceSpan;
  depth: number;
  totalDurationMs: number;
}

function TraceNode({ span, depth, totalDurationMs }: TraceNodeProps) {
  const [expanded, setExpanded] = React.useState(depth < 2);
  const hasChildren = span.children && span.children.length > 0;
  const percentWidth = span.durationMs ? (span.durationMs / totalDurationMs) * 100 : 0;

  // Color by stage
  const stageColors: Record<string, string> = {
    stt: 'bg-blue-600',
    extract: 'bg-brand-pink',
    l2: 'bg-orange-600',
    tool: 'bg-red-600',
    tts: 'bg-green-600',
    total: 'bg-brand-muted',
  };

  const color = stageColors[span.stage] || 'bg-brand-muted';

  return (
    <div className="mb-1">
      <div className="flex items-center gap-2">
        {hasChildren && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-brand-muted hover:text-brand-navy p-0.5"
          >
            <ChevronRight
              className={`w-4 h-4 transition-transform ${
                expanded ? 'rotate-90' : ''
              }`}
            />
          </button>
        )}
        {!hasChildren && <div className="w-5" />}

        {/* Span name and metadata */}
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium text-brand-navy">
            {span.name}
            {span.durationMs && (
              <span className="text-brand-muted ml-2">
                {span.durationMs.toFixed(0)}ms
              </span>
            )}
          </div>
          {span.metadata && Object.keys(span.metadata).length > 0 && (
            <div className="text-xs text-brand-muted mt-0.5">
              {Object.entries(span.metadata)
                .map(([k, v]) => {
                  if (k === 'text' || k === 'textLength') return null;
                  if (!v && v !== 0) return null;
                  return `${k}: ${v}`;
                })
                .filter(Boolean)
                .join(' • ')}
            </div>
          )}
        </div>

        {/* Timeline bar */}
        <div
          className={`${color} rounded h-6 min-w-20 transition-opacity hover:opacity-80`}
          style={{ width: Math.max(40, percentWidth * 200) + 'px' }}
          title={`${span.durationMs?.toFixed(0)}ms`}
        />
      </div>

      {/* Children */}
      {hasChildren && expanded && (
        <div className="ml-6 mt-1 border-l border-brand-cream pl-2">
          {span.children?.map((child) => (
            <TraceNode
              key={child.id}
              span={child}
              depth={depth + 1}
              totalDurationMs={totalDurationMs}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function TraceTreeView({ turns }: { turns: TurnRow[] }) {
  const trees = React.useMemo(() => {
    return turns.map((turn) => turnRowToSpanTree(turn));
  }, [turns]);

  if (turns.length === 0) {
    return (
      <div className="p-6 text-center text-brand-muted text-sm">
        No turns available for trace tree visualization
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-brand-navy mb-2">
          Call Trace Tree
        </h2>
        <p className="text-xs text-brand-muted">
          Hierarchical view of all turns with per-stage latencies
        </p>
      </div>

      <div className="space-y-3">
        {trees.map((tree) => (
          <div key={tree.id} className="bg-slate-50 p-4 rounded border border-brand-cream">
            <TraceNode
              span={tree}
              depth={0}
              totalDurationMs={tree.durationMs || 1000}
            />
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="text-xs text-brand-muted space-y-1 border-t border-brand-cream pt-4">
        <h4 className="font-semibold text-slate-700 mb-2">Stage Legend:</h4>
        <div className="grid grid-cols-2 gap-2">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-600 rounded" />
            <span>STT (Speech-to-Text)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-brand-pink rounded" />
            <span>Extract (Slots)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-orange-600 rounded" />
            <span>LLM (Gemini)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-600 rounded" />
            <span>Tools</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-600 rounded" />
            <span>TTS (Text-to-Speech)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
