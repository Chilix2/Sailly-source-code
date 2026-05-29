'use client';

import { useState, useEffect } from 'react';
import {
  Shield,
  CheckCircle,
  AlertCircle,
  Clock,
  Database,
  HardDrive,
  RefreshCw,
} from 'lucide-react';

interface CallRecord {
  id: string;
  recording_consent_at: string | null;
  started_at: string;
}

export default function GDPRCompliancePage() {
  const [calls, setCalls] = useState<CallRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/dashboard/calls').then((r: any) => r.json());
      const data = res.calls ?? res.data ?? (Array.isArray(res) ? res : []) as CallRecord[];
      if (Array.isArray(data)) {
        setCalls(data);
      } else {
        setError(res.error || 'Failed to load call data');
      }
    } catch (e: any) {
      setError(e.message || 'Network error');
    } finally {
      setLoading(false);
    }
  }

  const totalCalls = calls.length;
  const withConsent = calls.filter((c) => c.recording_consent_at !== null).length;
  const withoutConsent = totalCalls - withConsent;
  const consentRate = totalCalls > 0 ? Math.round((withConsent / totalCalls) * 100) : 0;

  type ChecklistStatus = 'done' | 'pending';

  const complianceChecklist: { label: string; detail: string; status: ChecklistStatus }[] = [
    {
      label: 'Recording Consent Tracking',
      detail: `${withConsent} of ${totalCalls} calls have recorded consent`,
      status: totalCalls > 0 ? 'done' : 'pending',
    },
    {
      label: 'Data Processing Agreement (DPA)',
      detail: 'Google Cloud DPA signed; ElevenLabs DPA in place',
      status: 'done',
    },
    {
      label: 'Data Retention Automation',
      detail: 'Automated purge not yet implemented',
      status: 'pending',
    },
    {
      label: 'PII Redaction in Logs',
      detail: 'Pending implementation',
      status: 'pending',
    },
    {
      label: 'Data Subject Request Handling',
      detail: 'Manual process — no self-serve portal yet',
      status: 'pending',
    },
    {
      label: 'DPIA (Data Protection Impact Assessment)',
      detail: 'Documented in COMPLIANCE_ROADMAP',
      status: 'done',
    },
  ];

  const dataStores = [
    {
      name: 'PostgreSQL',
      description: 'Call metadata, transcripts, consent records, tool invocations',
      icon: Database,
      retention: '90-day retention policy planned',
    },
    {
      name: 'Google Cloud Storage (GCS)',
      description: 'Audio recordings (when consent is given)',
      icon: HardDrive,
      retention: '30-day retention policy planned',
    },
    {
      name: 'Redis',
      description: 'Session state, rate limiting, temporary caches',
      icon: Database,
      retention: 'Ephemeral — TTL-based expiry',
    },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-transparent p-8 flex items-center justify-center">
        <RefreshCw size={24} className="animate-spin text-brand-pink" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-transparent p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-brand-navy mb-2">GDPR &amp; Compliance</h1>
          <p className="text-brand-slate">Consent tracking, data retention, and compliance status</p>
        </div>

        {error && (
          <div className="bg-white shadow-sm border border-brand-salmon/30 rounded-lg p-4 mb-8 flex items-center gap-3">
            <AlertCircle size={18} className="text-brand-salmon flex-shrink-0" />
            <p className="text-brand-salmon text-sm">{error}</p>
            <button
              onClick={loadData}
              className="ml-auto px-3 py-1.5 bg-brand-cream rounded text-brand-navy text-sm hover:bg-[#dfcdc7] transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
            <p className="text-brand-slate text-sm mb-1">Total Calls</p>
            <p className="text-3xl font-bold text-brand-pink">{totalCalls}</p>
          </div>
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
            <p className="text-brand-slate text-sm mb-1">With Consent</p>
            <p className="text-3xl font-bold text-[#16a34a]">{withConsent}</p>
          </div>
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
            <p className="text-brand-slate text-sm mb-1">Without Consent</p>
            <p className="text-3xl font-bold text-yellow-500">{withoutConsent}</p>
          </div>
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
            <p className="text-brand-slate text-sm mb-1">Consent Rate</p>
            <p className="text-3xl font-bold text-brand-navy">{consentRate}%</p>
          </div>
        </div>

        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6 mb-8">
          <h2 className="text-lg font-bold text-brand-navy mb-4 flex items-center gap-2">
            <Shield size={18} className="text-brand-pink" />
            Compliance Checklist
          </h2>
          <div className="space-y-3">
            {complianceChecklist.map((item, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3 bg-brand-cream border border-brand-cream rounded-lg"
              >
                {item.status === 'done' ? (
                  <CheckCircle size={18} className="text-[#16a34a] flex-shrink-0 mt-0.5" />
                ) : (
                  <Clock size={18} className="text-yellow-500 flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <p className="text-brand-navy font-medium text-sm">{item.label}</p>
                  <p className="text-brand-slate text-xs mt-0.5">{item.detail}</p>
                </div>
                <span
                  className={`ml-auto text-xs font-semibold px-2 py-0.5 rounded ${
                    item.status === 'done'
                      ? 'bg-green-500/20 text-[#16a34a]'
                      : 'bg-yellow-500/20 text-yellow-500'
                  }`}
                >
                  {item.status === 'done' ? 'Done' : 'Pending'}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
          <h2 className="text-lg font-bold text-brand-navy mb-4 flex items-center gap-2">
            <Database size={18} className="text-brand-pink" />
            Data Storage &amp; Retention
          </h2>
          <div className="space-y-4">
            {dataStores.map((store) => (
              <div
                key={store.name}
                className="flex items-start gap-4 p-4 bg-brand-cream border border-brand-cream rounded-lg"
              >
                <store.icon size={20} className="text-brand-pink flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-brand-navy font-medium">{store.name}</p>
                    <span className="text-xs px-2 py-0.5 rounded bg-green-500/20 text-[#16a34a] font-semibold">
                      Active
                    </span>
                  </div>
                  <p className="text-brand-slate text-sm">{store.description}</p>
                  <p className="text-brand-muted text-xs mt-1">Retention: {store.retention}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
