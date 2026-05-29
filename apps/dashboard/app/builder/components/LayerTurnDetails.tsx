'use client';

import React from 'react';
import { AlertTriangle, CheckCircle, Gauge, Workflow } from 'lucide-react';
import { useCallTurns } from '@/lib/api/debugger-client';
import { MOCK_CALL_TURNS } from '@/lib/api/mock-data';
import { useDebuggerStore } from '@/lib/store/debugger-store';

export function LayerTurnDetails({ callSid }: { callSid: string | null }) {
  const useMock = process.env.NEXT_PUBLIC_USE_MOCK === 'true';
  const { selectedTenantId, selectedTurnIdx } = useDebuggerStore();

  const apiTurns = useCallTurns(callSid || '', selectedTenantId);
  const turnsData = useMock && callSid
    ? MOCK_CALL_TURNS[callSid as keyof typeof MOCK_CALL_TURNS]
    : apiTurns.data;

  const turns = turnsData?.turns || [];
  const turn = selectedTurnIdx !== null ? turns[selectedTurnIdx] : turns[0];

  if (!callSid) {
    return (
      <div className="flex-1 p-4 text-sm text-brand-muted">
        Select a call to inspect Layer 1, Layer 2, and Layer 3 for each turn.
      </div>
    );
  }

  if (!turn) {
    return (
      <div className="flex-1 p-4 text-sm text-brand-muted">
        No turn data available for this call yet.
      </div>
    );
  }

  const forcedTools = turn.layer1_decision?.forced_tools || [];
  const validators = turn.layer1_decision?.validators_run || [];
  const warnings = turn.layer3_changes?.warnings || [];

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[#fdf5f2]">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-widest text-brand-muted">
          Selected Turn
        </div>
        <div className="mt-1 text-sm font-bold text-brand-navy">
          Turn {turn.turn_number}
        </div>
        <p className="mt-1 text-xs text-brand-muted">
          Deep-dive view for the selected turn across the deterministic FSM,
          LLM output, and policy/tool layer.
        </p>
      </div>

      <LayerCard
        title="Layer 1: Orchestrator"
        subtitle="FSM state, forced commits, validators"
        icon={<Workflow size={15} />}
      >
        <KeyValue label="FSM node" value={turn.node_name || turn.layer1_decision?.node || 'unknown'} />
        <KeyValue label="State hash" value={turn.layer1_decision?.state_hash || 'not recorded'} monospace />

        <TagGroup
          label="Forced tools"
          empty="No forced tools"
          tags={forcedTools}
          className="bg-brand-peach/30 text-brand-navy border-brand-peach"
        />

        <div>
          <div className="text-[10px] font-semibold uppercase tracking-wide text-brand-muted mb-1">
            Validators
          </div>
          {validators.length === 0 ? (
            <div className="text-xs text-brand-muted italic">No validators recorded</div>
          ) : (
            <div className="space-y-1">
              {validators.map((validator) => (
                <div
                  key={`${validator.slot}-${validator.retry}`}
                  className="flex items-center justify-between rounded-lg border border-[#e8d8d2] bg-white px-2 py-1 text-xs"
                >
                  <span className="truncate text-brand-navy">{validator.slot}</span>
                  <span
                    className={
                      validator.status === 'verified'
                        ? 'font-semibold text-green-700'
                        : 'font-semibold text-red-600'
                    }
                  >
                    {validator.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </LayerCard>

      <LayerCard
        title="Layer 2: LLM"
        subtitle="Raw model response and text pipeline"
        icon={<Gauge size={15} />}
      >
        <KeyValue label="LLM latency" value={`${turn.llm_latency_ms ?? '?'}ms`} />
        <PreviewBlock label="Raw output" value={turn.layer2_raw_output} />
        <PreviewBlock label="Stage 1 clean text" value={turn.stage1_clean_text} />
        <PreviewBlock label="Stage 2 clean text" value={turn.stage2_clean_text} />
        <PreviewBlock label="Final stage text" value={turn.stage3_text} />
      </LayerCard>

      <LayerCard
        title="Layer 3: Policy"
        subtitle="Warnings, tool changes, TTS guardrails"
        icon={<AlertTriangle size={15} />}
      >
        {warnings.length === 0 ? (
          <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-2 py-1 text-xs text-green-700">
            <CheckCircle size={13} />
            No policy warnings recorded
          </div>
        ) : (
          <div className="space-y-1">
            {warnings.map((warning, index) => (
              <div
                key={`${warning.kind}-${index}`}
                className="rounded-lg border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-700"
              >
                <span className="font-semibold">{warning.kind}:</span> {warning.message}
              </div>
            ))}
          </div>
        )}

        <KeyValue label="Text changed" value={turn.layer3_changes?.text_changed ? 'yes' : 'no'} />
        <KeyValue label="Tools changed" value={turn.layer3_changes?.tools_changed ? 'yes' : 'no'} />
        <KeyValue label="TTS situation" value={turn.tts_situation || 'not recorded'} />
        <KeyValue label="TTS mood" value={turn.tts_mood || 'not recorded'} />
        <KeyValue label="TTS suppressed" value={turn.tts_suppressed_reason || 'no'} />
        <TagGroup
          label="Tools called"
          empty="No tools called"
          tags={turn.tools_called || []}
          className="bg-brand-pink/10 text-brand-navy border-brand-pink/30"
        />
      </LayerCard>
    </div>
  );
}

function LayerCard({
  title,
  subtitle,
  icon,
  children,
}: {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-[#e8d8d2] bg-white shadow-sm">
      <div className="flex items-start gap-2 border-b border-[#f5e9e4] px-3 py-3">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-cream text-brand-pink">
          {icon}
        </span>
        <div className="min-w-0">
          <h3 className="text-xs font-bold text-brand-navy">{title}</h3>
          <p className="text-[10px] text-brand-muted">{subtitle}</p>
        </div>
      </div>
      <div className="space-y-3 px-3 py-3">{children}</div>
    </section>
  );
}

function KeyValue({
  label,
  value,
  monospace = false,
}: {
  label: string;
  value: React.ReactNode;
  monospace?: boolean;
}) {
  return (
    <div className="rounded-lg border border-[#e8d8d2] bg-[#fdf5f2] px-2 py-1.5">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-brand-muted">
        {label}
      </div>
      <div className={`mt-0.5 truncate text-xs font-semibold text-brand-navy ${monospace ? 'font-mono' : ''}`}>
        {value}
      </div>
    </div>
  );
}

function PreviewBlock({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-wide text-brand-muted mb-1">
        {label}
      </div>
      {value ? (
        <div className="max-h-24 overflow-y-auto rounded-lg border border-[#e8d8d2] bg-white p-2 text-xs leading-relaxed text-slate-700">
          {value}
        </div>
      ) : (
        <div className="text-xs text-brand-muted italic">Not recorded</div>
      )}
    </div>
  );
}

function TagGroup({
  label,
  tags,
  empty,
  className,
}: {
  label: string;
  tags: string[];
  empty: string;
  className: string;
}) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-wide text-brand-muted mb-1">
        {label}
      </div>
      {tags.length === 0 ? (
        <div className="text-xs text-brand-muted italic">{empty}</div>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <span
              key={tag}
              className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${className}`}
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
