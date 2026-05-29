'use client';

import React, { useState } from 'react';
import { Copy, Code2, Info } from 'lucide-react';
import { useCallTurns } from '@/lib/api/debugger-client';
import { MOCK_CALL_TURNS } from '@/lib/api/mock-data';
import { useDebuggerStore } from '@/lib/store/debugger-store';
import { findField, toCode, LayerField } from '@/lib/builder/layer-fields';
import { ValidatorRun } from '@/types/sailly-debugger';

export function InspectedDetailPanel({ callSid }: { callSid: string }) {
  const useMock = process.env.NEXT_PUBLIC_USE_MOCK === 'true';
  const { selectedTenantId, inspectedItem } = useDebuggerStore();
  const [showRaw, setShowRaw] = useState(false);

  const { data: turnsData } = useMock
    ? { data: MOCK_CALL_TURNS[callSid as keyof typeof MOCK_CALL_TURNS] }
    : useCallTurns(callSid, selectedTenantId);

  const turns = turnsData?.turns || [];

  if (!inspectedItem) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <Code2 className="h-6 w-6 text-brand-muted" />
        <p className="text-sm font-medium text-brand-navy">Nothing inspected</p>
        <p className="max-w-xs text-xs text-brand-muted">
          Click a field in the middle to see its value here.
        </p>
      </div>
    );
  }

  const turn = turns[inspectedItem.turnIdx];
  const field = turn ? findField(turn, inspectedItem.layer, inspectedItem.key) : undefined;
  const code = field ? toCode(field.value) : 'null';

  const copy = () => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(code).catch(() => undefined);
    }
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-start justify-between gap-2 border-b border-brand-cream p-4">
        <div className="min-w-0">
          <div className="text-[10px] font-bold uppercase tracking-widest text-brand-muted">
            Layer {inspectedItem.layer} · Turn {inspectedItem.turnIdx + 1}
          </div>
          <h3 className="truncate text-sm font-semibold text-brand-navy">
            {inspectedItem.label}
          </h3>
        </div>
        <div className="flex flex-shrink-0 items-center gap-1">
          {/* Pretty / Raw toggle */}
          <div className="flex overflow-hidden rounded-lg border border-brand-cream text-[11px]">
            <button
              type="button"
              onClick={() => setShowRaw(false)}
              className={`px-2 py-1 ${!showRaw ? 'bg-brand-pink text-white' : 'bg-white text-brand-muted'}`}
            >
              Pretty
            </button>
            <button
              type="button"
              onClick={() => setShowRaw(true)}
              className={`px-2 py-1 ${showRaw ? 'bg-brand-pink text-white' : 'bg-white text-brand-muted'}`}
            >
              Raw
            </button>
          </div>
          <button
            type="button"
            onClick={copy}
            className="flex items-center gap-1 rounded border border-brand-cream bg-[#fdf5f2] px-2 py-1 text-[11px] text-brand-muted hover:text-brand-navy"
          >
            <Copy className="h-3 w-3" /> copy
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-auto p-4">
        {!field ? (
          <div className="text-xs text-brand-muted">Field not available for this turn.</div>
        ) : showRaw ? (
          <pre className="whitespace-pre-wrap break-words rounded-lg border border-[#e8d8d2] bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-700">
            {code}
          </pre>
        ) : (
          <PrettyValue field={field} />
        )}
      </div>
    </div>
  );
}

function NotTracked({ note }: { note?: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-brand-cream bg-[#fdf5f2] p-3 text-xs text-brand-muted">
      <Info className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
      <div>
        <span className="font-semibold text-brand-navy">Not tracked yet.</span>{' '}
        {note || 'The backend does not populate this field in the current runtime.'}
      </div>
    </div>
  );
}

function PrettyValue({ field }: { field: LayerField }) {
  const { kind, value, tracked, note } = field;

  const empty =
    value === null ||
    value === undefined ||
    value === '' ||
    (Array.isArray(value) && value.length === 0);

  if (empty && !tracked) {
    return <NotTracked note={note} />;
  }

  switch (kind) {
    case 'chips': {
      const arr = (value as string[]) || [];
      if (arr.length === 0) return <EmptyLine label="none" />;
      return (
        <div className="flex flex-wrap gap-1.5">
          {arr.map((tag) => (
            <span
              key={tag}
              className="rounded-full border border-brand-peach bg-brand-peach/30 px-2 py-0.5 text-xs font-semibold text-brand-navy"
            >
              {tag}
            </span>
          ))}
        </div>
      );
    }
    case 'validators': {
      const arr = (value as ValidatorRun[]) || [];
      if (arr.length === 0) return <EmptyLine label="none" />;
      return (
        <div className="space-y-1">
          {arr.map((v, i) => (
            <div
              key={`${v.slot}-${i}`}
              className="flex items-center justify-between rounded-lg border border-[#e8d8d2] bg-white px-3 py-1.5 text-xs"
            >
              <span className="text-brand-navy">{v.slot}</span>
              <span
                className={
                  v.status === 'verified'
                    ? 'font-semibold text-green-700'
                    : v.status === 'failed'
                      ? 'font-semibold text-red-600'
                      : 'font-semibold text-brand-muted'
                }
              >
                {v.status}
              </span>
            </div>
          ))}
        </div>
      );
    }
    case 'warnings': {
      const arr = (value as Array<{ kind: string; message: string }>) || [];
      if (arr.length === 0)
        return (
          <div className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-xs text-green-700">
            No warnings.
          </div>
        );
      return (
        <div className="space-y-1">
          {arr.map((w, i) => (
            <div
              key={`${w.kind}-${i}`}
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700"
            >
              <span className="font-semibold">{w.kind}:</span> {w.message}
            </div>
          ))}
        </div>
      );
    }
    case 'bool':
      return (
        <span
          className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${
            value ? 'bg-brand-peach/40 text-brand-navy' : 'bg-slate-100 text-brand-muted'
          }`}
        >
          {value ? 'yes' : 'no'}
        </span>
      );
    case 'number':
      return (
        <div className="text-2xl font-bold text-brand-navy">
          {value === null || value === undefined ? '—' : String(value)}
          <span className="ml-1 text-xs font-normal text-brand-muted">ms</span>
        </div>
      );
    case 'mono':
      return (
        <div className="break-all rounded-lg border border-[#e8d8d2] bg-slate-50 p-3 font-mono text-xs text-slate-700">
          {value ? String(value) : 'not recorded'}
        </div>
      );
    case 'json':
      return (
        <div className="space-y-1">
          {value && typeof value === 'object' ? (
            Object.entries(value as Record<string, unknown>).map(([k, v]) => (
              <div
                key={k}
                className="flex items-start justify-between gap-2 rounded-lg border border-[#e8d8d2] bg-white px-3 py-1.5 text-xs"
              >
                <span className="font-semibold text-brand-muted">{k}</span>
                <span className="min-w-0 truncate text-right text-brand-navy">
                  {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                </span>
              </div>
            ))
          ) : (
            <EmptyLine label="empty" />
          )}
          <p className="pt-1 text-[10px] text-brand-muted">
            Switch to Raw for the full JSON.
          </p>
        </div>
      );
    case 'text':
    default:
      return (
        <div className="whitespace-pre-wrap break-words rounded-lg border border-[#e8d8d2] bg-white p-3 text-sm leading-relaxed text-slate-700">
          {value ? String(value) : <span className="italic text-brand-muted">empty</span>}
          {note && tracked && (
            <p className="mt-2 border-t border-[#f5e9e4] pt-2 text-[10px] italic text-brand-muted">
              {note}
            </p>
          )}
        </div>
      );
  }
}

function EmptyLine({ label }: { label: string }) {
  return <div className="text-xs italic text-brand-muted">{label}</div>;
}
