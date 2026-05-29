'use client';

import React from 'react';
import { TurnRow } from '@/types/sailly-debugger';
import { AlertTriangle, TrendingDown, Clock } from 'lucide-react';

/**
 * Root cause analyzer: detects issues in call flow
 */
function analyzeRootCauses(turns: TurnRow[]): Array<{
  score: number; // 0-100, where 100 is most critical
  category: string;
  message: string;
  affectedTurns: number[];
  severity: 'error' | 'warning' | 'info';
}> {
  const issues: Array<{
    score: number;
    category: string;
    message: string;
    affectedTurns: number[];
    severity: 'error' | 'warning' | 'info';
  }> = [];

  // Check for high latency turns
  const highLatencyTurns = turns
    .map((t, idx) => ({ idx, latency: t.total_latency_ms || 0 }))
    .filter((t) => t.latency > 5000);

  if (highLatencyTurns.length > 0) {
    issues.push({
      score: Math.min(100, highLatencyTurns.length * 20),
      category: 'Performance',
      message: `${highLatencyTurns.length} turn(s) exceeded 5 second latency`,
      affectedTurns: highLatencyTurns.map((t) => t.idx),
      severity: 'warning',
    });
  }

  // Check for tool failures
  const toolFailures = turns.filter(
    (t) =>
      t.layer3_changes &&
      typeof t.layer3_changes === 'string' &&
      t.layer3_changes.includes('suppressed')
  );

  if (toolFailures.length > 0) {
    issues.push({
      score: 75,
      category: 'Tool Execution',
      message: `${toolFailures.length} tool calls were suppressed by policy`,
      affectedTurns: toolFailures.map((t) => t.turn_number),
      severity: 'warning',
    });
  }

  // Check for low STT confidence
  const lowConfidenceTurns = turns
    .map((t, idx) => ({
      idx,
      confidence: (t.stt_confidence as number) || 1.0,
    }))
    .filter((t) => t.confidence < 0.5);

  if (lowConfidenceTurns.length > 0) {
    issues.push({
      score: 60,
      category: 'Speech Recognition',
      message: `${lowConfidenceTurns.length} turn(s) had low STT confidence (< 50%)`,
      affectedTurns: lowConfidenceTurns.map((t) => t.idx),
      severity: 'warning',
    });
  }

  // Check for validation failures
  const validationFailures = turns.filter((t) => {
    if (typeof t.layer1_decision === 'string') {
      try {
        const d = JSON.parse(t.layer1_decision);
        return d.validators_run?.some((v: any) => v.status === 'failed');
      } catch {
        return false;
      }
    }
    return false;
  });

  if (validationFailures.length > 0) {
    issues.push({
      score: 80,
      category: 'Validation',
      message: `${validationFailures.length} turn(s) had validation failures`,
      affectedTurns: validationFailures.map((t) => t.turn_number),
      severity: 'error',
    });
  }

  // Check for FSM state anomalies (repeated nodes)
  const nodes = turns.map((t) => t.node_name);
  const repeatedNodes = new Set<string>();
  for (let i = 1; i < nodes.length; i++) {
    if (nodes[i] === nodes[i - 1]) {
      repeatedNodes.add(nodes[i]);
    }
  }

  if (repeatedNodes.size > 0) {
    issues.push({
      score: 65,
      category: 'FSM Path',
      message: `FSM state repeated (potential loop): ${Array.from(repeatedNodes).join(', ')}`,
      affectedTurns: turns
        .map((t, idx) => (repeatedNodes.has(t.node_name || '') ? idx : -1))
        .filter((idx) => idx >= 0),
      severity: 'warning',
    });
  }

  // Sort by score descending
  return issues.sort((a, b) => b.score - a.score);
}

export function RootCauseView({ turns }: { turns: TurnRow[] }) {
  const issues = React.useMemo(() => analyzeRootCauses(turns), [turns]);

  const overallScore = Math.max(
    0,
    100 - Math.min(100, issues.reduce((sum, i) => sum + i.score, 0) / 5)
  );

  if (turns.length === 0) {
    return (
      <div className="p-6 text-center text-brand-muted text-sm">
        No turns available for root cause analysis
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 overflow-y-auto">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-brand-navy mb-2">
          Root Cause Analysis
        </h2>
        <p className="text-xs text-brand-muted">
          Automated detection of call flow anomalies and issues
        </p>
      </div>

      {/* Overall health score */}
      <div className="bg-slate-50 p-4 rounded border border-brand-cream">
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <div className="text-xs font-semibold text-brand-navy mb-2">
              Call Health Score
            </div>
            <div className="w-full bg-white border border-brand-cream rounded h-3 overflow-hidden">
              <div
                className={`h-full transition-all ${
                  overallScore > 80
                    ? 'bg-green-500'
                    : overallScore > 50
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                }`}
                style={{ width: overallScore + '%' }}
              />
            </div>
          </div>
          <div className="text-2xl font-bold text-brand-navy">
            {overallScore.toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Issues */}
      <div className="space-y-3">
        {issues.length === 0 ? (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-700">
            ✓ No issues detected. Call flow appears healthy.
          </div>
        ) : (
          issues.map((issue, idx) => (
            <div
              key={idx}
              className={`p-4 rounded border ${
                issue.severity === 'error'
                  ? 'bg-red-50 border-red-200'
                  : issue.severity === 'warning'
                    ? 'bg-yellow-50 border-yellow-200'
                    : 'bg-blue-50 border-blue-200'
              }`}
            >
              <div className="flex items-start gap-3">
                {issue.severity === 'error' ? (
                  <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                ) : issue.severity === 'warning' ? (
                  <TrendingDown className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
                ) : (
                  <Clock className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
                )}

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h4
                      className={`text-sm font-semibold ${
                        issue.severity === 'error'
                          ? 'text-red-700'
                          : issue.severity === 'warning'
                            ? 'text-orange-700'
                            : 'text-blue-700'
                      }`}
                    >
                      {issue.category}
                    </h4>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        issue.severity === 'error'
                          ? 'bg-red-100 text-red-700'
                          : issue.severity === 'warning'
                            ? 'bg-yellow-100 text-orange-700'
                            : 'bg-blue-100 text-blue-700'
                      }`}
                    >
                      {Math.round(issue.score)}
                    </span>
                  </div>

                  <p
                    className={`text-xs mt-1 ${
                      issue.severity === 'error'
                        ? 'text-red-700'
                        : issue.severity === 'warning'
                          ? 'text-orange-700'
                          : 'text-blue-700'
                    }`}
                  >
                    {issue.message}
                  </p>

                  {issue.affectedTurns.length > 0 && (
                    <div
                      className={`text-xs mt-2 pt-2 border-t ${
                        issue.severity === 'error'
                          ? 'border-red-200 text-red-700'
                          : issue.severity === 'warning'
                            ? 'border-yellow-200 text-orange-700'
                            : 'border-blue-200 text-blue-700'
                      }`}
                    >
                      Affected turns: {issue.affectedTurns.map((t) => `T${t}`).join(', ')}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Statistics */}
      <div className="bg-slate-50 p-4 rounded border border-brand-cream">
        <h4 className="text-sm font-semibold text-brand-navy mb-3">Call Statistics</h4>
        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-brand-muted">Total Turns</span>
            <p className="text-lg font-semibold text-brand-navy">{turns.length}</p>
          </div>
          <div>
            <span className="text-brand-muted">Avg Latency</span>
            <p className="text-lg font-semibold text-brand-navy">
              {(
                turns.reduce((sum, t) => sum + (t.total_latency_ms || 0), 0) /
                turns.length
              ).toFixed(0)}ms
            </p>
          </div>
          <div>
            <span className="text-brand-muted">Tools Used</span>
            <p className="text-lg font-semibold text-brand-navy">
              {new Set(turns.flatMap((t) => t.tools_called || [])).size}
            </p>
          </div>
          <div>
            <span className="text-brand-muted">Slots Filled</span>
            <p className="text-lg font-semibold text-brand-navy">
              {turns.reduce((max, t) => Math.max(max, t.slots_filled_count || 0), 0)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
