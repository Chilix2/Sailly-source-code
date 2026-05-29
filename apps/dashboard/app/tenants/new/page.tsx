'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { CheckCircle, ChevronLeft, ChevronRight, Loader, Rocket } from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

type CapabilitySummary = {
  id: string;
  name: string;
  description?: string;
};

type ProviderModel = {
  id: string;
  label: string;
  latency_class?: string;
};

type ProviderDescriptor = {
  id: string;
  label: string;
  configured?: boolean;
  models?: ProviderModel[];
};

type ProviderCatalog = {
  stt?: ProviderDescriptor[];
  llm?: ProviderDescriptor[];
  tts?: ProviderDescriptor[];
};

const STEPS = [
  'Industry',
  'Business',
  'Capabilities',
  'Providers',
  'Voice',
  'Knowledge',
  'Tools',
  'Routing',
  'Scenarios',
  'Test',
  'Deploy',
  'Readiness',
];

type WizardState = {
  tenant_id: string;
  industry: string;
  name: string;
  language: string;
  city: string;
  address: string;
  phone: string;
  hours: string;
  capabilities: string[];
  stt_provider: string;
  stt_model: string;
  llm_provider: string;
  llm_model: string;
  tts_provider: string;
  tts_model: string;
  tts_voice: string;
  greeting_line: string;
  knowledge_notes: string;
  tools: string[];
  phone_number: string;
  websocket_route: string;
};

const DEFAULT_FORM: WizardState = {
  tenant_id: '',
  industry: 'restaurant',
  name: '',
  language: 'de',
  city: '',
  address: '',
  phone: '',
  hours: '',
  capabilities: ['greeting_language', 'business_info', 'menu_browsing', 'takeaway_order', 'reservation_create', 'goodbye_close'],
  stt_provider: 'deepgram',
  stt_model: 'flux-general-multi',
  llm_provider: 'anthropic',
  llm_model: 'claude-3-5-haiku-latest',
  tts_provider: 'google',
  tts_model: 'gemini-2.5-flash-tts',
  tts_voice: 'Kore',
  greeting_line: 'Hallo, Sie sprechen mit der KI-Assistentin. Wie kann ich Ihnen helfen?',
  knowledge_notes: '',
  tools: ['faq', 'get_menu', 'create_order', 'create_reservation', 'end_call'],
  phone_number: '',
  websocket_route: '/ws/headless',
};

export default function NewTenantPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<WizardState>(DEFAULT_FORM);
  const [capabilities, setCapabilities] = useState<CapabilitySummary[]>([]);
  const [providers, setProviders] = useState<ProviderCatalog>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validated, setValidated] = useState(false);

  useEffect(() => {
    (async () => {
      const [capRes, providerRes] = await Promise.all([
        fetch(`/api/builder/capabilities?industry=${form.industry}`),
        fetch('/api/builder/providers'),
      ]);
      if (!capRes.ok) throw new Error(`Capabilities HTTP ${capRes.status}`);
      if (!providerRes.ok) throw new Error(`Providers HTTP ${providerRes.status}`);
      const capData = await capRes.json().catch(() => ({}));
      const providerData = await providerRes.json().catch(() => ({}));
      setCapabilities(capData.packs?.[0]?.capabilities ?? []);
      setProviders(providerData.providers ?? {});
    })().catch((e) => setError(e instanceof Error ? e.message : 'Failed to load builder metadata'));
  }, [form.industry]);

  const yamlPreview = useMemo(() => buildYaml(form), [form]);

  const update = (patch: Partial<WizardState>) => setForm((f) => ({ ...f, ...patch }));

  const providerModels = (kind: 'stt' | 'llm' | 'tts', providerId: string) => (
    providers?.[kind]?.find((p) => p.id === providerId)?.models ?? []
  );

  const validate = async (): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/builder/tenants/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ yaml: yamlPreview }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      setValidated(true);
      return true;
    } catch (e) {
      setValidated(false);
      setError(e instanceof Error ? e.message : 'Validation failed');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const createTenant = async () => {
    const valid = await validate();
    if (!valid) return;
    setLoading(true);
    try {
      const res = await fetch('/api/builder/tenants', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: form.tenant_id, yaml: yamlPreview }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      router.push(`/builder?tenant=${form.tenant_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen bg-gray-50 flex overflow-hidden">
      <aside className="w-72 bg-white border-r border-brand-cream p-4 overflow-y-auto">
        <h1 className="text-lg font-black text-brand-navy">New Voice Agent</h1>
        <p className="text-xs text-brand-muted mb-5">A-Z production readiness wizard</p>
        <Link
          href="/builder"
          className="block mb-4 px-3 py-2 border border-brand-cream rounded text-center text-xs font-bold text-brand-muted hover:text-brand-pink"
        >
          Back to Debugger
        </Link>
        <div className="space-y-1">
          {STEPS.map((label, i) => (
            <button
              key={label}
              onClick={() => setStep(i)}
              className={`w-full text-left px-3 py-2 rounded text-xs font-bold ${step === i ? 'bg-brand-pink text-white' : i < step ? 'bg-green-50 text-green-700' : 'hover:bg-gray-100 text-brand-navy'}`}
            >
              <span className="inline-block w-5">{i < step ? '✓' : i + 1}</span>{label}
            </button>
          ))}
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto grid grid-cols-[1fr_360px] gap-5">
          <section className="bg-white border border-brand-cream rounded-2xl p-5 shadow-sm">
            <h2 className="text-xl font-black text-brand-navy mb-1">{STEPS[step]}</h2>
            <p className="text-xs text-brand-muted mb-5">{stepHelp(step)}</p>
            {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700 mb-4">{error}</div>}

            {step === 0 && (
              <Grid>
                <Field label="Tenant ID"><input className="input" value={form.tenant_id} onChange={(e) => update({ tenant_id: e.target.value })} placeholder="doboo_clone" /></Field>
                <Field label="Industry"><select className="input" value={form.industry} onChange={(e) => update({ industry: e.target.value })}><option value="restaurant">Restaurant</option><option value="hospitality">Hospitality</option><option value="hotel">Hotel</option><option value="car_dealership">Car dealership</option><option value="construction_trades">Construction / trades</option><option value="medical_practice">Medical practice</option><option value="smb_support">SMB support</option><option value="other_custom">Other / custom</option></select></Field>
                <Field label="Language"><select className="input" value={form.language} onChange={(e) => update({ language: e.target.value })}><option value="de">Deutsch</option><option value="en">English</option><option value="fr">Français</option></select></Field>
              </Grid>
            )}

            {step === 1 && (
              <Grid>
                <Field label="Business name"><input className="input" value={form.name} onChange={(e) => update({ name: e.target.value })} /></Field>
                <Field label="Phone"><input className="input" value={form.phone} onChange={(e) => update({ phone: e.target.value })} /></Field>
                <Field label="City"><input className="input" value={form.city} onChange={(e) => update({ city: e.target.value })} /></Field>
                <Field label="Address"><input className="input" value={form.address} onChange={(e) => update({ address: e.target.value })} /></Field>
                <Field label="Opening hours"><textarea className="input min-h-24" value={form.hours} onChange={(e) => update({ hours: e.target.value })} /></Field>
              </Grid>
            )}

            {step === 2 && (
              <Checklist items={capabilities.map((c) => ({ id: c.id, label: c.name, help: c.description }))} selected={form.capabilities} onChange={(capabilities) => update({ capabilities })} />
            )}

            {step === 3 && (
              <Grid>
                <ProviderSelect label="STT provider" kind="stt" value={form.stt_provider} providers={providers} onChange={(v) => update({ stt_provider: v, stt_model: providerModels('stt', v)[0]?.id || '' })} />
                <ModelSelect label="STT model" models={providerModels('stt', form.stt_provider)} value={form.stt_model} onChange={(v) => update({ stt_model: v })} />
                <ProviderSelect label="LLM provider" kind="llm" value={form.llm_provider} providers={providers} onChange={(v) => update({ llm_provider: v, llm_model: providerModels('llm', v)[0]?.id || '' })} />
                <ModelSelect label="LLM model" models={providerModels('llm', form.llm_provider)} value={form.llm_model} onChange={(v) => update({ llm_model: v })} />
                <ProviderSelect label="TTS provider" kind="tts" value={form.tts_provider} providers={providers} onChange={(v) => update({ tts_provider: v, tts_model: providerModels('tts', v)[0]?.id || '' })} />
                <ModelSelect label="TTS model" models={providerModels('tts', form.tts_provider)} value={form.tts_model} onChange={(v) => update({ tts_model: v })} />
              </Grid>
            )}

            {step === 4 && (
              <Grid>
                <Field label="TTS voice"><input className="input" value={form.tts_voice} onChange={(e) => update({ tts_voice: e.target.value })} /></Field>
                <Field label="Greeting line"><textarea className="input min-h-24" value={form.greeting_line} onChange={(e) => update({ greeting_line: e.target.value })} /></Field>
              </Grid>
            )}

            {step === 5 && <Field label="Knowledge notes / files to upload"><textarea className="input min-h-48" value={form.knowledge_notes} onChange={(e) => update({ knowledge_notes: e.target.value })} placeholder="Menu PDFs, FAQ docs, policy docs, CSVs…" /></Field>}

            {step === 6 && <Checklist items={['faq', 'get_menu', 'create_order', 'create_reservation', 'modify_order', 'cancel_order', 'order_status', 'modify_reservation', 'cancel_reservation', 'capture_catering_lead', 'transfer_to_human', 'end_call'].map((id) => ({ id, label: id }))} selected={form.tools} onChange={(tools) => update({ tools })} />}

            {step === 7 && (
              <Grid>
                <Field label="Phone number"><input className="input" value={form.phone_number} onChange={(e) => update({ phone_number: e.target.value })} /></Field>
                <Field label="Websocket route"><input className="input" value={form.websocket_route} onChange={(e) => update({ websocket_route: e.target.value })} /></Field>
              </Grid>
            )}

            {step === 8 && <GeneratedList title="Generated mandatory scenarios" items={form.capabilities.map((id) => `${form.industry}_${id}_smoke`)} />}
            {step === 9 && <Readiness checklist={['Run mandatory scenarios', 'Verify create_order/readback', 'Verify create_reservation/readback', 'Verify escalation/handoff']} />}
            {step === 10 && <Readiness checklist={['Write tenant YAML', 'Refresh runtime registry', 'Restart selected worker', 'Check health endpoint']} />}
            {step === 11 && (
              <div className="space-y-4">
                <Readiness checklist={['Provider secrets configured', 'Tenant YAML validates', 'Capabilities selected', 'Phone/websocket route configured', 'Mandatory scenarios pass', 'Human fallback configured', 'Logs/metrics visible', 'Rollback available']} />
                <div className="flex gap-2">
                  <button onClick={validate} disabled={loading} className="px-3 py-2 border border-brand-cream rounded text-xs font-bold">Validate</button>
                  <button onClick={createTenant} disabled={loading || !form.tenant_id} className="px-3 py-2 bg-green-600 text-white rounded text-xs font-bold">
                    {loading ? <Loader size={13} className="inline animate-spin mr-1" /> : <Rocket size={13} className="inline mr-1" />} Create tenant
                  </button>
                  {validated && <span className="text-xs text-green-700 flex items-center"><CheckCircle size={14} className="mr-1" /> YAML valid</span>}
                </div>
              </div>
            )}

            <div className="flex justify-between pt-5 mt-5 border-t border-brand-cream">
              <button disabled={step === 0} onClick={() => setStep((s) => Math.max(0, s - 1))} className="px-3 py-2 border border-brand-cream rounded text-xs font-bold disabled:opacity-40"><ChevronLeft size={13} className="inline mr-1" /> Back</button>
              <button disabled={step === STEPS.length - 1} onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))} className="px-3 py-2 bg-brand-pink text-white rounded text-xs font-bold disabled:opacity-40">Next <ChevronRight size={13} className="inline ml-1" /></button>
            </div>
          </section>

          <aside className="bg-gray-900 rounded-2xl p-4 text-green-300 text-[11px] font-mono overflow-y-auto max-h-[calc(100vh-3rem)]">
            <div className="text-white font-sans font-bold text-xs mb-2">Live YAML preview</div>
            <pre>{yamlPreview}</pre>
          </aside>
        </div>
      </main>

      <style jsx>{`
        .input { width: 100%; border: 1px solid #eaded7; border-radius: 0.5rem; padding: 0.5rem 0.75rem; font-size: 0.75rem; outline: none; }
        .input:focus { border-color: #d9468f; }
      `}</style>
    </div>
  );
}

function buildYaml(form: WizardState): string {
  const q = (value: string) => `"${value.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n')}"`;
  const restaurantName = form.industry === 'restaurant' ? `restaurant_name: ${q(form.name)}\ncuisine_type: ${q('Configured via Builder')}` : '';
  return `tenant_id: ${form.tenant_id || 'new_tenant'}\nindustry: ${form.industry}\ntwilio_numbers:${form.phone_number ? `\n  - ${q(form.phone_number)}` : ' []'}\nsystem_prompt: |\n  You are the production voice agent for ${form.name || 'this business'}.\n  Enabled capabilities: ${form.capabilities.join(', ')}.\nvoice: ${q(form.tts_voice)}\nmodel: ${q(form.llm_model)}\nprovider_config:\n  stt:\n    provider: ${q(form.stt_provider)}\n    model: ${q(form.stt_model)}\n  llm:\n    provider: ${q(form.llm_provider)}\n    model: ${q(form.llm_model)}\n  tts:\n    provider: ${q(form.tts_provider)}\n    model: ${q(form.tts_model)}\npractice:\n  name: ${q(form.name)}\n  location: ${q(`${form.address}, ${form.city}`)}\n  phone: ${q(form.phone)}\n  hours: ${q(form.hours)}\nlocale: ${q(form.language === 'de' ? 'de-DE' : 'en-US')}\nlanguage: ${q(form.language)}\ntts:\n  tts_provider: ${q(form.tts_provider)}\n  model: ${q(form.tts_model)}\n  voice: ${q(form.tts_voice)}\n  language_code: ${q(form.language === 'de' ? 'de-DE' : 'en-US')}\naudio:\n  stt_provider: ${q(form.stt_provider)}\n  stt_model: ${q(form.stt_model)}\n  stt_endpointing_ms: 700\n  smart_format: true\ngreeting_line: ${q(form.greeting_line)}\nfarewell_text: ${q('Vielen Dank für Ihren Anruf. Auf Wiederhören.')}\n${restaurantName}\ncapabilities:\n${form.capabilities.map((id) => `  - ${id}`).join('\n')}\ntools:\n${form.tools.map((name) => `  - name: ${name}\n    description: ${q(`${name} tool`)}\n    parameters: {}`).join('\n')}\nruntime:\n  websocket_route: ${q(form.websocket_route)}\nproduction_readiness:\n  provider_secrets_configured: false\n  mandatory_scenarios_passed: false\n  human_fallback_configured: ${form.tools.includes('transfer_to_human')}\n`;
}

function stepHelp(step: number) {
  return [
    'Choose a reusable industry pack.',
    'Configure the business identity and locations.',
    'Pick what this agent should be able to do.',
    'Choose STT, LLM, and TTS providers/models.',
    'Set voice, language, and first audible message.',
    'Plan knowledge files and structured data.',
    'Attach built-in and custom tools.',
    'Configure phone and websocket routing.',
    'Generate mandatory smoke scenarios.',
    'Run the scenario suite before deploy.',
    'Prepare runtime deployment.',
    'Validate production readiness.',
  ][step];
}

function Grid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-4">{children}</div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="block text-[10px] font-black uppercase tracking-widest text-brand-muted mb-1">{label}</span>{children}</label>;
}

function ProviderSelect({ label, kind, value, providers, onChange }: { label: string; kind: keyof ProviderCatalog; value: string; providers: ProviderCatalog; onChange: (value: string) => void }) {
  return <Field label={label}><select className="input" value={value} onChange={(e) => onChange(e.target.value)}>{(providers?.[kind] ?? []).map((p) => <option key={p.id} value={p.id}>{p.label}{p.configured ? ' (configured)' : ''}</option>)}</select></Field>;
}

function ModelSelect({ label, models, value, onChange }: { label: string; models: ProviderModel[]; value: string; onChange: (value: string) => void }) {
  return <Field label={label}><select className="input" value={value} onChange={(e) => onChange(e.target.value)}>{models.map((m) => <option key={m.id} value={m.id}>{m.label} · {m.latency_class}</option>)}</select></Field>;
}

function Checklist({ items, selected, onChange }: { items: { id: string; label: string; help?: string }[]; selected: string[]; onChange: (next: string[]) => void }) {
  return <div className="space-y-2">{items.map((item) => <label key={item.id} className="flex gap-2 p-2 border border-brand-cream rounded hover:bg-gray-50"><input type="checkbox" checked={selected.includes(item.id)} onChange={(e) => onChange(e.target.checked ? [...selected, item.id] : selected.filter((id) => id !== item.id))} /><span><span className="block text-xs font-bold text-brand-navy">{item.label}</span>{item.help && <span className="block text-[10px] text-brand-muted">{item.help}</span>}</span></label>)}</div>;
}

function GeneratedList({ title, items }: { title: string; items: string[] }) {
  return <div><p className="text-xs font-bold text-brand-navy mb-2">{title}</p><div className="space-y-1">{items.map((item) => <div key={item} className="px-2 py-1.5 bg-green-50 border border-green-200 rounded text-xs font-mono text-green-800">{item}</div>)}</div></div>;
}

function Readiness({ checklist }: { checklist: string[] }) {
  return <div className="space-y-2">{checklist.map((item) => <div key={item} className="flex items-center gap-2 text-xs text-brand-navy"><span className="w-4 h-4 rounded-full bg-gray-100 border border-gray-300" />{item}</div>)}</div>;
}
