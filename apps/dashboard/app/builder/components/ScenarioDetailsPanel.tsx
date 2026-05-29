'use client';

import React from 'react';
import { ScenarioTags } from '@/types/sailly-debugger';
import { AlertCircle, CheckCircle, Info } from 'lucide-react';

export function ScenarioDetailsPanel({
  scenario: tags,
  className = '',
}: {
  scenario?: ScenarioTags;
  className?: string;
}) {
  if (!tags) {
    return (
      <div className={`text-xs text-brand-muted italic ${className}`}>
        Scenario tags not yet classified (check back in 5 minutes)
      </div>
    );
  }

  // Color map for scenario phases
  const phaseColors: Record<string, string> = {
    A: 'bg-green-50 text-green-700 border-green-200',
    B: 'bg-blue-50 text-blue-700 border-blue-200',
    C: 'bg-orange-50 text-orange-700 border-orange-200',
    D: 'bg-red-50 text-red-700 border-red-200',
  };

  const phaseColor = phaseColors[tags.scenario_phase] || phaseColors.D;

  // Confidence indicator
  const getConfidenceIcon = (conf: number) => {
    if (conf >= 0.85) return <CheckCircle className="w-4 h-4 text-green-600" />;
    if (conf >= 0.65) return <Info className="w-4 h-4 text-blue-600" />;
    return <AlertCircle className="w-4 h-4 text-orange-600" />;
  };

  const getConfidenceText = (conf: number) => {
    if (conf >= 0.85) return 'High confidence';
    if (conf >= 0.65) return 'Moderate confidence';
    return 'Low confidence';
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Primary scenario + phase badge */}
      <div className="border border-brand-cream rounded-lg p-3 bg-slate-50">
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-semibold text-brand-muted uppercase">
            Scenario Classification
          </span>
          <div className="flex items-center gap-1">
            {getConfidenceIcon(tags.confidence)}
            <span className="text-xs font-medium text-slate-700">
              {getConfidenceText(tags.confidence)}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="px-3 py-1 bg-white border border-brand-cream rounded-lg">
            <span className="text-sm font-semibold text-brand-navy">
              {tags.primary_scenario.split('_').join(' ')}
            </span>
          </div>
          <div className={`px-2 py-1 border rounded ${phaseColor}`}>
            <span className="text-sm font-bold">Phase {tags.scenario_phase}</span>
          </div>
          <span className="text-xs text-brand-muted">
            ({Math.round(tags.confidence * 100)}% confidence)
          </span>
        </div>
      </div>

      {/* Detected intents */}
      {tags.detected_intents && tags.detected_intents.length > 0 && (
        <div className="border border-brand-cream rounded-lg p-3">
          <div className="text-xs font-semibold text-brand-muted uppercase mb-2">
            Detected Intents
          </div>
          <div className="flex flex-wrap gap-2">
            {tags.detected_intents.map((intent) => (
              <span
                key={intent}
                className="px-2 py-1 bg-brand-peach/20 border border-brand-peach rounded text-xs font-medium text-brand-navy"
              >
                {intent}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Modifiers */}
      {tags.modifiers && tags.modifiers.length > 0 && (
        <div className="border border-brand-cream rounded-lg p-3">
          <div className="text-xs font-semibold text-brand-muted uppercase mb-2">
            Flags
          </div>
          <div className="space-y-1">
            {tags.modifiers.map((mod) => (
              <div
                key={mod}
                className="inline-block px-2 py-1 bg-slate-100 border border-slate-200 rounded text-xs text-slate-700 font-medium mr-2 mb-1"
              >
                • {mod}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* LLM Reasoning */}
      {tags.llm_reasoning && (
        <div className="border border-brand-cream rounded-lg p-3 bg-slate-50">
          <div className="text-xs font-semibold text-brand-muted uppercase mb-1">
            Classification Reasoning
          </div>
          <p className="text-xs text-slate-700 leading-relaxed italic">
            "{tags.llm_reasoning}"
          </p>
        </div>
      )}

      {/* Classification timestamp */}
      <div className="text-xs text-brand-muted text-right">
        Classified {tags.classified_at ? new Date(tags.classified_at).toLocaleTimeString() : 'pending'}
      </div>
    </div>
  );
}
