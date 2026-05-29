'use client';

import React, { useState } from 'react';
import { useDebuggerStore, DebuggerView } from '@/lib/store/debugger-store';
import { useActiveCalls } from '@/lib/api/debugger-client';
import { Eye, Bug, Info } from 'lucide-react';

interface TabDef {
  id: DebuggerView;
  label: string;
  tip: string;
}

const TABS: TabDef[] = [
  {
    id: 'fsm-flow',
    label: 'Layer',
    tip: 'Focused Layer x Turn inspector. Pick a layer on the left and a turn in the bottom strip; the middle shows only what fired in that layer on that turn.',
  },
  {
    id: 'tree',
    label: 'Trace Tree',
    tip: 'Hierarchical per-stage latency breakdown (STT, Extract, LLM, Tools, TTS) for the selected turn.',
  },
  {
    id: 'timeline',
    label: 'Gantt',
    tip: 'Wall-clock timeline of pipeline stages for the selected turn, showing relative stage durations.',
  },
  {
    id: 'golden',
    label: 'Reference',
    tip: 'Scenario reference library: how each scenario should run plus prime example error-free calls.',
  },
  {
    id: 'steering',
    label: 'Steering',
    tip: 'Reset, fork, and replay controls for a call (requires backend endpoints; currently disabled).',
  },
  {
    id: 'root-cause',
    label: 'Root Cause',
    tip: 'Auto-detected anomalies (high latency, validation failures, FSM loops) for the selected turn or whole call.',
  },
];

export function DebuggerHeader() {
  const {
    selectedTenantId,
    currentView,
    setCurrentView,
    selectedTurnIdx,
    selectedLayer,
    wholeCallMode,
    setWholeCallMode,
    inspectedItem,
  } = useDebuggerStore();
  const { data: activeCalls } = useActiveCalls();

  const [tip, setTip] = useState<{ text: string; x: number; y: number } | null>(
    null
  );

  const handleMove = (e: React.MouseEvent, text: string) => {
    setTip({ text, x: e.clientX, y: e.clientY });
  };

  const turnLabel =
    selectedTurnIdx !== null ? `Turn ${selectedTurnIdx + 1}` : 'No turn';
  const layerLabel = selectedLayer ? `Layer ${selectedLayer}` : 'all layers';

  return (
    <div className="border-b border-brand-cream bg-white px-6 py-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Bug className="w-6 h-6 text-brand-pink" />
          <h1 className="text-xl font-semibold text-brand-navy">Sailly Debugger</h1>
          <div className="group relative">
            <button
              type="button"
              aria-label="What does the debugger show?"
              className="flex h-7 w-7 items-center justify-center rounded-full border border-brand-cream bg-[#fdf5f2] text-brand-muted transition hover:border-brand-pink/50 hover:text-brand-pink focus:outline-none focus:ring-2 focus:ring-brand-pink/30"
            >
              <Info className="h-4 w-4" />
            </button>
            <div className="pointer-events-none absolute left-0 top-9 z-40 hidden w-80 rounded-xl border border-[#e8d8d2] bg-white p-4 text-xs leading-relaxed text-slate-700 shadow-xl group-hover:block group-focus-within:block">
              <div className="mb-2 font-bold text-brand-navy">What this shows</div>
              <p>
                Pick a call, then walk the flow node by node. Each node is a turn:
                click it to inspect Layer 1 (deterministic FSM decision and forced
                tools), Layer 2 (LLM output and text pipeline), and Layer 3 (policy
                changes, warnings, tools, timings, and root-cause flags).
              </p>
            </div>
          </div>
          <span className="text-sm text-brand-muted">
            {selectedTenantId || 'No tenant'}
          </span>
          {activeCalls && activeCalls.count > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-brand-peach text-brand-navy rounded text-xs font-medium">
              <span className="w-2 h-2 bg-brand-salmon rounded-full animate-pulse" />
              {activeCalls.count} live
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* Dynamic selection context */}
          <div className="flex items-center gap-2 text-xs text-brand-muted">
            <Eye className="w-4 h-4" />
            <span className="font-medium text-brand-navy">{turnLabel}</span>
            <span>·</span>
            <span>{layerLabel}</span>
          </div>
          {/* Inspected-field chip */}
          <span
            className={`rounded-full border px-2.5 py-1 text-xs font-medium ${
              inspectedItem
                ? 'border-brand-pink/40 bg-brand-pink/10 text-brand-pink'
                : 'border-brand-cream bg-[#fdf5f2] text-brand-muted'
            }`}
            title="Field currently inspected on the right"
          >
            {inspectedItem
              ? `Layer ${inspectedItem.layer} · ${inspectedItem.label}`
              : 'Nothing inspected'}
          </span>
          {/* Whole-call / single-turn toggle */}
          <button
            type="button"
            onClick={() => setWholeCallMode(!wholeCallMode)}
            className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
              wholeCallMode
                ? 'border-brand-pink bg-brand-pink/10 text-brand-pink'
                : 'border-brand-cream bg-[#fdf5f2] text-brand-muted hover:text-brand-navy'
            }`}
          >
            {wholeCallMode ? 'Whole call' : 'Single turn'}
          </button>
        </div>
      </div>

      {/* View tabs */}
      <div className="flex gap-2 flex-wrap">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setCurrentView(tab.id)}
            onMouseMove={(e) => handleMove(e, tab.tip)}
            onMouseLeave={() => setTip(null)}
            className={`px-3 py-2 text-sm font-medium rounded-lg transition ${
              currentView === tab.id
                ? 'bg-brand-pink text-white'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Cursor-following tooltip bubble */}
      {tip && (
        <div
          className="pointer-events-none fixed z-50 max-w-xs rounded-lg border border-[#e8d8d2] bg-white px-3 py-2 text-xs leading-relaxed text-slate-700 shadow-xl"
          style={{ left: tip.x + 14, top: tip.y + 14 }}
        >
          {tip.text}
        </div>
      )}
    </div>
  );
}
