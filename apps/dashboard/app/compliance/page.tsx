'use client';

export default function CompliancePage() {
  return (
    <div className="min-h-screen bg-transparent p-8">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold text-brand-navy mb-2">Compliance & GDPR</h1>
        <p className="text-brand-slate">Data protection and regulatory compliance management</p>
        <div className="mt-12 p-6 bg-white shadow-sm border border-brand-cream rounded-lg text-center">
          <p className="text-brand-slate">Phase 3 Implementation</p>
          <p className="text-brand-navy font-semibold mt-2">Compliance center coming soon</p>
          <p className="text-sm text-brand-muted mt-4">Features: DSR, retention management, consent tracking, audit log, data flow map, compliance checklist</p>
        </div>
      </div>
    </div>
  );
}
