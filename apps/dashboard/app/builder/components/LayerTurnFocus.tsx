'use client';

import React from 'react';
import { ChevronRight } from 'lucide-react';
import { useCallTurns } from '@/lib/api/debugger-client';
import { MOCK_CALL_TURNS } from '@/lib/api/mock-data';
import { useDebuggerStore, LayerNumber } from '@/lib/store/debugger-store';
import { buildLayerFields, LAYER_META } from '@/lib/builder/layer-fields';

export function LayerTurnFocus({ callSid }: { callSid: string }) {
  const useMock = process.env.NEXT_PUBLIC_USE_MOCK === 'true';
  const { selectedTenantId, selectedTurnIdx, selectedLayer, inspectedItem, setInspectedItem } =
    useDebuggerStore();

  const { data: turnsData } = useMock
    ? { data: MOCK_CALL_TURNS[callSid as keyof typeof MOCK_CALL_TURNS] }
    : useCallTurns(callSid, selectedTenantId);

  const turns = turnsData?.turns || [];
  const turnIdx = selectedTurnIdx ?? 0;
  const turn = turns[turnIdx];
  const layer: LayerNumber = selectedLayer ?? 1;

  if (!turn) {
    return (
      <div className="p-6 text-sm text-brand-muted">
        No turn data available for this call yet. Select a turn in the bottom strip.
      </div>
    );
  }

  const meta = LAYER_META[layer];
  const fields = buildLayerFields(turn)[layer];

  return (
    <div className="flex flex-col gap-4 p-6">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-widest text-brand-muted">
          {meta.title} · Turn {turn.turn_number}
        </div>
        <h2 className="mt-1 text-sm font-semibold text-brand-navy">{meta.subtitle}</h2>
        <p className="mt-1 text-xs text-brand-muted">
          Everything that fired in this layer on this turn. Click a field to inspect
          its value on the right.
        </p>
      </div>

      <div className="overflow-hidden rounded-xl border border-[#e8d8d2] bg-white shadow-sm">
        <div className="divide-y divide-[#f5e9e4]">
          {fields.map((field) => {
            const isActive =
              inspectedItem?.layer === layer &&
              inspectedItem?.turnIdx === turnIdx &&
              inspectedItem?.key === field.key;
            const untracked = !field.tracked;
            return (
              <button
                key={field.key}
                type="button"
                onClick={() =>
                  setInspectedItem(
                    isActive
                      ? null
                      : { layer, turnIdx, key: field.key, label: field.label }
                  )
                }
                className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition ${
                  isActive
                    ? 'bg-brand-pink/10 ring-1 ring-inset ring-brand-pink/40'
                    : 'hover:bg-[#fdf5f2]'
                }`}
              >
                <span className="min-w-0">
                  <span className="block text-[10px] font-semibold uppercase tracking-wide text-brand-muted">
                    {field.label}
                  </span>
                  <span
                    className={`mt-0.5 block truncate text-sm font-semibold ${
                      untracked ? 'italic text-brand-muted' : 'text-brand-navy'
                    } ${field.kind === 'mono' ? 'font-mono text-xs' : ''}`}
                  >
                    {field.preview}
                  </span>
                </span>
                <span className="flex flex-shrink-0 items-center gap-2">
                  {untracked && (
                    <span className="rounded-full border border-brand-cream bg-[#fdf5f2] px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide text-brand-muted">
                      not tracked
                    </span>
                  )}
                  <ChevronRight
                    className={`h-4 w-4 ${isActive ? 'text-brand-pink' : 'text-brand-muted'}`}
                  />
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
