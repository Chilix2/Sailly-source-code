'use client';

import React, { useMemo } from 'react';
import { useCallTurns } from '@/lib/api/debugger-client';
import { MOCK_CALL_TURNS } from '@/lib/api/mock-data';
import { useDebuggerStore } from '@/lib/store/debugger-store';
import { ChevronDown, Download, Copy } from 'lucide-react';

export function TurnInspector({ callSid }: { callSid: string }) {
  const useMock = process.env.NEXT_PUBLIC_USE_MOCK === 'true';
  const { selectedTenantId, selectedTurnIdx } = useDebuggerStore();

  const { data: turnsData } = useMock
    ? { data: MOCK_CALL_TURNS[callSid as keyof typeof MOCK_CALL_TURNS] }
    : useCallTurns(callSid, selectedTenantId);

  const turns = turnsData?.turns || [];
  const turn = selectedTurnIdx !== null ? turns[selectedTurnIdx] : null;

  const [expandedSections, setExpandedSections] = React.useState<
    Record<string, boolean>
  >({
    transcript: true,
    layer1: false,
    layer2: false,
    layer3: false,
    tools: false,
    timings: false,
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const handleExportJSON = () => {
    if (!turn) return;
    const json = JSON.stringify(turn, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `turn-${turn.turn_number}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!turn) {
    return (
      <div className="flex items-center justify-center h-full text-brand-muted text-sm">
        No turn selected
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto flex flex-col bg-white">
      {/* Header with turn info and export */}
      <div className="border-b border-brand-cream bg-slate-50 p-4 flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-sm text-brand-navy">Turn {turn.turn_number}</h3>
          <div className="flex gap-2">
            <button
              onClick={handleExportJSON}
              className="p-2 hover:bg-brand-cream rounded-lg transition"
              title="Export as JSON"
            >
              <Download className="w-4 h-4 text-brand-muted" />
            </button>
          </div>
        </div>
        <p className="text-xs text-brand-muted">
          {new Date(turn.created_at).toLocaleTimeString()}
        </p>
      </div>

      {/* Collapsible sections */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {/* Transcript */}
        <Section
          title="Transcript"
          expanded={expandedSections.transcript}
          onToggle={() => toggleSection('transcript')}
        >
          <div className="space-y-3 text-xs">
            {turn.user_text && (
              <div>
                <span className="font-semibold text-blue-600">User:</span>
                <p className="text-slate-700 mt-1 break-words">
                  {turn.user_text}
                </p>
              </div>
            )}
            {turn.bot_text && (
              <div>
                <span className="font-semibold text-brand-salmon">Bot:</span>
                <p className="text-slate-700 mt-1 break-words">
                  {turn.bot_text}
                </p>
              </div>
            )}
          </div>
        </Section>

        {/* Layer 1 */}
        <Section
          title="Layer 1: Orchestrator"
          expanded={expandedSections.layer1}
          onToggle={() => toggleSection('layer1')}
        >
          <div className="space-y-2 text-xs font-mono">
            {turn.node_name && (
              <div className="bg-slate-50 p-2 rounded border border-brand-cream">
                <span className="text-brand-muted">node:</span>{' '}
                <span className="text-brand-pink font-semibold">{turn.node_name}</span>
              </div>
            )}
            {turn.layer1_decision?.forced_tools && (
              <div className="bg-slate-50 p-2 rounded border border-brand-cream">
                <span className="text-brand-muted">forced_tools:</span>{' '}
                <span className="text-orange-600">
                  {turn.layer1_decision.forced_tools.join(', ') || '[]'}
                </span>
              </div>
            )}
            {turn.layer1_decision?.validators_run &&
              turn.layer1_decision.validators_run.length > 0 && (
                <div className="bg-slate-50 p-2 rounded border border-brand-cream">
                  <div className="text-brand-muted mb-1">validators_run:</div>
                  <div className="space-y-1 pl-2">
                    {turn.layer1_decision.validators_run.map((v, i) => (
                      <div key={i} className="text-slate-700">
                        {v.slot}:{' '}
                        <span
                          className={
                            v.status === 'verified'
                              ? 'text-brand-salmon'
                              : 'text-red-600'
                          }
                        >
                          {v.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
          </div>
        </Section>

        {/* Layer 2 */}
        <Section
          title="Layer 2: LLM"
          expanded={expandedSections.layer2}
          onToggle={() => toggleSection('layer2')}
        >
          <div className="space-y-2 text-xs">
            <div className="bg-slate-50 p-2 rounded border border-brand-cream flex justify-between">
              <span className="text-brand-muted">latency:</span>
              <span className="text-blue-600 font-semibold">{turn.llm_latency_ms}ms</span>
            </div>
            {turn.layer2_raw_output && (
              <div className="bg-slate-50 p-2 rounded border border-brand-cream text-slate-700 break-words max-h-40 overflow-y-auto">
                {turn.layer2_raw_output.slice(0, 200)}
                {turn.layer2_raw_output.length > 200 && '...'}
              </div>
            )}
          </div>
        </Section>

        {/* Layer 3 */}
        <Section
          title="Layer 3: Policy"
          expanded={expandedSections.layer3}
          onToggle={() => toggleSection('layer3')}
        >
          <div className="space-y-2 text-xs">
            {turn.layer3_changes?.warnings && turn.layer3_changes.warnings.length > 0 && (
              <div className="bg-red-50 border border-red-200 p-2 rounded">
                {turn.layer3_changes.warnings.map((w, i) => (
                  <div key={i} className="text-red-700">
                    <span className="font-semibold">{w.kind}:</span> {w.message}
                  </div>
                ))}
              </div>
            )}
            <div className="bg-slate-50 p-2 rounded border border-brand-cream flex justify-between">
              <span className="text-brand-muted">text_changed:</span>
              <span className="text-slate-700">
                {turn.layer3_changes?.text_changed ? 'yes' : 'no'}
              </span>
            </div>
            <div className="bg-slate-50 p-2 rounded border border-brand-cream flex justify-between">
              <span className="text-brand-muted">tools_changed:</span>
              <span className="text-slate-700">
                {turn.layer3_changes?.tools_changed ? 'yes' : 'no'}
              </span>
            </div>
          </div>
        </Section>

        {/* Tools */}
        {turn.tools_called && turn.tools_called.length > 0 && (
          <Section
            title="Tools Called"
            expanded={expandedSections.tools}
            onToggle={() => toggleSection('tools')}
          >
            <div className="flex flex-wrap gap-2">
              {turn.tools_called.map((tool) => (
                <span
                  key={tool}
                  className="px-2 py-1 bg-brand-peach text-brand-navy rounded-lg text-xs font-medium"
                >
                  {tool}
                </span>
              ))}
            </div>
          </Section>
        )}

        {/* Timings */}
        <Section
          title="Timings"
          expanded={expandedSections.timings}
          onToggle={() => toggleSection('timings')}
        >
          <div className="space-y-1 text-xs">
            {turn.stt_latency_ms && (
              <div className="flex justify-between">
                <span className="text-brand-muted">STT:</span>
                <span className="text-slate-700">{turn.stt_latency_ms}ms</span>
              </div>
            )}
            {turn.llm_latency_ms && (
              <div className="flex justify-between">
                <span className="text-brand-muted">LLM:</span>
                <span className="text-slate-700">{turn.llm_latency_ms}ms</span>
              </div>
            )}
            {turn.tts_latency_ms && (
              <div className="flex justify-between">
                <span className="text-brand-muted">TTS:</span>
                <span className="text-slate-700">{turn.tts_latency_ms}ms</span>
              </div>
            )}
            {turn.total_latency_ms && (
              <div className="flex justify-between font-semibold">
                <span className="text-brand-navy">Total:</span>
                <span className="text-blue-600">{turn.total_latency_ms}ms</span>
              </div>
            )}
          </div>
        </Section>
      </div>
    </div>
  );
}

function Section({
  title,
  expanded,
  onToggle,
  children,
}: {
  title: string;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-brand-cream rounded-lg overflow-hidden bg-white">
      <button
        onClick={onToggle}
        className="w-full px-3 py-2 bg-slate-50 hover:bg-slate-100 transition flex items-center justify-between text-xs font-semibold text-brand-navy border-b border-brand-cream"
      >
        <span>{title}</span>
        <ChevronDown
          className={`w-4 h-4 transition text-brand-muted ${expanded ? 'rotate-180' : ''}`}
        />
      </button>
      {expanded && (
        <div className="p-3 bg-white border-t border-brand-cream">
          {children}
        </div>
      )}
    </div>
  );
}
