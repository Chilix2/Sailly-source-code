'use client';

import { Webhook, CheckCircle, Info } from 'lucide-react';

const WEBHOOK_ENDPOINTS = [
  {
    path: '/twilio/incoming',
    description: 'Handles inbound Twilio voice calls and routes them to the agent',
    method: 'POST',
  },
  {
    path: '/elevenlabs/webhook',
    description: 'Receives ElevenLabs conversation events and post-call data',
    method: 'POST',
  },
  {
    path: '/api/demo/call-status',
    description: 'Twilio call status callback for tracking call lifecycle events',
    method: 'POST',
  },
];

export default function WebhooksPage() {
  return (
    <div className="min-h-screen bg-transparent p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-brand-navy mb-2">Webhooks</h1>
          <p className="text-brand-slate">Configured webhook endpoints and integration status</p>
        </div>

        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6 mb-8">
          <h2 className="text-lg font-bold text-brand-navy mb-4 flex items-center gap-2">
            <Webhook size={18} className="text-brand-pink" />
            Configured Endpoints
          </h2>
          <div className="space-y-4">
            {WEBHOOK_ENDPOINTS.map((ep) => (
              <div
                key={ep.path}
                className="flex items-start justify-between p-4 bg-brand-cream border border-brand-cream rounded-lg"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <code className="text-brand-navy font-mono text-sm">{ep.path}</code>
                    <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 font-semibold">
                      {ep.method}
                    </span>
                  </div>
                  <p className="text-brand-slate text-sm">{ep.description}</p>
                </div>
                <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                  <CheckCircle size={16} className="text-[#16a34a]" />
                  <span className="text-[#16a34a] text-sm font-semibold">Active</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white/50 shadow-sm border border-blue-500/10 rounded-lg p-4 flex items-start gap-3">
          <Info size={18} className="text-blue-400 flex-shrink-0 mt-0.5" />
          <p className="text-brand-slate text-sm">
            Webhook health monitoring, delivery success rates, and failed webhook logging are
            coming in a future release.
          </p>
        </div>
      </div>
    </div>
  );
}
