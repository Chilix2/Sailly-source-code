'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Phone,
  PlayCircle,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Activity,
  Zap,
  Globe,
  Clock,
} from 'lucide-react';

interface DryRunCheck {
  name: string;
  status: 'pass' | 'fail' | 'warn';
  message: string;
}

interface DryRunResult {
  success: boolean;
  checks: DryRunCheck[];
}

interface RecentCall {
  id: number;
  call_sid: string;
  caller_number: string;
  started_at: string;
  duration_seconds: number;
  quality_score: number;
  outcome: string;
  total_cost: number;
  was_escalated: boolean;
}

const INDUSTRIES = [
  { value: 'restaurant', label: 'Restaurant' },
  { value: 'hotel', label: 'Hotel' },
  { value: 'retail', label: 'Retail' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'generic', label: 'Generic' },
];

const LOCALES = [
  { value: 'de-DE', label: 'Deutsch (DE)' },
  { value: 'en-US', label: 'English (US)' },
  { value: 'en-GB', label: 'English (GB)' },
  { value: 'fr-FR', label: 'Français (FR)' },
  { value: 'es-ES', label: 'Español (ES)' },
];

function formatDuration(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' });
}

function qualityBadge(score: number) {
  if (score >= 8) return 'bg-[#f0fdf4] text-[#16a34a]';
  if (score >= 6) return 'bg-[#fff8ea] text-brand-peach';
  return 'bg-[#fff0ee] text-brand-salmon';
}

export default function TestingPage() {
  const router = useRouter();

  const [phoneNumber, setPhoneNumber] = useState('');
  const [industry, setIndustry] = useState('restaurant');
  const [locale, setLocale] = useState('de-DE');
  const [initiating, setInitiating] = useState(false);
  const [initiateResult, setInitiateResult] = useState<{ success: boolean; message: string } | null>(null);

  const [recentCalls, setRecentCalls] = useState<RecentCall[]>([]);
  const [callsLoading, setCallsLoading] = useState(true);

  const [dryRunResult, setDryRunResult] = useState<DryRunResult | null>(null);
  const [dryRunLoading, setDryRunLoading] = useState(false);

  const [infraStatus, setInfraStatus] = useState<{
    twilio: 'unknown' | 'ok' | 'error';
    model: 'unknown' | 'ok' | 'error';
  }>({ twilio: 'unknown', model: 'unknown' });

  const loadRecentCalls = useCallback(async () => {
    try {
      setCallsLoading(true);
      const res = await fetch('/api/dashboard/calls?limit=10&offset=0');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setRecentCalls(json.calls ?? json.data ?? []);
    } catch {
      // silent
    } finally {
      setCallsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRecentCalls();
  }, [loadRecentCalls]);

  const handleInitiate = async () => {
    if (!phoneNumber.trim()) return;
    try {
      setInitiating(true);
      setInitiateResult(null);
      const res = await fetch('/api/demo/initiate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone_number: phoneNumber.trim(), industry, locale }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? json.message ?? `HTTP ${res.status}`);
      setInitiateResult({ success: true, message: json.message ?? 'Call initiated successfully' });
      setTimeout(() => loadRecentCalls(), 5000);
    } catch (err) {
      setInitiateResult({ success: false, message: err instanceof Error ? err.message : 'Failed to initiate call' });
    } finally {
      setInitiating(false);
    }
  };

  const handleDryRun = async () => {
    try {
      setDryRunLoading(true);
      setDryRunResult(null);
      const res = await fetch('/api/demo/dry-run');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setDryRunResult(json);

      const allPass = json.checks?.every((c: DryRunCheck) => c.status === 'pass');
      setInfraStatus({
        twilio: json.checks?.find((c: DryRunCheck) => c.name.toLowerCase().includes('twilio'))?.status === 'pass' ? 'ok' : 'error',
        model: json.checks?.find((c: DryRunCheck) => c.name.toLowerCase().includes('model') || c.name.toLowerCase().includes('gemini'))?.status === 'pass' ? 'ok' : allPass ? 'ok' : 'unknown',
      });
    } catch {
      setDryRunResult({ success: false, checks: [] });
    } finally {
      setDryRunLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-transparent p-6 md:p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-brand-navy">Testing & QA</h1>
          <p className="text-brand-slate mt-1">Trigger test calls, run dry-run checks, and review results</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Initiate + Dry Run */}
          <div className="lg:col-span-1 space-y-6">
            {/* Initiate Test Call */}
            <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6 space-y-4">
              <h2 className="text-sm font-semibold text-brand-navy flex items-center gap-2">
                <Phone size={16} />
                Initiate Test Call
              </h2>

              <div className="space-y-3">
                <div>
                  <label className="text-xs text-brand-slate mb-1 block">Phone Number</label>
                  <input
                    type="tel"
                    placeholder="+49..."
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    className="w-full px-3 py-2 bg-brand-cream border border-[#e8d8d2] rounded-lg text-brand-navy placeholder-zinc-500 focus:border-accent outline-none transition text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-brand-slate mb-1 block">Industry</label>
                  <select
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="w-full px-3 py-2 bg-brand-cream border border-[#e8d8d2] rounded-lg text-brand-navy focus:border-accent outline-none transition text-sm"
                  >
                    {INDUSTRIES.map((i) => (
                      <option key={i.value} value={i.value}>{i.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-brand-slate mb-1 block">Locale</label>
                  <select
                    value={locale}
                    onChange={(e) => setLocale(e.target.value)}
                    className="w-full px-3 py-2 bg-brand-cream border border-[#e8d8d2] rounded-lg text-brand-navy focus:border-accent outline-none transition text-sm"
                  >
                    {LOCALES.map((l) => (
                      <option key={l.value} value={l.value}>{l.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                onClick={handleInitiate}
                disabled={initiating || !phoneNumber.trim()}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-pink hover:bg-accent/80 disabled:bg-zinc-800 disabled:text-zinc-600 text-brand-navy font-medium rounded-lg text-sm transition"
              >
                {initiating ? <RefreshCw size={16} className="animate-spin" /> : <PlayCircle size={16} />}
                {initiating ? 'Initiating…' : 'Start Test Call'}
              </button>

              {initiateResult && (
                <div className={`p-3 rounded-lg text-sm ${
                  initiateResult.success
                    ? 'bg-green-950/30 border border-green-900/50 text-[#16a34a]'
                    : 'bg-[#fff0ee] border border-[#ffd8d0] text-brand-salmon'
                }`}>
                  {initiateResult.success ? <CheckCircle2 size={14} className="inline mr-1" /> : <XCircle size={14} className="inline mr-1" />}
                  {initiateResult.message}
                </div>
              )}
            </div>

            {/* Dry Run */}
            <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6 space-y-4">
              <h2 className="text-sm font-semibold text-brand-navy flex items-center gap-2">
                <Zap size={16} />
                Dry-Run Check
              </h2>
              <p className="text-xs text-brand-muted">Validate infrastructure without making a real call</p>
              <button
                onClick={handleDryRun}
                disabled={dryRunLoading}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-cream hover:bg-[#dfcdc7] disabled:text-zinc-600 text-brand-navy font-medium rounded-lg text-sm transition border border-[#e8d8d2]"
              >
                {dryRunLoading ? <RefreshCw size={16} className="animate-spin" /> : <Activity size={16} />}
                {dryRunLoading ? 'Running…' : 'Run Dry-Run'}
              </button>

              {dryRunResult && (
                <div className="space-y-2">
                  <div className={`flex items-center gap-2 text-sm font-medium ${
                    dryRunResult.success ? 'text-[#16a34a]' : 'text-brand-salmon'
                  }`}>
                    {dryRunResult.success ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                    {dryRunResult.success ? 'All checks passed' : 'Some checks failed'}
                  </div>
                  {dryRunResult.checks.map((check, idx) => (
                    <div key={idx} className="flex items-start gap-2 py-1.5 text-xs">
                      {check.status === 'pass' ? (
                        <CheckCircle2 size={14} className="text-[#16a34a] shrink-0 mt-0.5" />
                      ) : check.status === 'warn' ? (
                        <AlertCircle size={14} className="text-yellow-400 shrink-0 mt-0.5" />
                      ) : (
                        <XCircle size={14} className="text-brand-salmon shrink-0 mt-0.5" />
                      )}
                      <div>
                        <span className="text-brand-navy font-medium">{check.name}</span>
                        <p className="text-brand-muted">{check.message}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Infrastructure Status */}
            <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6 space-y-4">
              <h2 className="text-sm font-semibold text-brand-navy flex items-center gap-2">
                <Globe size={16} />
                Infrastructure Status
              </h2>
              <div className="space-y-3">
                <StatusRow label="Twilio" status={infraStatus.twilio} />
                <StatusRow label="Gemini Model" status={infraStatus.model} />
              </div>
              <p className="text-xs text-brand-muted">Run a dry-run to refresh status</p>
            </div>
          </div>

          {/* Right Column: Recent Test Calls */}
          <div className="lg:col-span-2">
            <div className="bg-white shadow-sm border border-brand-cream rounded-lg overflow-hidden">
              <div className="flex items-center justify-between p-6 border-b border-brand-cream">
                <h2 className="text-sm font-semibold text-brand-navy flex items-center gap-2">
                  <Clock size={16} />
                  Recent Calls
                </h2>
                <button
                  onClick={loadRecentCalls}
                  disabled={callsLoading}
                  className="flex items-center gap-1 px-3 py-1.5 bg-brand-cream hover:bg-[#dfcdc7] border border-[#e8d8d2] rounded-lg text-brand-slate text-xs transition"
                >
                  <RefreshCw size={14} className={callsLoading ? 'animate-spin' : ''} />
                  Refresh
                </button>
              </div>

              {callsLoading && recentCalls.length === 0 ? (
                <div className="p-8 text-center text-brand-muted flex items-center justify-center gap-2">
                  <RefreshCw size={16} className="animate-spin" />
                  Loading calls…
                </div>
              ) : recentCalls.length === 0 ? (
                <div className="p-8 text-center text-brand-muted">
                  No calls recorded yet. Trigger a test call to get started.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-brand-cream border-b border-brand-cream">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-brand-slate">Date</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-brand-slate">Caller</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-brand-slate">Duration</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-brand-slate">Quality</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-brand-slate">Outcome</th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-brand-slate">Cost</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800">
                      {recentCalls.map((call) => (
                        <tr
                          key={call.id}
                          onClick={() => router.push(`/calls/${call.id}`)}
                          className="hover:bg-[#ecd8d3] transition cursor-pointer"
                        >
                          <td className="px-4 py-3 text-brand-navy text-xs">{formatDateTime(call.started_at)}</td>
                          <td className="px-4 py-3 text-brand-navy font-mono text-xs">{call.caller_number}</td>
                          <td className="px-4 py-3 text-brand-navy text-xs">{formatDuration(call.duration_seconds)}</td>
                          <td className="px-4 py-3">
                            {call.quality_score != null ? (
                              <span className={`px-2 py-0.5 rounded text-xs font-medium ${qualityBadge(call.quality_score * 10)}`}>
                                {(call.quality_score * 10).toFixed(1)}
                              </span>
                            ) : (
                              <span className="text-brand-muted text-xs">—</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-brand-slate text-xs">{call.outcome ?? '—'}</td>
                          <td className="px-4 py-3 text-right text-brand-slate font-mono text-xs">
                            {call.total_cost != null ? `€${call.total_cost.toFixed(3)}` : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusRow({ label, status }: { label: string; status: 'unknown' | 'ok' | 'error' }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-brand-navy">{label}</span>
      <span className={`flex items-center gap-1.5 text-xs font-medium ${
        status === 'ok' ? 'text-[#16a34a]' : status === 'error' ? 'text-brand-salmon' : 'text-brand-muted'
      }`}>
        <span className={`w-2 h-2 rounded-full ${
          status === 'ok' ? 'bg-green-400' : status === 'error' ? 'bg-red-400' : 'bg-[#dfcdc7]'
        }`} />
        {status === 'ok' ? 'Operational' : status === 'error' ? 'Error' : 'Unknown'}
      </span>
    </div>
  );
}
