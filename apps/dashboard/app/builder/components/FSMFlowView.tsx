'use client';

import React from 'react';
import { useCallTurns } from '@/lib/api/debugger-client';
import { MOCK_CALL_TURNS } from '@/lib/api/mock-data';
import { useDebuggerStore } from '@/lib/store/debugger-store';
import { getStateColor, getStateLabel, FSM_STATES } from '@/lib/fsm/states';
import { ArrowRight } from 'lucide-react';

export function FSMFlowView({ callSid }: { callSid: string }) {
  const useMock = process.env.NEXT_PUBLIC_USE_MOCK === 'true';
  const { selectedTenantId, selectedTurnIdx } = useDebuggerStore();

  const { data: turnsData } = useMock
    ? { data: MOCK_CALL_TURNS[callSid as keyof typeof MOCK_CALL_TURNS] }
    : useCallTurns(callSid, selectedTenantId);

  const turns = turnsData?.turns || [];
  const turn = selectedTurnIdx !== null ? turns[selectedTurnIdx] : turns[0];

  if (!turn) {
    return <div className="p-6 text-brand-muted">No turn data</div>;
  }

  const currentNode = turn.node_name || turn.layer1_decision?.node;
  const forcedTools = turn.layer1_decision?.forced_tools || [];
  const validators = turn.layer1_decision?.validators_run || [];
  const warnings = turn.layer3_changes?.warnings || [];

  return (
    <div className="p-6 overflow-auto flex flex-col gap-6">
      {/* FSM Path */}
      <div className="bg-slate-50 p-4 rounded border border-brand-cream">
        <h3 className="text-sm font-semibold mb-4 text-brand-navy">FSM Path (All Turns)</h3>
        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          {turns.map((t, idx) => {
            const nodeColor = getStateColor(t.node_name);
            const isSelected = idx === selectedTurnIdx;
            const nodeLabel = getStateLabel(t.node_name);

            return (
              <React.Fragment key={t.id}>
                <div
                  className={`px-3 py-2 rounded text-xs font-medium whitespace-nowrap transition ${
                    isSelected
                      ? 'ring-2 ring-brand-pink'
                      : 'hover:bg-slate-100 cursor-pointer'
                  }`}
                  style={{
                    backgroundColor: nodeColor + '40',
                    borderLeft: `3px solid ${nodeColor}`,
                  }}
                >
                  T{t.turn_number}: {nodeLabel}
                </div>
                {idx < turns.length - 1 && (
                  <ArrowRight className="w-4 h-4 text-brand-muted flex-shrink-0" />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Current turn: 3-layer flow */}
      <div className="space-y-4">
        {/* Layer 1 */}
        <div className="border border-brand-cream rounded overflow-hidden">
          <div
            className="px-4 py-3 font-semibold text-sm text-brand-navy bg-brand-cream"
            style={{ borderLeft: `4px solid ${getStateColor(currentNode)}` }}
          >
            Layer 1: Orchestrator
          </div>
          <div className="p-4 bg-slate-50 space-y-3">
            <div>
              <span className="text-xs text-brand-muted">FSM State:</span>
              <div className="mt-1 inline-block px-3 py-1 bg-white border border-brand-cream rounded-lg text-sm font-mono text-brand-navy">
                {currentNode}
              </div>
            </div>

            {forcedTools.length > 0 && (
              <div>
                <span className="text-xs text-brand-muted block mb-2">Forced Tools:</span>
                <div className="flex flex-wrap gap-2">
                  {forcedTools.map((tool) => (
                    <span
                      key={tool}
                      className="px-2 py-1 bg-yellow-50 text-orange-700 border border-yellow-200 rounded-lg text-xs font-medium"
                    >
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {validators.length > 0 && (
              <div>
                <span className="text-xs text-brand-muted block mb-2">Validators:</span>
                <div className="space-y-1">
                  {validators.map((v) => (
                    <div
                      key={v.slot}
                      className="text-xs px-2 py-1 bg-white border border-brand-cream rounded-lg flex justify-between text-slate-700"
                    >
                      <span>{v.slot}</span>
                      <span
                        className={
                          v.status === 'verified' ? 'text-green-700' : 'text-red-600'
                        }
                      >
                        {v.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {turn.layer1_decision?.state_hash && (
              <div className="pt-2 border-t border-brand-cream">
                <span className="text-xs text-brand-muted">State Hash:</span>
                <div className="text-xs font-mono text-slate-700 mt-1 truncate">
                  {turn.layer1_decision.state_hash}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Arrow */}
        <div className="flex justify-center">
          <ArrowRight className="w-6 h-6 text-brand-muted rotate-90" />
        </div>

        {/* Layer 2 */}
        <div className="border border-[#e8d8d2] rounded-xl overflow-hidden bg-white shadow-sm">
          <div className="px-4 py-3 bg-blue-50 text-blue-800 font-semibold text-sm border-b border-blue-100">
            Layer 2: LLM
          </div>
          <div className="p-4 bg-slate-50 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-brand-muted">Latency:</span>
              <span className="text-blue-700 font-mono font-semibold">
                {turn.llm_latency_ms || '?'}ms
              </span>
            </div>
            {turn.layer2_raw_output && (
              <div>
                <span className="text-xs text-brand-muted block mb-1">Output (preview):</span>
                <div className="text-xs bg-white p-2 rounded text-slate-700 max-h-24 overflow-y-auto break-words">
                  {turn.layer2_raw_output.slice(0, 300)}
                  {turn.layer2_raw_output.length > 300 && '...'}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Arrow */}
        <div className="flex justify-center">
          <ArrowRight className="w-6 h-6 text-brand-muted rotate-90" />
        </div>

        {/* Layer 3 */}
        <div className="border border-[#e8d8d2] rounded-xl overflow-hidden bg-white shadow-sm">
          <div className="px-4 py-3 bg-brand-peach/30 text-brand-navy font-semibold text-sm border-b border-brand-peach">
            Layer 3: Policy
          </div>
          <div className="p-4 bg-slate-50 space-y-2">
            {warnings.length > 0 ? (
              <div className="bg-red-50 border border-red-200 rounded-lg p-2 space-y-1">
                {warnings.map((w, i) => (
                  <div key={i} className="text-xs text-red-700">
                    <span className="font-semibold">{w.kind}:</span> {w.message}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-green-700">✓ No warnings</div>
            )}

            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-brand-muted">Text changed:</span>
                <span className="text-slate-700">
                  {turn.layer3_changes?.text_changed ? 'yes' : 'no'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-brand-muted">Tools changed:</span>
                <span className="text-slate-700">
                  {turn.layer3_changes?.tools_changed ? 'yes' : 'no'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Arrow */}
        <div className="flex justify-center">
          <ArrowRight className="w-6 h-6 text-brand-muted rotate-90" />
        </div>

        {/* Tools & TTS */}
        <div className="grid grid-cols-2 gap-4">
          {/* Tools */}
          <div className="border border-brand-cream rounded overflow-hidden">
            <div className="px-4 py-3 bg-brand-cream text-brand-navy font-semibold text-sm border-b border-brand-cream">
              Tools
            </div>
            <div className="p-4 bg-slate-50">
              {turn.tools_called && turn.tools_called.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {turn.tools_called.map((tool) => (
                    <span
                      key={tool}
                      className="px-2 py-1 bg-brand-peach text-brand-navy rounded text-xs"
                    >
                      {tool}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-brand-muted">No tools</div>
              )}
            </div>
          </div>

          {/* TTS */}
          <div className="border border-brand-cream rounded overflow-hidden">
            <div className="px-4 py-3 bg-brand-cream text-brand-navy font-semibold text-sm border-b border-brand-cream">
              TTS
            </div>
            <div className="p-4 bg-slate-50 space-y-1 text-xs">
              {turn.tts_situation && (
                <div className="flex justify-between">
                  <span className="text-brand-muted">Situation:</span>
                  <span className="text-slate-700">{turn.tts_situation}</span>
                </div>
              )}
              {turn.tts_mood && (
                <div className="flex justify-between">
                  <span className="text-brand-muted">Mood:</span>
                  <span className="text-slate-700">{turn.tts_mood}</span>
                </div>
              )}
              {turn.tts_suppressed_reason && (
                <div className="flex justify-between text-red-600">
                  <span>Suppressed:</span>
                  <span>{turn.tts_suppressed_reason}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
