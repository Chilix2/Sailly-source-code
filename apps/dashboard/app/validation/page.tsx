'use client';

import { useEffect, useState } from 'react';
import { Suspense } from 'react';
import Link from 'next/link';

interface ValidationRun {
  id: number;
  run_id: string;
  bucket: string;
  started_at: string;
  finished_at?: string;
  status: 'running' | 'completed' | 'failed';
  total_scenarios: number;
  passed_count: number;
  failed_count: number;
  pass_rate: number;
  phase_a_baseline: number;
  pipeline_gap: number;
  total_elapsed_seconds: number;
}

interface ValidationResult {
  scenario_id: string;
  passed: boolean;
  composite_score: number;
  tools_expected: string[];
  tools_got: string[];
  tools_missing: string[];
  failure_reasons: string[];
  turn_count: number;
}

function BrowserValidationDashboard() {
  const [latestRun, setLatestRun] = useState<ValidationRun | null>(null);
  const [scenarios, setScenarios] = useState<ValidationResult[]>([]);
  const [history, setHistory] = useState<ValidationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedScenario, setExpandedScenario] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);

  useEffect(() => {
    fetchValidationData();
    // Refresh every 10 seconds to show live progress
    const interval = setInterval(fetchValidationData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchValidationData = async () => {
    try {
      const res = await fetch('/api/dashboard/browser-validation');
      if (!res.ok) throw new Error('Failed to fetch validation data');
      
      const data = await res.json();
      setLatestRun(data.latestRun);
      setScenarios(data.scenarios || []);
      setHistory(data.history || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const triggerValidation = async (bucket: string) => {
    try {
      setTriggering(true);
      const res = await fetch('/api/dashboard/browser-validation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bucket }),
      });
      
      if (!res.ok) throw new Error('Failed to trigger validation');
      
      const data = await res.json();
      alert(`Validation started for bucket: ${bucket}`);
      
      // Refresh immediately
      setTimeout(fetchValidationData, 1000);
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setTriggering(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-brand-muted">
        Loading validation dashboard…
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 text-red-700 rounded-lg">
        <h2 className="font-semibold">Error loading validation data</h2>
        <p>{error}</p>
        <button
          onClick={fetchValidationData}
          className="mt-3 px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Browser Validation Dashboard</h1>
        <div className="text-sm text-brand-muted">
          Last updated: {new Date().toLocaleTimeString()}
        </div>
      </div>

      {/* Latest Run Status */}
      {latestRun && (
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 p-6 space-y-4">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-xl font-semibold">
                Latest Run: {latestRun.bucket} (ID: {latestRun.run_id})
              </h2>
              <p className="text-sm text-brand-muted">
                Status: <span className={`font-semibold ${latestRun.status === 'completed' ? 'text-green-600' : 'text-yellow-600'}`}>
                  {latestRun.status}
                </span>
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-brand-muted">
                {new Date(latestRun.started_at).toLocaleString()}
              </p>
              {latestRun.total_elapsed_seconds && (
                <p className="text-sm text-brand-muted">
                  Duration: {Math.round(latestRun.total_elapsed_seconds / 60)}m
                </p>
              )}
            </div>
          </div>

          {/* Pass Rate Display */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded">
              <p className="text-sm text-brand-muted">Pass Rate</p>
              <p className="text-2xl font-bold text-green-600">
                {latestRun.pass_rate.toFixed(1)}%
              </p>
            </div>
            <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded">
              <p className="text-sm text-brand-muted">Passed</p>
              <p className="text-2xl font-bold text-green-600">
                {latestRun.passed_count}/{latestRun.total_scenarios}
              </p>
            </div>
            <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded">
              <p className="text-sm text-brand-muted">Phase A Baseline</p>
              <p className="text-2xl font-bold text-blue-600">
                {latestRun.phase_a_baseline.toFixed(1)}%
              </p>
            </div>
            <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded">
              <p className="text-sm text-brand-muted">Pipeline Gap</p>
              <p className="text-2xl font-bold text-red-600">
                {latestRun.pipeline_gap.toFixed(1)}%
              </p>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Progress</span>
              <span>{latestRun.passed_count + latestRun.failed_count}/{latestRun.total_scenarios} scenarios</span>
            </div>
            <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
              <div
                className="bg-green-500 h-full transition-all"
                style={{ width: `${(latestRun.pass_rate || 0)}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Trigger Buttons */}
      <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 p-6 space-y-4">
        <h3 className="font-semibold">Run Validation</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {['smoke', '1', '2', '3', '4', '5', '6', 'all'].map((bucket) => (
            <button
              key={bucket}
              onClick={() => triggerValidation(bucket)}
              disabled={triggering}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
            >
              {bucket === 'smoke' ? '🔥 Smoke' : bucket === 'all' ? '🔄 Full 280' : `Bucket ${bucket}`}
            </button>
          ))}
        </div>
      </div>

      {/* Scenarios Table */}
      {scenarios.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="p-6 border-b border-slate-200 dark:border-slate-700">
            <h3 className="font-semibold">
              Scenarios ({scenarios.filter(s => s.passed).length}/{scenarios.length} passed)
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="px-4 py-2 text-left text-sm font-semibold">Scenario</th>
                  <th className="px-4 py-2 text-left text-sm font-semibold">Status</th>
                  <th className="px-4 py-2 text-left text-sm font-semibold">Score</th>
                  <th className="px-4 py-2 text-left text-sm font-semibold">Tools</th>
                  <th className="px-4 py-2 text-left text-sm font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                {scenarios.map((scenario) => (
                  <tr key={scenario.scenario_id} className="hover:bg-slate-50 dark:hover:bg-slate-800">
                    <td className="px-4 py-2 text-sm">{scenario.scenario_id}</td>
                    <td className="px-4 py-2 text-sm">
                      <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                        scenario.passed
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {scenario.passed ? '✓ PASS' : '✗ FAIL'}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-sm">{scenario.composite_score.toFixed(1)}</td>
                    <td className="px-4 py-2 text-sm text-xs">
                      {scenario.tools_got.length > 0 ? (
                        <span className="text-brand-muted">{scenario.tools_got.length} tools</span>
                      ) : (
                        <span className="text-red-600">No tools</span>
                      )}
                      {scenario.tools_missing.length > 0 && (
                        <div className="text-red-600">Missing: {scenario.tools_missing.join(', ')}</div>
                      )}
                    </td>
                    <td className="px-4 py-2 text-sm">
                      <button
                        onClick={() => setExpandedScenario(
                          expandedScenario === scenario.scenario_id ? null : scenario.scenario_id
                        )}
                        className="text-blue-600 hover:underline"
                      >
                        {expandedScenario === scenario.scenario_id ? 'Hide' : 'Details'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Expandable Details */}
          {expandedScenario && (
            <div className="bg-slate-50 dark:bg-slate-800 p-4 border-t border-slate-200 dark:border-slate-700">
              {scenarios
                .filter(s => s.scenario_id === expandedScenario)
                .map((scenario) => (
                  <div key={scenario.scenario_id} className="space-y-3 text-sm">
                    <div>
                      <h4 className="font-semibold mb-1">Tools Expected</h4>
                      <p className="text-brand-muted">
                        {scenario.tools_expected.length > 0
                          ? scenario.tools_expected.join(', ')
                          : 'None'}
                      </p>
                    </div>
                    <div>
                      <h4 className="font-semibold mb-1">Tools Got</h4>
                      <p className="text-brand-muted">
                        {scenario.tools_got.length > 0 ? scenario.tools_got.join(', ') : 'None'}
                      </p>
                    </div>
                    {scenario.failure_reasons.length > 0 && (
                      <div>
                        <h4 className="font-semibold mb-1 text-red-600">Failure Reasons</h4>
                        <ul className="text-brand-muted space-y-1">
                          {scenario.failure_reasons.map((reason, i) => (
                            <li key={i}>• {reason}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {/* History Sidebar */}
      {history.length > 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 p-6 space-y-3">
          <h3 className="font-semibold">Recent Runs ({history.length})</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {history.map((run) => (
              <Link
                key={run.run_id}
                href={`/dashboard/validation/${run.run_id}`}
                className="block p-3 bg-slate-50 dark:bg-slate-800 rounded hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-semibold text-sm">{run.bucket}</p>
                    <p className="text-xs text-brand-muted">
                      {new Date(run.started_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-semibold ${
                      (run.pass_rate || 0) >= 85 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {run.pass_rate?.toFixed(1)}%
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ValidationPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[40vh] items-center justify-center text-sm text-brand-muted">
          Loading validation dashboard…
        </div>
      }
    >
      <BrowserValidationDashboard />
    </Suspense>
  );
}

