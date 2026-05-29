'use client';

import React from 'react';
import { useCallTurns } from '@/lib/api/debugger-client';
import { MOCK_CALL_TURNS } from '@/lib/api/mock-data';
import { useDebuggerStore } from '@/lib/store/debugger-store';
import { getStateColor, getStateLabel } from '@/lib/fsm/states';
import { TurnRow } from '@/types/sailly-debugger';
import { ArrowRight, CheckCircle, AlertTriangle, AlertCircle } from 'lucide-react';

type TurnStatus = 'success' | 'warning' | 'error';

function getTurnStatus(turn: TurnRow): TurnStatus {
  if (turn.layer1_decision?.validators_run?.some((v) => v.status === 'failed')) {
    return 'error';
  }
  if (turn.tts_suppressed_reason) {
    return 'error';
  }
  if (turn.layer3_changes?.warnings && turn.layer3_changes.warnings.length > 0) {
    return 'warning';
  }
  return 'success';
}

function statusBadge(status: TurnStatus) {
  switch (status) {
    case 'error':
      return <AlertCircle className="h-3.5 w-3.5 text-red-600" />;
    case 'warning':
      return <AlertTriangle className="h-3.5 w-3.5 text-orange-600" />;
    default:
      return <CheckCircle className="h-3.5 w-3.5 text-green-600" />;
  }
}

/**
 * Build a short edge label describing the transition into the next turn.
 * Uses forced tools first, then the next node's label.
 */
function edgeLabel(next: TurnRow): string {
  const forced = next.layer1_decision?.forced_tools || [];
  if (forced.length > 0) return forced[0];
  return '';
}

function nodeSubLabel(turn: TurnRow): string {
  const forced = turn.layer1_decision?.forced_tools || [];
  if (forced.length > 0) return forced.join(', ');
  const tools = turn.tools_called || [];
  if (tools.length > 0) return tools.join(', ');
  return turn.user_text ? turn.user_text.slice(0, 28) : '—';
}

export function CallFlowchart({ callSid }: { callSid: string }) {
  const useMock = process.env.NEXT_PUBLIC_USE_MOCK === 'true';
  const { selectedTenantId, selectedTurnIdx, setSelectedTurnIdx } =
    useDebuggerStore();

  const { data: turnsData } = useMock
    ? { data: MOCK_CALL_TURNS[callSid as keyof typeof MOCK_CALL_TURNS] }
    : useCallTurns(callSid, selectedTenantId);

  const turns = turnsData?.turns || [];

  if (turns.length === 0) {
    return (
      <div className="p-6 text-sm text-brand-muted">
        No turn data available for this call yet.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-6">
      <div>
        <h2 className="text-sm font-semibold text-brand-navy">Call Flow</h2>
        <p className="mt-1 text-xs text-brand-muted">
          Each node is a turn / FSM state. Click a node to inspect its Layer 1/2/3
          detail in the side panel.
        </p>
      </div>

      {/* Stable horizontal lane: deterministic order, fixed-width nodes */}
      <div className="overflow-x-auto pb-4">
        <div className="flex min-w-max items-stretch gap-0">
          {turns.map((turn, idx) => {
            const status = getTurnStatus(turn);
            const color = getStateColor(turn.node_name);
            const isSelected = idx === selectedTurnIdx;
            const next = turns[idx + 1];
            const label = next ? edgeLabel(next) : '';

            return (
              <React.Fragment key={turn.id}>
                <button
                  type="button"
                  onClick={() => setSelectedTurnIdx(idx)}
                  className={`flex w-48 flex-shrink-0 flex-col rounded-xl border bg-white text-left shadow-sm transition hover:shadow-md focus:outline-none ${
                    isSelected
                      ? 'border-brand-pink ring-2 ring-brand-pink'
                      : 'border-[#e8d8d2]'
                  }`}
                  style={{ borderTop: `4px solid ${color}` }}
                >
                  <div className="flex items-center justify-between px-3 pt-2">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-brand-muted">
                      Turn {turn.turn_number}
                    </span>
                    {statusBadge(status)}
                  </div>
                  <div className="px-3 pb-1 pt-1">
                    <div className="text-sm font-bold text-brand-navy">
                      {getStateLabel(turn.node_name)}
                    </div>
                    <div className="mt-0.5 truncate text-xs text-brand-muted">
                      {nodeSubLabel(turn)}
                    </div>
                  </div>
                  <div className="flex items-center justify-between border-t border-[#f5e9e4] px-3 py-1.5 text-[10px] text-brand-muted">
                    <span>{turn.total_latency_ms ?? '?'}ms</span>
                    {(turn.tools_called?.length || 0) > 0 && (
                      <span className="rounded-full bg-brand-peach/40 px-1.5 py-0.5 text-brand-navy">
                        {turn.tools_called.length} tool
                        {turn.tools_called.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </button>

                {next && (
                  <div className="flex w-16 flex-shrink-0 flex-col items-center justify-center px-1">
                    <ArrowRight className="h-5 w-5 text-brand-muted" />
                    {label && (
                      <span className="mt-1 max-w-full truncate text-center text-[9px] font-medium text-brand-pink">
                        {label}
                      </span>
                    )}
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Hint */}
      {selectedTurnIdx === null && (
        <div className="rounded-lg border border-dashed border-brand-cream bg-[#fdf5f2] px-4 py-3 text-xs text-brand-muted">
          Select a node above (or a turn in the bottom strip) to open its layer
          detail.
        </div>
      )}
    </div>
  );
}
