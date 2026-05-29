'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Mic2,
  MicOff,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Phone,
  PhoneOff,
  Volume2,
  ArrowRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ── Types ─────────────────────────────────────────────────────────────────────

type DemoState = 'idle' | 'connecting' | 'connected' | 'error';

interface TranscriptEntry {
  id: number;
  speaker: 'user' | 'bot' | 'system';
  text: string;
  ts: number;
}

interface AvailabilityState {
  unavailable: boolean;
  reason: 'validation' | 'maintenance' | null;
  message: string;
  submessage: string;
  countdownTarget: Date | null;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const DEMO_CALL_SID_STORAGE_KEY = 'saillyDemoCallSid';

const VOICES = [
  { id: 'Kore',   label: 'Kore',   gender: 'Weiblich', description: 'Klar & professionell' },
  { id: 'Puck',   label: 'Puck',   gender: 'Männlich', description: 'Freundlich & energetisch' },
  { id: 'Charon', label: 'Charon', gender: 'Männlich', description: 'Tief & ausdrucksstark' },
  { id: 'Fenrir', label: 'Fenrir', gender: 'Männlich', description: 'Strukturiert & expressiv' },
  { id: 'Zephyr', label: 'Zephyr', gender: 'Weiblich', description: 'Sanft & beruhigend' },
];

const STYLES = [
  { id: 'warm',         label: 'Warm' },
  { id: 'professional', label: 'Professionell' },
  { id: 'cheerful',     label: 'Fröhlich' },
];

const INDUSTRY_ICONS: Record<string, string> = {
  restaurant: '🍜',
  hotel:      '🏨',
  medical:    '🏥',
  services:   '🔧',
  beauty:     '💅',
  retail:     '🛍️',
  banking:    '🏦',
};

const INDUSTRY_LABELS: Record<string, string> = {
  restaurant: 'Restaurant',
  hotel:      'Hotel',
  medical:    'Praxis / Medizin',
  services:   'Dienstleistungen',
  beauty:     'Beauty & Wellness',
  retail:     'Einzelhandel',
  banking:    'Finanzdienstleistungen',
};

// Static fallback tenants — dynamically extended from API when available
const FALLBACK_TENANTS = [
  { id: 'doboo',        label: 'DOBOO Korean Soulfood', industry: 'restaurant' },
  { id: 'hotel-demo',   label: 'Motel One Bonn',        industry: 'hotel' },
  { id: 'praxis-demo',  label: 'Praxis Demo',           industry: 'medical' },
  { id: 'services-kmu', label: 'Beauty & Nails',        industry: 'services' },
];

interface TenantOption {
  id: string;
  label: string;
  industry: string;
}

// ── AudioWorklet source (inlined) ─────────────────────────────────────────────

const WORKLET_CODE = `
class PCM16Processor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buf = [];
    this._len = 0;
    this._chunkCount = 0;
  }
  process(inputs) {
    const channel = inputs[0]?.[0];
    if (channel && channel.length > 0) {
      for (let i = 0; i < channel.length; i++) {
        this._buf.push(channel[i]);
        this._len++;
      }
      if (this._len >= 320) {
        const pcm = new Int16Array(this._len);
        for (let i = 0; i < this._len; i++) {
          const c = Math.max(-1, Math.min(1, this._buf[i]));
          pcm[i] = c < 0 ? c * 32768 : c * 32767;
        }
        const chunkId = this._chunkCount % 1000000;
        this._chunkCount++;
        const wrapper = new ArrayBuffer(4 + pcm.buffer.byteLength);
        const view = new DataView(wrapper);
        view.setUint32(0, chunkId, true);
        new Uint8Array(wrapper, 4).set(new Uint8Array(pcm.buffer));
        this.port.postMessage(wrapper, [wrapper]);
        this._buf = [];
        this._len = 0;
      }
    }
    return true;
  }
}
registerProcessor('pcm16-processor', PCM16Processor);
`;

// ── Helpers ───────────────────────────────────────────────────────────────────

function getWsBase(): string {
  if (typeof window === 'undefined') return 'wss://sailly.tech';
  const base = process.env.NEXT_PUBLIC_VOICE_AGENT_WSS;
  if (base) return base.replace(/\/$/, '');
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.hostname}`;
}

// ── Sailly CSS Orb (no Three.js dependency) ───────────────────────────────────

function SaillyOrb({ state }: { state: DemoState | 'bot-speaking' }) {
  const isActive = state === 'connected' || state === 'bot-speaking';
  const isSpeaking = state === 'bot-speaking';
  const isConnecting = state === 'connecting';

  return (
    <div className="relative w-16 h-16 flex items-center justify-center">
      {/* Outer glow rings when active */}
      {isActive && (
        <>
          <div
            className="absolute inset-0 rounded-full opacity-30"
            style={{
              background: 'radial-gradient(circle, #ff9b8a 0%, transparent 70%)',
              animation: 'sailly-ring 2s ease-in-out infinite',
              transform: 'scale(1.6)',
            }}
          />
          <div
            className="absolute inset-0 rounded-full opacity-20"
            style={{
              background: 'radial-gradient(circle, #ffb6cb 0%, transparent 70%)',
              animation: 'sailly-ring 2s ease-in-out infinite 0.5s',
              transform: 'scale(1.4)',
            }}
          />
        </>
      )}
      {/* Core orb */}
      <div
        className="w-14 h-14 rounded-full shadow-lg"
        style={{
          background: 'linear-gradient(135deg, #ff9b8a 0%, #ffb6cb 50%, #ffc8b9 100%)',
          animation: isConnecting
            ? 'sailly-pulse 1s ease-in-out infinite'
            : isSpeaking
            ? 'sailly-speak 0.8s ease-in-out infinite alternate'
            : 'sailly-idle 4s ease-in-out infinite',
          boxShadow: isActive
            ? '0 0 20px rgba(255, 155, 138, 0.5)'
            : '0 4px 12px rgba(255, 155, 138, 0.3)',
        }}
      />
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function DemoCallPage() {
  const [selectedVoice, setSelectedVoice]   = useState(VOICES[0].id);
  const [selectedStyle, setSelectedStyle]   = useState(STYLES[0].id);
  const [selectedTenant, setSelectedTenant] = useState(FALLBACK_TENANTS[0].id);
  const [tenants, setTenants] = useState<TenantOption[]>(FALLBACK_TENANTS);

  // Fetch available tenants from backend API on mount
  useEffect(() => {
    fetch('/api/demo/tenants')
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data && Array.isArray(data.tenants) && data.tenants.length > 0) {
          // API returns { id, name, industry } — map name → label for TenantOption
          setTenants(data.tenants.map((t: { id: string; name?: string; label?: string; industry: string }) => ({
            id: t.id,
            label: t.label || t.name || t.id,
            industry: t.industry,
          })));
        }
      })
      .catch(() => { /* keep fallback list */ });
  }, []);

  const [demoState, setDemoState] = useState<DemoState>('idle');
  const [error, setError]         = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [isBotSpeaking, setIsBotSpeaking] = useState(false);
  const [isMuted, setIsMuted]     = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [availability, setAvailability] = useState<AvailabilityState>({
    unavailable: false, reason: null, message: '', submessage: '', countdownTarget: null,
  });
  const [countdown, setCountdown] = useState('');

  // auto-run state
  const [autoRunAD,   setAutoRunAD]   = useState(false);
  const [autoRunEEnd, setAutoRunEEnd] = useState(false);

  const wsRef             = useRef<WebSocket | null>(null);
  const recordingCtxRef   = useRef<AudioContext | null>(null);
  const playbackCtxRef    = useRef<AudioContext | null>(null);
  const workletNodeRef    = useRef<AudioWorkletNode | null>(null);
  const micStreamRef      = useRef<MediaStream | null>(null);
  const transcriptIdRef   = useRef(0);
  const transcriptEndRef  = useRef<HTMLDivElement | null>(null);
  const gainNodeRef       = useRef<GainNode | null>(null);
  const nextPlayTimeRef   = useRef<number>(0);
  const echoGateTimerRef  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMutedRef        = useRef(false);
  const callEndedDrainRef = useRef(false);

  // stable refs so interval callbacks always see the latest values
  const autoRunADIntervalRef   = useRef<ReturnType<typeof setInterval> | null>(null);
  const autoRunEEndIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startCallRef  = useRef<(() => Promise<void>) | null>(null);
  const stopCallRef   = useRef<((updateState?: boolean) => void) | null>(null);
  const demoStateRef  = useRef<DemoState>('idle');

  useEffect(() => {
    // Scroll only within the transcript container, not the window
    if (transcriptEndRef.current) {
      const transcriptContainer = transcriptEndRef.current.closest('div[style*="overflow-y"]');
      if (transcriptContainer) {
        transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
      }
    }
  }, [transcript]);

  useEffect(() => {
    let cancelled = false;
    async function checkAvailability() {
      try {
        const res = await fetch('/validation/demo_availability.json?_=' + Date.now());
        if (res.ok) {
          const d = await res.json();
          if (d.validation_running) {
            if (!cancelled) setAvailability({
              unavailable: true, reason: 'validation',
              message: 'Demo Calls vorübergehend pausiert',
              submessage: d.phase || 'Validierungslauf läuft — gleich wieder verfügbar.',
              countdownTarget: d.estimated_end ? new Date(d.estimated_end) : null,
            });
            return;
          }
        }
      } catch { /* ignore */ }
      if (!cancelled) setAvailability({ unavailable: false, reason: null, message: '', submessage: '', countdownTarget: null });
    }
    checkAvailability();
    const iv = setInterval(checkAvailability, 15_000);
    return () => { cancelled = true; clearInterval(iv); };
  }, []);

  useEffect(() => {
    if (!availability.countdownTarget) { setCountdown(''); return; }
    function tick() {
      const diff = availability.countdownTarget!.getTime() - Date.now();
      if (diff <= 0) { setCountdown('gleich'); return; }
      const h = Math.floor(diff / 3600000);
      const mn = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setCountdown(h > 0 ? `${h}h ${mn}m` : mn > 0 ? `${mn}m ${s}s` : `${s}s`);
    }
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, [availability.countdownTarget]);

  // Auto-run interval for A-D (120 seconds)
  useEffect(() => {
    if (!autoRunAD) {
      if (autoRunADIntervalRef.current) {
        clearInterval(autoRunADIntervalRef.current);
        autoRunADIntervalRef.current = null;
      }
      return;
    }
    const triggerCall = () => {
      const s = demoStateRef.current;
      if (s === 'connected' || s === 'connecting') {
        if (stopCallRef.current) stopCallRef.current();
        setTimeout(() => { if (startCallRef.current) startCallRef.current(); }, 500);
      } else {
        if (startCallRef.current) startCallRef.current();
      }
    };
    triggerCall();
    autoRunADIntervalRef.current = setInterval(triggerCall, 120_000);
    return () => {
      if (autoRunADIntervalRef.current) {
        clearInterval(autoRunADIntervalRef.current);
        autoRunADIntervalRef.current = null;
      }
    };
  }, [autoRunAD]);

  // Auto-run interval for E-end (180 seconds)
  useEffect(() => {
    if (!autoRunEEnd) {
      if (autoRunEEndIntervalRef.current) {
        clearInterval(autoRunEEndIntervalRef.current);
        autoRunEEndIntervalRef.current = null;
      }
      return;
    }
    const triggerCall = () => {
      const s = demoStateRef.current;
      if (s === 'connected' || s === 'connecting') {
        if (stopCallRef.current) stopCallRef.current();
        setTimeout(() => { if (startCallRef.current) startCallRef.current(); }, 500);
      } else {
        if (startCallRef.current) startCallRef.current();
      }
    };
    triggerCall();
    autoRunEEndIntervalRef.current = setInterval(triggerCall, 180_000);
    return () => {
      if (autoRunEEndIntervalRef.current) {
        clearInterval(autoRunEEndIntervalRef.current);
        autoRunEEndIntervalRef.current = null;
      }
    };
  }, [autoRunEEnd]);

  const addTranscript = useCallback((speaker: TranscriptEntry['speaker'], text: string) => {
    setTranscript(prev => [...prev, { id: ++transcriptIdRef.current, speaker, text, ts: Date.now() }]);
  }, []);

  const playPCM16 = useCallback((data: ArrayBuffer) => {
    const ctx = playbackCtxRef.current;
    if (!ctx) return;
    const pcm16 = new Int16Array(data);
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) float32[i] = pcm16[i] / 32768;
    const buffer = ctx.createBuffer(1, float32.length, 24000);
    buffer.getChannelData(0).set(float32);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    const now = ctx.currentTime;
    const startAt = Math.max(now + 0.02, nextPlayTimeRef.current);
    source.start(startAt);
    nextPlayTimeRef.current = startAt + buffer.duration;
    const recCtx = recordingCtxRef.current;
    if (gainNodeRef.current && recCtx) {
      gainNodeRef.current.gain.cancelScheduledValues(recCtx.currentTime);
      gainNodeRef.current.gain.setValueAtTime(0.05, recCtx.currentTime);
    }
    setIsBotSpeaking(true);
    if (echoGateTimerRef.current) clearTimeout(echoGateTimerRef.current);
    const msUntilEnd = Math.max(0, (nextPlayTimeRef.current - ctx.currentTime) * 1000);
    echoGateTimerRef.current = setTimeout(() => {
      setIsBotSpeaking(false);
      const rc = recordingCtxRef.current;
      if (gainNodeRef.current && rc && !isMutedRef.current)
        gainNodeRef.current.gain.linearRampToValueAtTime(1, rc.currentTime + 0.05);
      echoGateTimerRef.current = null;
    }, msUntilEnd + 800);
  }, []);

  const startMicCapture = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    micStreamRef.current = stream;
    const ctx = new AudioContext({ sampleRate: 16000 });
    recordingCtxRef.current = ctx;
    await ctx.audioWorklet.addModule('/pcm16-processor.js');
    const source = ctx.createMediaStreamSource(stream);
    const gain = ctx.createGain();
    gainNodeRef.current = gain;
    gain.gain.value = 1;
    const worklet = new AudioWorkletNode(ctx, 'pcm16-processor');
    workletNodeRef.current = worklet;
    worklet.port.onmessage = (e: MessageEvent) => {
      if (e.data instanceof ArrayBuffer) {
        const audioData = e.data.slice(4);
        if (wsRef.current?.readyState === WebSocket.OPEN && !isMutedRef.current)
          wsRef.current.send(audioData);
      }
    };
    source.connect(gain);
    gain.connect(worklet);
  }, []);

  const toggleMute = useCallback(() => {
    setIsMuted(prev => {
      const next = !prev;
      isMutedRef.current = next;
      if (gainNodeRef.current && !isBotSpeaking)
        gainNodeRef.current.gain.value = next ? 0 : 1;
      return next;
    });
  }, [isBotSpeaking]);

  const toggleAutoRunAD   = useCallback(() => setAutoRunAD(v => !v),   []);
  const toggleAutoRunEEnd = useCallback(() => setAutoRunEEnd(v => !v), []);

  const drainPlaybackBeforeClose = useCallback(async () => {
    const ctx = playbackCtxRef.current;
    if (ctx) {
      const queuedMs = Math.max(0, (nextPlayTimeRef.current - ctx.currentTime) * 1000);
      const waitMs = Math.min(12_000, queuedMs + 1_000);
      if (waitMs > 0) await new Promise(resolve => setTimeout(resolve, waitMs));
      if (playbackCtxRef.current === ctx) {
        playbackCtxRef.current.close().catch(() => {});
        playbackCtxRef.current = null;
      }
    }
    nextPlayTimeRef.current = 0;
  }, []);

  const stopCall = useCallback((updateState = true, closePlayback = true) => {
    if (updateState) setDemoState('idle');
    if (updateState) sessionStorage.removeItem(DEMO_CALL_SID_STORAGE_KEY);
    setIsDarkMode(false);
    setIsBotSpeaking(false);
    setIsMuted(false);
    isMutedRef.current = false;
    if (echoGateTimerRef.current) { clearTimeout(echoGateTimerRef.current); echoGateTimerRef.current = null; }
    if (wsRef.current) { try { wsRef.current.send(JSON.stringify({ type: 'stop' })); } catch { } wsRef.current.close(); wsRef.current = null; }
    if (workletNodeRef.current) { workletNodeRef.current.disconnect(); workletNodeRef.current = null; }
    if (micStreamRef.current) { micStreamRef.current.getTracks().forEach(t => t.stop()); micStreamRef.current = null; }
    if (recordingCtxRef.current) { recordingCtxRef.current.close().catch(() => {}); recordingCtxRef.current = null; }
    if (closePlayback && playbackCtxRef.current) { playbackCtxRef.current.close().catch(() => {}); playbackCtxRef.current = null; }
    if (closePlayback) nextPlayTimeRef.current = 0;
  }, []);

  const handleCallEnded = useCallback(() => {
    if (callEndedDrainRef.current) return;
    callEndedDrainRef.current = true;
    stopCall(true, false);
    drainPlaybackBeforeClose().finally(() => {
      callEndedDrainRef.current = false;
    });
  }, [drainPlaybackBeforeClose, stopCall]);

  const startCall = useCallback(async () => {
    setError(null);
    setTranscript([]);
    setDemoState('connecting');

    // AudioContext MUST be created synchronously here, while the browser's user-gesture
    // activation (button click → startCall) is still live. Creating it inside ws.onopen
    // (which fires asynchronously after a network event) causes the context to start in
    // 'suspended' state in Chrome and permanently suspended in Safari — so audio frames
    // arrive, are scheduled via source.start(), but never actually play.
    if (playbackCtxRef.current) {
      playbackCtxRef.current.close().catch(() => {});
      playbackCtxRef.current = null;
    }
    const pbCtx = new AudioContext({ sampleRate: 24000 });
    playbackCtxRef.current = pbCtx;
    nextPlayTimeRef.current = 0;
    // Call resume() synchronously while still in the gesture context (critical for Safari).
    pbCtx.resume().catch(() => {});

    try {
      const ws = new WebSocket(`${getWsBase()}/ws/demo/`);
      wsRef.current = ws;
      ws.binaryType = 'arraybuffer';
      ws.onopen = async () => {
        try {
          const savedCallSid = sessionStorage.getItem(DEMO_CALL_SID_STORAGE_KEY);
          ws.send(JSON.stringify({
            tenant: selectedTenant,
            voice: selectedVoice,
            style: selectedStyle,
            call_sid: savedCallSid || undefined,
          }));
          // AudioContext already created above — just ensure it's running after the
          // async network round-trip (handles edge cases where browser needs a nudge).
          if (pbCtx.state === 'suspended') {
            await pbCtx.resume().catch(() => {});
          }
          nextPlayTimeRef.current = pbCtx.currentTime;
          // Request mic access here — after WS is open, so user sees "connecting" first
          try {
            await startMicCapture();
          } catch (micErr) {
            const msg = micErr instanceof Error ? micErr.message : String(micErr);
            let hint = '';
            if (msg.includes('Permission denied') || msg.includes('NotAllowedError'))
              hint = ' — Klicken Sie auf das Schloss-Symbol in der Adresszeile und erlauben Sie den Mikrofonzugriff für diese Seite.';
            else if (msg.includes('NotFoundError'))
              hint = ' — Kein Mikrofon gefunden. Bitte schließen Sie ein Mikrofon an.';
            else if (msg.includes('NotReadableError') || msg.includes('Could not start audio source'))
              hint = ' — Das Mikrofon wird von einer anderen App verwendet. Bitte schließen Sie andere Apps (z.B. Zoom, Teams) und versuchen Sie es erneut.';
            else
              hint = ' — Bitte erlauben Sie Mikrofonzugriff im Browser und stellen Sie sicher, dass ein Mikrofon angeschlossen ist.';
            setError(`Mikrofon konnte nicht gestartet werden: ${hint.slice(3)}`);
            setDemoState('error');
            ws.close();
            return;
          }
          if (recordingCtxRef.current) await recordingCtxRef.current.resume();
          setDemoState('connected');
          setIsDarkMode(true);
        } catch (err) {
          setError(`Fehler: ${err instanceof Error ? err.message : 'Unbekannter Fehler'}`);
          setDemoState('error');
          ws.close();
        }
      };
      ws.onmessage = (event: MessageEvent) => {
        if (event.data instanceof ArrayBuffer) {
          playPCM16(event.data);
        } else if (typeof event.data === 'string') {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'call_ended') handleCallEnded();
            else if (msg.type === 'session_init' && msg.call_sid) sessionStorage.setItem(DEMO_CALL_SID_STORAGE_KEY, msg.call_sid);
            else if (msg.type === 'transcript' && msg.text) addTranscript(msg.speaker === 'user' ? 'user' : 'bot', msg.text);
            else if (msg.type === 'bot_text' && msg.text) {
              setTranscript(prev => {
                const last = prev[prev.length - 1];
                if (last?.speaker === 'bot' && Date.now() - last.ts < 3000)
                  return [...prev.slice(0, -1), { ...last, text: last.text + msg.text }];
                return [...prev, { id: ++transcriptIdRef.current, speaker: 'bot', text: msg.text!, ts: Date.now() }];
              });
            }
          } catch { }
        }
      };
      ws.onerror = () => { setError('Verbindungsfehler. Bitte erneut versuchen.'); setDemoState('error'); };
      ws.onclose = (event: CloseEvent) => {
        if (demoState === 'connected' || demoState === 'connecting') {
          if (event.code === 4401) setError('Token abgelaufen. Bitte Seite neu laden.');
          setDemoState('idle');
          setIsDarkMode(false);
        }
        if (!callEndedDrainRef.current) stopCall(false);
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
      setDemoState('error');
    }
  }, [selectedVoice, selectedStyle, selectedTenant, startMicCapture, playPCM16, addTranscript, demoState, stopCall, handleCallEnded]);

  // keep refs current so intervals always have fresh values
  useEffect(() => { startCallRef.current = startCall; }, [startCall]);
  useEffect(() => { stopCallRef.current  = stopCall;  }, [stopCall]);
  useEffect(() => { demoStateRef.current = demoState; }, [demoState]);

  useEffect(() => () => stopCall(false), [stopCall]);

  const isActive     = demoState === 'connected';
  const isConnecting = demoState === 'connecting';
  const selectedTenantObj = tenants.find(t => t.id === selectedTenant) || tenants[0];
  const orbState = isConnecting ? 'connecting' : isBotSpeaking ? 'bot-speaking' : isActive ? 'connected' : 'idle';

  return (
    <div
      className="min-h-screen font-sans transition-all duration-500 overflow-y-auto"
      style={{ 
        background: isDarkMode ? 'linear-gradient(145deg, #050810 0%, #1a2230 100%)' : 'linear-gradient(145deg, #fff8f5 0%, #fef0e8 100%)',
        scrollbarGutter: 'stable'
      }}
    >
      {/* Page header */}
      <div className="max-w-6xl mx-auto px-6 pt-8 pb-6 text-center">
        <h1 className="text-3xl font-bold" style={{ color: isDarkMode ? '#f0f0f0' : '#1a1a2e' }}>
          KI Sprachagent — Live Demo
        </h1>
        <p className="mt-2 text-base" style={{ color: isDarkMode ? '#a0aec0' : '#64748b' }}>
          Sprechen Sie direkt im Browser mit dem KI-Agenten. Keine App, kein Telefon.
        </p>
      </div>

      <main className="max-w-6xl mx-auto px-6 pb-10 grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">

        {/* ── Left: Phone UI (sailly.de style) ──────────────────────────────── */}
        <div className="flex justify-center">
          {/* Glass card phone — matches sailly.de/de design */}
          <div
            className="relative w-full max-w-[360px] rounded-[2.5rem] overflow-hidden shadow-2xl transition-all duration-500"
            style={{
              background: isDarkMode ? 'rgba(18, 18, 18, 0.85)' : 'rgba(255,255,255,0.65)',
              backdropFilter: 'blur(20px)',
              WebkitBackdropFilter: 'blur(20px)',
              border: isDarkMode ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(255,255,255,0.5)',
              boxShadow: isDarkMode ? '0 20px 60px rgba(0, 0, 0, 0.4), 0 4px 20px rgba(0,0,0,0.3)' : '0 20px 60px rgba(255, 120, 100, 0.12), 0 4px 20px rgba(0,0,0,0.08)',
            }}
          >
            {/* Top pill notch */}
            <div className="flex justify-center pt-3 pb-1">
              <div className="w-12 h-1.5 rounded-full" style={{ background: 'rgba(0,0,0,0.15)' }} />
            </div>

            {/* Avatar + title */}
            <div className="flex flex-col items-center pt-4 pb-3 px-4">
              <SaillyOrb state={orbState} />
              <div className="mt-3 text-center">
                <p className="text-base font-bold" style={{ color: isDarkMode ? '#f0f0f0' : '#1a1a2e' }}>Sailly</p>
                <p
                  className="text-sm font-medium"
                  style={{
                    background: 'linear-gradient(135deg, #e60076 0%, #a020f0 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  {INDUSTRY_ICONS[selectedTenantObj?.industry || 'restaurant']} {selectedTenantObj?.label || 'Demo'} · Live Demo
                </p>
              </div>

              {/* Live status pill */}
              <div
                className="mt-2 px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1.5"
                style={{
                  background: isActive
                    ? 'rgba(0, 208, 132, 0.12)'
                    : isConnecting
                    ? 'rgba(230, 0, 118, 0.10)'
                    : 'rgba(100, 116, 139, 0.08)',
                  color: isActive ? '#00a86b' : isConnecting ? '#e60076' : '#64748b',
                  border: `1px solid ${isActive ? 'rgba(0,208,132,0.25)' : isConnecting ? 'rgba(230,0,118,0.2)' : 'rgba(100,116,139,0.15)'}`,
                }}
              >
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{
                    background: isActive ? '#00d084' : isConnecting ? '#e60076' : '#94a3b8',
                    animation: (isActive || isConnecting) ? 'sailly-pulse 1.2s ease-in-out infinite' : 'none',
                  }}
                />
                {isActive
                  ? (isBotSpeaking ? 'Sailly spricht...' : 'Hört zu...')
                  : isConnecting
                  ? 'Verbinde...'
                  : 'Bereit'}
                {isActive && (
                  <button
                    onClick={toggleMute}
                    className="ml-1 p-0.5 rounded-full transition-colors"
                    title={isMuted ? 'Stummschaltung aufheben' : 'Stummschalten'}
                  >
                    {isMuted
                      ? <MicOff size={11} />
                      : <Mic2 size={11} />}
                  </button>
                )}
              </div>
            </div>

            {/* Transcript area */}
            <div
              className="mx-3 rounded-2xl overflow-hidden transition-all duration-500"
              style={{
                background: isDarkMode ? 'rgba(30, 30, 30, 0.9)' : 'rgba(255,255,255,0.7)',
                border: isDarkMode ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(255,255,255,0.6)',
                height: 280,
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2.5">
                {transcript.filter(e => e.speaker !== 'system').length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center gap-2 text-center px-4">
                    <div className="text-2xl opacity-40">💬</div>
                    <p className="text-xs" style={{ color: isDarkMode ? '#64748b' : '#94a3b8' }}>
                      Hier erscheint die Unterhaltung...
                    </p>
                  </div>
                ) : (
                  transcript.filter(e => e.speaker !== 'system').map(entry => (
                    <div key={entry.id} className="flex flex-col">
                      <div
                        className={cn(
                          'px-3 py-2 text-xs leading-relaxed max-w-[85%] break-words',
                          entry.speaker === 'user'
                            ? 'self-end rounded-[14px] rounded-br-[4px] text-white'
                            : 'self-start rounded-[14px] rounded-bl-[4px]'
                        )}
                        style={
                          entry.speaker === 'user'
                            ? { background: 'linear-gradient(135deg, #e60076 0%, #a020f0 100%)' }
                            : isDarkMode
                            ? {
                                background: 'rgba(51, 51, 51, 0.8)',
                                color: '#e0e0e0',
                                border: '1px solid rgba(100, 100, 100, 0.3)',
                              }
                            : {
                                background: 'rgba(241,245,249,0.9)',
                                color: '#334155',
                                border: '1px solid rgba(226,232,240,0.8)',
                              }
                        }
                      >
                        {entry.text}
                      </div>
                      <span className={cn(
                        'text-[9px] mt-0.5 mx-1',
                        entry.speaker === 'user' ? 'self-end' : 'self-start'
                      )} style={{ color: isDarkMode ? '#a0aec0' : '#cbd5e1' }}>
                        {entry.speaker === 'user' ? 'Sie' : 'Sailly'}
                      </span>
                    </div>
                  ))
                )}
                <div ref={transcriptEndRef} />
              </div>
            </div>

            {/* Error message */}
            {error && (
              <div
                className="mx-3 mt-2 px-3 py-2 rounded-xl text-xs flex items-start gap-2"
                style={{ background: 'rgba(255,59,48,0.08)', color: '#dc2626', border: '1px solid rgba(255,59,48,0.2)' }}
              >
                <AlertCircle size={13} className="shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Unavailability overlay */}
            {availability.unavailable && (
              <div
                className="absolute inset-0 z-20 flex flex-col items-center justify-center px-6 text-center rounded-[2.5rem]"
                style={{ background: 'rgba(26,26,46,0.85)', backdropFilter: 'blur(8px)' }}
              >
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
                  style={{ background: '#e60076' }}
                >
                  <Loader2 size={28} color="white" className="animate-spin" />
                </div>
                <h3 className="text-lg font-bold mb-2" style={{ color: '#f5e9e4' }}>{availability.message}</h3>
                <p className="text-sm mb-4" style={{ color: '#b0c0d0' }}>{availability.submessage}</p>
                {countdown && (
                  <div
                    className="rounded-2xl px-5 py-3 text-center"
                    style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)' }}
                  >
                    <p className="text-xs uppercase tracking-wide mb-1" style={{ color: '#fec081' }}>Wieder verfügbar in</p>
                    <p className="text-2xl font-bold font-mono" style={{ color: '#f5e9e4' }}>{countdown}</p>
                  </div>
                )}
              </div>
            )}

            {/* Bottom bar — call button */}
            <div
              className="p-5 flex items-center justify-center gap-6"
              style={{ borderTop: '1px solid rgba(255,255,255,0.5)' }}
            >
              {!isActive && !isConnecting ? (
                <button
                  onClick={availability.unavailable ? undefined : startCall}
                  disabled={availability.unavailable}
                  className="w-16 h-16 rounded-full flex items-center justify-center shadow-lg transition-all hover:scale-110 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                  style={{
                    background: availability.unavailable
                      ? '#9ca3af'
                      : 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
                    boxShadow: availability.unavailable ? 'none' : '0 4px 16px rgba(34, 197, 94, 0.4)',
                  }}
                >
                  <Phone size={26} color="white" />
                </button>
              ) : (
                <button
                  onClick={() => stopCall()}
                  className="w-16 h-16 rounded-full flex items-center justify-center shadow-lg transition-all hover:scale-110 active:scale-95"
                  style={{
                    background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                    boxShadow: '0 4px 16px rgba(239, 68, 68, 0.4)',
                  }}
                >
                  {isConnecting
                    ? <Loader2 size={24} color="white" className="animate-spin" />
                    : <PhoneOff size={24} color="white" />}
                </button>
              )}
            </div>
          </div>

          {/* Auto-run buttons */}
          <div className="flex gap-3 mt-4 w-full max-w-[360px]">
            <button
              onClick={toggleAutoRunAD}
              className="flex-1 px-4 py-2.5 rounded-2xl border text-sm font-medium transition-all"
              style={{
                background:   autoRunAD ? 'rgba(230,0,118,0.12)' : 'rgba(255,255,255,0.55)',
                borderColor:  autoRunAD ? '#e60076' : 'rgba(255,255,255,0.6)',
                color:        autoRunAD ? '#e60076' : '#64748b',
                boxShadow:    autoRunAD ? '0 0 0 1.5px #e60076, 0 2px 8px rgba(230,0,118,0.08)' : '0 1px 4px rgba(0,0,0,0.05)',
                animation:    autoRunAD ? 'sailly-pulse 1.2s ease-in-out infinite' : 'none',
              }}
            >
              A-D
            </button>
            <button
              onClick={toggleAutoRunEEnd}
              className="flex-1 px-4 py-2.5 rounded-2xl border text-sm font-medium transition-all"
              style={{
                background:   autoRunEEnd ? 'rgba(230,0,118,0.12)' : 'rgba(255,255,255,0.55)',
                borderColor:  autoRunEEnd ? '#e60076' : 'rgba(255,255,255,0.6)',
                color:        autoRunEEnd ? '#e60076' : '#64748b',
                boxShadow:    autoRunEEnd ? '0 0 0 1.5px #e60076, 0 2px 8px rgba(230,0,118,0.08)' : '0 1px 4px rgba(0,0,0,0.05)',
                animation:    autoRunEEnd ? 'sailly-pulse 1.2s ease-in-out infinite' : 'none',
              }}
            >
              E-end
            </button>
          </div>
        </div>

        {/* ── Right: Settings + Info ─────────────────────────────────────── */}
        <div className="space-y-5">

          {/* Tenant / Client selection */}
          <div>
            <h2
              className="text-xs font-semibold uppercase tracking-widest mb-3 flex items-center gap-2"
              style={{ color: '#94a3b8' }}
            >
              Mandant / Client
            </h2>
            <div className="grid grid-cols-1 gap-2">
              {tenants.map(t => {
                const icon = INDUSTRY_ICONS[t.industry] || '🏢';
                const industryLabel = INDUSTRY_LABELS[t.industry] || t.industry;
                const isSelected = selectedTenant === t.id;
                return (
                  <button
                    key={t.id}
                    disabled={isActive || isConnecting}
                    onClick={() => setSelectedTenant(t.id)}
                    className="flex items-center justify-between px-4 py-3 rounded-2xl border transition-all disabled:opacity-40 text-left"
                    style={{
                      background: isSelected
                        ? 'rgba(255,255,255,0.85)'
                        : 'rgba(255,255,255,0.55)',
                      borderColor: isSelected ? '#e60076' : 'rgba(255,255,255,0.6)',
                      boxShadow: isSelected
                        ? '0 0 0 1.5px #e60076, 0 2px 8px rgba(230,0,118,0.08)'
                        : '0 1px 4px rgba(0,0,0,0.05)',
                      backdropFilter: 'blur(8px)',
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 text-lg"
                        style={{
                          background: isSelected ? 'rgba(230,0,118,0.1)' : 'rgba(255,255,255,0.7)',
                          border: '1px solid rgba(255,255,255,0.6)',
                        }}
                      >
                        {icon}
                      </div>
                      <div>
                        <div className="text-sm font-semibold" style={{ color: '#1a1a2e' }}>{t.label}</div>
                        <div className="text-xs" style={{ color: '#94a3b8' }}>{industryLabel} · {t.id}</div>
                      </div>
                    </div>
                    <ArrowRight size={14} style={{ color: isSelected ? '#e60076' : '#cbd5e1' }} />
                  </button>
                );
              })}
            </div>
          </div>

          {/* Voice selection */}
          <div>
            <h2
              className="text-xs font-semibold uppercase tracking-widest mb-3 flex items-center gap-2"
              style={{ color: '#94a3b8' }}
            >
              <Volume2 size={12} /> Stimme
            </h2>
            <div className="grid grid-cols-1 gap-2">
              {VOICES.map(v => {
                const isSelected = selectedVoice === v.id;
                return (
                  <button
                    key={v.id}
                    disabled={isActive || isConnecting}
                    onClick={() => setSelectedVoice(v.id)}
                    className="flex items-center justify-between px-4 py-3 rounded-2xl border transition-all disabled:opacity-40"
                    style={{
                      background: isSelected ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.55)',
                      borderColor: isSelected ? '#e60076' : 'rgba(255,255,255,0.6)',
                      boxShadow: isSelected
                        ? '0 0 0 1.5px #e60076, 0 2px 8px rgba(230,0,118,0.08)'
                        : '0 1px 4px rgba(0,0,0,0.05)',
                      backdropFilter: 'blur(8px)',
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                        style={{
                          background: isSelected
                            ? 'linear-gradient(135deg, #e60076 0%, #a020f0 100%)'
                            : 'rgba(255,255,255,0.7)',
                          border: '1px solid rgba(255,255,255,0.6)',
                        }}
                      >
                        <Volume2 size={13} color={isSelected ? 'white' : '#94a3b8'} />
                      </div>
                      <div className="text-left">
                        <div className="text-sm font-semibold" style={{ color: '#1a1a2e' }}>
                          {v.label} <span className="text-xs font-normal opacity-50">· {v.gender}</span>
                        </div>
                        <div className="text-xs" style={{ color: '#94a3b8' }}>{v.description}</div>
                      </div>
                    </div>
                    <div
                      className="w-2 h-2 rounded-full shrink-0 transition-opacity"
                      style={{ background: '#e60076', opacity: isSelected ? 1 : 0 }}
                    />
                  </button>
                );
              })}
            </div>
          </div>

          {/* Style selection */}
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: '#94a3b8' }}>
              Gesprächsstil
            </h2>
            <div className="grid grid-cols-3 gap-2">
              {STYLES.map(s => {
                const isSelected = selectedStyle === s.id;
                return (
                  <button
                    key={s.id}
                    disabled={isActive || isConnecting}
                    onClick={() => setSelectedStyle(s.id)}
                    className="py-2.5 px-3 rounded-2xl border text-sm font-medium transition-all disabled:opacity-40"
                    style={{
                      background: isSelected ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.55)',
                      borderColor: isSelected ? '#e60076' : 'rgba(255,255,255,0.6)',
                      color: isSelected ? '#1a1a2e' : '#64748b',
                      boxShadow: isSelected
                        ? '0 0 0 1.5px #e60076, 0 2px 8px rgba(230,0,118,0.08)'
                        : '0 1px 4px rgba(0,0,0,0.05)',
                      backdropFilter: 'blur(8px)',
                    }}
                  >
                    {s.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Features */}
          <div
            className="rounded-2xl p-5 border space-y-3"
            style={{
              background: 'rgba(255,255,255,0.65)',
              borderColor: 'rgba(255,255,255,0.6)',
              backdropFilter: 'blur(10px)',
              boxShadow: '0 1px 6px rgba(0,0,0,0.05)',
            }}
          >
            <h2 className="text-sm font-semibold" style={{ color: '#1a1a2e' }}>Features</h2>
            <ul className="space-y-1.5">
              {[
                'Echtzeit-Spracherkennung (Deepgram)',
                'KI-Sprachagent (Gemini 2.5 Flash)',
                'Natürliche Sprachsynthese (Google TTS)',
                'Kein Twilio — direkt via WebSocket',
                'Bestellungen und Reservierungen testen',
              ].map(f => (
                <li key={f} className="flex items-center gap-2 text-sm" style={{ color: '#475569' }}>
                  <CheckCircle2 size={13} style={{ color: '#e60076', flexShrink: 0 }} />
                  {f}
                </li>
              ))}
            </ul>
          </div>

          {/* Examples */}
          <div
            className="rounded-2xl p-5 border space-y-3"
            style={{
              background: 'rgba(255,255,255,0.65)',
              borderColor: 'rgba(255,255,255,0.6)',
              backdropFilter: 'blur(10px)',
              boxShadow: '0 1px 6px rgba(0,0,0,0.05)',
            }}
          >
            <h2 className="text-sm font-semibold" style={{ color: '#1a1a2e' }}>Beispiele</h2>
            <ul className="space-y-1.5">
              {[
                '"Hallo"',
                '"Was gibt es zu essen?"',
                '"Ich möchte Bibimbap bestellen"',
                '"Einen Tisch für 2 morgen um 19 Uhr"',
                '"Wie ist das Wetter?"',
              ].map(ex => (
                <li
                  key={ex}
                  className="px-3 py-2 rounded-xl text-sm italic cursor-default"
                  style={{
                    background: 'rgba(255,255,255,0.7)',
                    color: '#64748b',
                    border: '1px solid rgba(255,255,255,0.7)',
                  }}
                >
                  {ex}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </main>

      <style jsx global>{`
        @keyframes sailly-idle {
          0%, 100% { transform: scale(1); filter: brightness(1); }
          50% { transform: scale(1.03); filter: brightness(1.05); }
        }
        @keyframes sailly-pulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.08); opacity: 0.85; }
        }
        @keyframes sailly-speak {
          0% { transform: scale(1); }
          100% { transform: scale(1.06); }
        }
        @keyframes sailly-ring {
          0%, 100% { opacity: 0.15; transform: scale(1.4); }
          50% { opacity: 0.35; transform: scale(1.6); }
        }
      `}</style>
    </div>
  );
}
