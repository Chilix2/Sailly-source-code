'use client';

import React from 'react';
import { AlertCircle } from 'lucide-react';

/**
 * Phase 8: Steering (Placeholder)
 *
 * This phase requires backend endpoints for:
 * - Reset: Clear call state and restart from beginning
 * - Fork: Create a branch point for exploring alternate decisions
 * - Replay: Re-execute a turn with modified state or inputs
 *
 * Once backend provides these endpoints, this view will enable:
 * - Resetting the call to a specific turn
 * - Creating decision branches at forks
 * - Testing alternate LLM outputs
 * - Validating FSM paths
 */
export function SteeringView() {
  return (
    <div className="p-6 space-y-6 bg-gradient-to-br from-slate-50 via-white to-slate-100 min-h-full">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-brand-navy mb-2">
          Call Steering
        </h2>
        <p className="text-xs text-brand-muted">
          Phase 8: Reset, fork, and replay controls (requires backend implementation)
        </p>
      </div>

      {/* Warning banner */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex gap-3">
        <AlertCircle className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="text-sm font-semibold text-orange-700 mb-1">
            Backend Implementation Required
          </h4>
          <p className="text-xs text-orange-600">
            Steering requires backend reset/fork/replay endpoints. These are scheduled for
            a future phase after core FSM observability is stable.
          </p>
        </div>
      </div>

      {/* Placeholder sections */}
      <div className="space-y-4">
        <div className="bg-white p-4 rounded-lg border border-brand-cream">
          <h3 className="text-sm font-semibold text-brand-navy mb-3">Reset</h3>
          <p className="text-xs text-brand-muted mb-3">
            Clear the call and restart from a specific turn or from the beginning.
          </p>
          <button
            disabled
            className="px-3 py-1 bg-slate-100 text-brand-muted rounded-lg text-xs cursor-not-allowed opacity-50"
          >
            Reset to Start (disabled)
          </button>
        </div>

        <div className="bg-white p-4 rounded-lg border border-brand-cream">
          <h3 className="text-sm font-semibold text-brand-navy mb-3">Fork</h3>
          <p className="text-xs text-brand-muted mb-3">
            Create a branch point at a specific turn to explore alternate FSM paths.
          </p>
          <button
            disabled
            className="px-3 py-1 bg-slate-100 text-brand-muted rounded-lg text-xs cursor-not-allowed opacity-50"
          >
            Create Fork (disabled)
          </button>
        </div>

        <div className="bg-white p-4 rounded-lg border border-brand-cream">
          <h3 className="text-sm font-semibold text-brand-navy mb-3">Replay</h3>
          <p className="text-xs text-brand-muted mb-3">
            Re-execute a turn with modified inputs or state to test alternate decision paths.
          </p>
          <div className="space-y-2">
            <input
              type="text"
              placeholder="User input to replay with..."
              disabled
              className="w-full px-2 py-1 bg-slate-50 border border-brand-cream rounded-lg text-xs text-brand-muted cursor-not-allowed opacity-50"
            />
            <button
              disabled
              className="px-3 py-1 bg-slate-100 text-brand-muted rounded-lg text-xs cursor-not-allowed opacity-50"
            >
              Replay Turn (disabled)
            </button>
          </div>
        </div>
      </div>

      {/* Documentation */}
      <div className="bg-white p-4 rounded-lg border border-brand-cream text-xs space-y-2 text-brand-muted">
        <p className="font-semibold text-brand-navy">Implementation Roadmap</p>
        <ul className="list-disc list-inside space-y-1 ml-2">
          <li>
            Backend: Add <code>/api/admin/call/{'{call_sid}'}/reset</code> endpoint
          </li>
          <li>
            Backend: Add <code>/api/admin/call/{'{call_sid}'}/fork</code> endpoint
          </li>
          <li>
            Backend: Add <code>/api/admin/call/{'{call_sid}'}/replay</code> endpoint
          </li>
          <li>Frontend: Enable controls and connect to endpoints</li>
          <li>Testing: Validate alternate FSM paths and decisions</li>
        </ul>
      </div>
    </div>
  );
}
