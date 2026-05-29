'use client';

import React, { useMemo } from 'react';
import { useCallTurns } from '@/lib/api/debugger-client';
import { MOCK_CALL_TURNS } from '@/lib/api/mock-data';
import { useDebuggerStore } from '@/lib/store/debugger-store';
import { AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';

export function TurnStrip({ callSid }: { callSid: string }) {
  const useMock = process.env.NEXT_PUBLIC_USE_MOCK === 'true';
  const { selectedTenantId, selectedTurnIdx, setSelectedTurnIdx } =
    useDebuggerStore();

  const { data: turnsData } = useMock
    ? { data: MOCK_CALL_TURNS[callSid as keyof typeof MOCK_CALL_TURNS] }
    : useCallTurns(callSid, selectedTenantId);

  const turns = turnsData?.turns || [];

  const getTurnStatus = (turn: (typeof turns)[0]) => {
    if (turn.layer3_changes?.warnings && turn.layer3_changes.warnings.length > 0) {
      return 'warning';
    }
    if (
      turn.layer1_decision?.validators_run?.some((v) => v.status === 'failed')
    ) {
      return 'error';
    }
    if (turn.tts_suppressed_reason) {
      return 'error';
    }
    return 'success';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-3 h-3" />;
      case 'warning':
        return <AlertTriangle className="w-3 h-3" />;
      case 'error':
        return <AlertCircle className="w-3 h-3" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-brand-peach hover:bg-brand-peach/80 text-brand-navy';
      case 'warning':
        return 'bg-yellow-100 hover:bg-yellow-200 text-orange-700';
      case 'error':
        return 'bg-red-100 hover:bg-red-200 text-red-700';
      default:
        return 'bg-slate-100 text-slate-600';
    }
  };

  return (
    <div className="flex h-full w-full items-center gap-3 overflow-x-auto bg-white px-5 py-3">
      <div className="sticky left-0 z-10 flex h-full items-center bg-white pr-3">
        <span className="text-xs text-brand-muted flex-shrink-0 font-semibold uppercase tracking-wide">
          Turns
        </span>
      </div>
      <div className="flex min-w-max gap-2">
        {turns.map((turn) => {
          const status = getTurnStatus(turn);
          return (
            <button
              key={turn.id}
              onClick={() => setSelectedTurnIdx(turn.turn_number - 1)}
              className={`flex-shrink-0 px-3 py-2 rounded-lg text-xs font-medium transition flex items-center gap-2 ${
                selectedTurnIdx === turn.turn_number - 1
                  ? 'ring-2 ring-brand-pink ' + getStatusColor(status)
                  : getStatusColor(status)
              }`}
            >
              {getStatusIcon(status)}
              <span>T{turn.turn_number}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
