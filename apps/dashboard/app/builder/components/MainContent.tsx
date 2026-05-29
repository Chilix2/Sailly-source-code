'use client';

import React from 'react';
import { useDebuggerStore } from '@/lib/store/debugger-store';
import { useCallTurns } from '@/lib/api/debugger-client';
import { MOCK_CALL_TURNS } from '@/lib/api/mock-data';
import { LayerTurnFocus } from './LayerTurnFocus';
import { TraceTreeView } from './TraceTreeView';
import { GanttTimelineView } from './GanttTimelineView';
import { GoldenPathView } from './GoldenPathView';
import { SteeringView } from './SteeringView';
import { RootCauseView } from './RootCauseView';

export function MainContent({ callSid }: { callSid: string }) {
  const { currentView, selectedTenantId, selectedTurnIdx, wholeCallMode } =
    useDebuggerStore();
  const useMock = process.env.NEXT_PUBLIC_USE_MOCK === 'true';

  const { data: turnsData } = useMock
    ? { data: MOCK_CALL_TURNS[callSid as keyof typeof MOCK_CALL_TURNS] }
    : useCallTurns(callSid, selectedTenantId);

  const turns = turnsData?.turns || [];

  // Scope analytical views to the selected turn unless whole-call mode is on.
  const scopedTurns = React.useMemo(() => {
    if (wholeCallMode) return turns;
    if (turns.length === 0) return turns;
    const idx = selectedTurnIdx ?? 0;
    return turns[idx] ? [turns[idx]] : turns.slice(0, 1);
  }, [turns, wholeCallMode, selectedTurnIdx]);

  const scopeLabel = wholeCallMode
    ? `Whole call · ${turns.length} turns`
    : `Showing Turn ${(selectedTurnIdx ?? 0) + 1}`;

  return (
    <div className="flex-1 overflow-auto bg-gradient-to-br from-slate-50 via-white to-slate-100">
      {currentView === 'fsm-flow' && <LayerTurnFocus callSid={callSid} />}

      {currentView === 'tree' && (
        <ScopedView label={scopeLabel}>
          <TraceTreeView turns={scopedTurns} />
        </ScopedView>
      )}

      {currentView === 'timeline' && (
        <ScopedView label={scopeLabel}>
          <GanttTimelineView turns={scopedTurns} />
        </ScopedView>
      )}

      {currentView === 'golden' && (
        <GoldenPathView
          calls={[{ callSid, turns }]}
          goldenCalls={[{ callSid, turns }]}
        />
      )}

      {currentView === 'steering' && <SteeringView />}

      {currentView === 'root-cause' && (
        <ScopedView label={scopeLabel}>
          <RootCauseView turns={scopedTurns} />
        </ScopedView>
      )}
    </div>
  );
}

function ScopedView({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="border-b border-brand-cream bg-white/60 px-6 py-2 text-[11px] font-medium uppercase tracking-wide text-brand-muted">
        {label}
        <span className="ml-2 normal-case text-brand-muted/80">
          (toggle &ldquo;Whole call&rdquo; in the header to see every turn)
        </span>
      </div>
      {children}
    </div>
  );
}
