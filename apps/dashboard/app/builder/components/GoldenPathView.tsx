'use client';

import React from 'react';
import { TurnRow } from '@/types/sailly-debugger';
import { BookOpen, Star, Sparkles } from 'lucide-react';

export interface GoldenPathViewProps {
  calls?: { callSid: string; turns: TurnRow[] }[];
  goldenCalls?: { callSid: string; turns: TurnRow[] }[];
}

const SCENARIO_PHASES: { phase: string; name: string }[] = [
  { phase: 'A', name: 'Greeting' },
  { phase: 'B', name: 'Single FAQ' },
  { phase: 'C', name: 'Multi FAQ' },
  { phase: 'D', name: 'Single order' },
  { phase: 'E', name: 'Single reservation' },
  { phase: 'F', name: 'Multi intent' },
  { phase: 'G', name: 'Transfer / callback' },
  { phase: 'H', name: 'Chaos / edge case' },
  { phase: 'I', name: 'End / wrap-up' },
];

/**
 * Reference library: how each scenario should run (golden templates) plus
 * prime example error-free calls. Empty for now - references get populated as
 * golden flows are defined and clean calls accumulate.
 */
export function GoldenPathView(_props: GoldenPathViewProps) {
  return (
    <div className="space-y-6 overflow-y-auto p-6">
      <div>
        <h2 className="flex items-center gap-2 text-sm font-semibold text-brand-navy">
          <BookOpen className="h-4 w-4 text-brand-pink" />
          Scenario Reference
        </h2>
        <p className="mt-1 text-xs text-brand-muted">
          How each scenario should run, plus prime example error-free calls to
          compare against.
        </p>
      </div>

      {/* How each scenario should run */}
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-brand-muted">
          How each scenario should run
        </h3>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
          {SCENARIO_PHASES.map((s) => (
            <div
              key={s.phase}
              className="rounded-xl border border-[#e8d8d2] bg-white p-3 shadow-sm"
            >
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-cream text-xs font-bold text-brand-pink">
                  {s.phase}
                </span>
                <span className="text-sm font-semibold text-brand-navy">
                  {s.name}
                </span>
              </div>
              <p className="mt-2 text-[11px] italic text-brand-muted">
                No golden flow defined yet.
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Prime example calls */}
      <section>
        <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-brand-muted">
          <Star className="h-3.5 w-3.5 text-brand-pink" />
          Prime example calls (error-free)
        </h3>
        <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-brand-cream bg-[#fdf5f2] px-6 py-10 text-center">
          <Sparkles className="h-6 w-6 text-brand-muted" />
          <p className="text-sm font-medium text-brand-navy">
            No prime examples yet
          </p>
          <p className="max-w-md text-xs text-brand-muted">
            We are just getting started. Error-free calls will be promoted here as
            references once they accumulate, so you can diff future calls against a
            known-good run.
          </p>
        </div>
      </section>
    </div>
  );
}
