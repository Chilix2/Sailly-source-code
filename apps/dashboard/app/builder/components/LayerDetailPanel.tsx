'use client';

import React from 'react';
import { Workflow, Gauge, AlertTriangle, ChevronRight } from 'lucide-react';
import { useCallTurns } from '@/lib/api/debugger-client';
import { MOCK_CALL_TURNS } from '@/lib/api/mock-data';
import { useDebuggerStore, LayerNumber } from '@/lib/store/debugger-store';
import { TurnRow } from '@/types/sailly-debugger';

interface LayerItem {
  key: string;
  label: string;
  preview: string;
  value: unknown;
}

function toCode(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function preview(value: unknown, empty = '—'): string {
  if (value === null || value === undefined || value === '') return empty;
  if (Array.isArray(value)) return value.length ? value.join(', ') : empty;
  if (typeof value === 'object') {
    const keys = Object.keys(value as Record<string, unknown>);
    return keys.length ? `${keys.length} field${keys.length > 1 ? 's' : ''}` : empty;
  }
  if (typeof value === 'string' && value.length > 40) return value.slice(0, 40) + '…';
  return String(value);
}

function buildLayerItems(turn: TurnRow): Record<LayerNumber, LayerItem[]> {
  const l1 = turn.layer1_decision;
  const l3 = turn.layer3_changes;

  return {
    1: [
      { key: 'fsm_node', label: 'FSM node', preview: preview(turn.node_name || l1?.node), value: turn.node_name || l1?.node || null },
      { key: 'state_hash', label: 'State hash', preview: preview(l1?.state_hash, 'not recorded'), value: l1?.state_hash ?? null },
      { key: 'forced_tools', label: 'Forced tools', preview: preview(l1?.forced_tools, 'none'), value: l1?.forced_tools ?? [] },
      { key: 'validators', label: 'Validators', preview: preview(l1?.validators_run, 'none'), value: l1?.validators_run ?? [] },
      { key: 'layer1_decision', label: 'Raw Layer 1 decision', preview: preview(l1), value: l1 ?? null },
    ],
    2: [
      { key: 'llm_latency_ms', label: 'LLM latency (ms)', preview: preview(turn.llm_latency_ms), value: turn.llm_latency_ms ?? null },
      { key: 'layer2_raw_output', label: 'Raw model output', preview: preview(turn.layer2_raw_output, 'not recorded'), value: turn.layer2_raw_output ?? null },
      { key: 'stage1_clean_text', label: 'Stage 1 clean text', preview: preview(turn.stage1_clean_text, 'not recorded'), value: turn.stage1_clean_text ?? null },
      { key: 'stage2_clean_text', label: 'Stage 2 clean text', preview: preview(turn.stage2_clean_text, 'not recorded'), value: turn.stage2_clean_text ?? null },
      { key: 'stage3_text', label: 'Final stage text', preview: preview(turn.stage3_text, 'not recorded'), value: turn.stage3_text ?? null },
    ],
    3: [
      { key: 'warnings', label: 'Warnings', preview: preview(l3?.warnings, 'none'), value: l3?.warnings ?? [] },
      { key: 'text_changed', label: 'Text changed', preview: l3?.text_changed ? 'yes' : 'no', value: !!l3?.text_changed },
      { key: 'tools_changed', label: 'Tools changed', preview: l3?.tools_changed ? 'yes' : 'no', value: !!l3?.tools_changed },
      { key: 'tools_called', label: 'Tools called', preview: preview(turn.tools_called, 'none'), value: turn.tools_called ?? [] },
      { key: 'tts_situation', label: 'TTS situation', preview: preview(turn.tts_situation, 'not recorded'), value: turn.tts_situation ?? null },
      { key: 'tts_mood', label: 'TTS mood', preview: preview(turn.tts_mood, 'not recorded'), value: turn.tts_mood ?? null },
      { key: 'tts_suppressed_reason', label: 'TTS suppressed', preview: preview(turn.tts_suppressed_reason, 'no'), value: turn.tts_suppressed_reason ?? null },
      { key: 'layer3_changes', label: 'Raw Layer 3 changes', preview: preview(l3), value: l3 ?? null },
    ],
  };
}

const LAYER_META: Record<LayerNumber, { title: string; subtitle: string; icon: React.ReactNode }> = {
  1: { title: 'Layer 1: Orchestrator', subtitle: 'FSM state, forced commits, validators', icon: <Workflow size={15} /> },
  2: { title: 'Layer 2: LLM', subtitle: 'Raw model response and text pipeline', icon: <Gauge size={15} /> },
  3: { title: 'Layer 3: Policy', subtitle: 'Warnings, tool changes, TTS guardrails', icon: <AlertTriangle size={15} /> },
};

export function LayerDetailPanel({ callSid }: { callSid: string }) {
  const useMock = process.env.NEXT_PUBLIC_USE_MOCK === 'true';
  const { selectedTenantId, selectedTurnIdx, inspectedItem, setInspectedItem } =
    useDebuggerStore();

  const { data: turnsData } = useMock
    ? { data: MOCK_CALL_TURNS[callSid as keyof typeof MOCK_CALL_TURNS] }
    : useCallTurns(callSid, selectedTenantId);

  const turns = turnsData?.turns || [];
  const turnIdx = selectedTurnIdx ?? 0;
  const turn = turns[turnIdx];

  if (!turn) {
    return (
      <div className="p-4 text-sm text-brand-muted">
        Select a node in the flow to inspect its layers.
      </div>
    );
  }

  const items = buildLayerItems(turn);
  const layers: LayerNumber[] = [1, 2, 3];

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[#fdf5f2]">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-widest text-brand-muted">
          Layers · selected node
        </div>
        <div className="mt-1 text-sm font-bold text-brand-navy">
          Turn {turn.turn_number}
        </div>
        <p className="mt-1 text-xs text-brand-muted">
          Click any field to open its raw value, code, or configuration on the
          right.
        </p>
      </div>

      {layers.map((layer) => {
        const meta = LAYER_META[layer];
        return (
          <section
            key={layer}
            className="rounded-xl border border-[#e8d8d2] bg-white shadow-sm"
          >
            <div className="flex items-start gap-2 border-b border-[#f5e9e4] px-3 py-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-cream text-brand-pink">
                {meta.icon}
              </span>
              <div className="min-w-0">
                <h3 className="text-xs font-bold text-brand-navy">{meta.title}</h3>
                <p className="text-[10px] text-brand-muted">{meta.subtitle}</p>
              </div>
            </div>
            <div className="divide-y divide-[#f5e9e4]">
              {items[layer].map((item) => {
                const isActive =
                  inspectedItem?.layer === layer &&
                  inspectedItem?.turnIdx === turnIdx &&
                  inspectedItem?.key === item.key;
                return (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() =>
                      setInspectedItem(
                        isActive
                          ? null
                          : { layer, turnIdx, key: item.key, label: item.label }
                      )
                    }
                    className={`flex w-full items-center justify-between gap-2 px-3 py-2 text-left transition ${
                      isActive
                        ? 'bg-brand-pink/10 ring-1 ring-inset ring-brand-pink/40'
                        : 'hover:bg-[#fdf5f2]'
                    }`}
                  >
                    <span className="min-w-0">
                      <span className="block text-[10px] font-semibold uppercase tracking-wide text-brand-muted">
                        {item.label}
                      </span>
                      <span className="block truncate text-xs font-semibold text-brand-navy">
                        {item.preview}
                      </span>
                    </span>
                    <ChevronRight
                      className={`h-4 w-4 flex-shrink-0 ${
                        isActive ? 'text-brand-pink' : 'text-brand-muted'
                      }`}
                    />
                  </button>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
