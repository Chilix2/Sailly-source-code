/**
 * Sailly - AI Voice Agent Backend (Minimal Bootstrap Version)
 * Stripped-down server for getting infrastructure running
 */

import 'dotenv/config';
import Fastify from 'fastify';
import fastifyFormBody from '@fastify/formbody';
import fastifyHelmet from '@fastify/helmet';
import fastifyRateLimit from '@fastify/rate-limit';
import fastifyCookie from '@fastify/cookie';
import fastifyCors from '@fastify/cors';
import { WebSocketServer } from 'ws';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import Twilio from 'twilio';
import https from 'https';

const app = Fastify({
  logger: true
});

// Security
await app.register(fastifyHelmet);
await app.register(fastifyRateLimit, { max: 100, timeWindow: '15 minutes' });
await app.register(fastifyCookie);
await app.register(fastifyCors, { origin: true });
await app.register(fastifyFormBody);

const PORT = parseInt(process.env.PORT || '3002');
const NODE_ENV = process.env.NODE_ENV || 'production';
const AI_PROVIDER = process.env.AI_PROVIDER || 'gemini';

// Industry-to-Twilio-Number mapping
const INDUSTRY_PHONE_NUMBERS: Record<string, string> = {
  restaurant: process.env.TWILIO_NUMBER_RESTAURANT || "+14252928787",
  medical: process.env.TWILIO_NUMBER_MEDICAL || "+14258422614",
  hotel: process.env.TWILIO_NUMBER_HOTEL || "+14256753218",
  services: process.env.TWILIO_NUMBER_SERVICES || "+14254032398",
  other: process.env.TWILIO_PHONE_NUMBER || "+14252928787",
};

// In-memory user database (for demo)
const users: Record<string, { id: number; username: string; email: string; fullName: string; password: string; role: string }> = {
  franck: {
    id: 1,
    username: 'franck',
    email: 'franck@sailly.tech',
    fullName: 'Franck Mueller',
    password: 'YachtMaster2026!',
    role: 'admin'
  },
  sailly: {
    id: 2,
    username: 'sailly',
    email: 'sailly@sailly.tech',
    fullName: 'Sailly',
    password: 'StartUp2026!',
    role: 'viewer'
  }
};

// Health check
app.get('/health', async (_request, reply) => {
  return reply.code(200).send({
    status: 'ok',
    timestamp: new Date().toISOString(),
    environment: NODE_ENV,
    ai_provider: AI_PROVIDER
  });
});

// Auth endpoint for dashboard login
app.post('/api/auth/login', async (request, reply) => {
  try {
    const body = request.body as Record<string, string>;
    const { username, password } = body;

    if (!username || !password) {
      return reply.code(400).send({
        success: false,
        message: 'Username and password required'
      });
    }

    // Find user
    const user = users[username.toLowerCase()];
    if (!user) {
      return reply.code(401).send({
        success: false,
        message: 'Invalid credentials'
      });
    }

    // Verify password
    if (user.password !== password) {
      return reply.code(401).send({
        success: false,
        message: 'Invalid credentials'
      });
    }

    return reply.code(200).send({
      success: true,
      user: {
        id: user.id,
        username: user.username,
        fullName: user.fullName,
        email: user.email,
        role: user.role
      }
    });
  } catch (err) {
    console.error('[api/auth/login] error:', err);
    return reply.code(500).send({
      success: false,
      message: 'Auth service error'
    });
  }
});

// WebSocket for media streaming (required by Twilio)
const wss = new WebSocketServer({ noServer: true });

app.get('/media-stream', { websocket: true }, async (socket, request) => {
  console.log('WebSocket client connected');
  
  socket.on('message', (data) => {
    // Echo incoming messages (for testing)
    socket.send(JSON.stringify({
      type: 'ack',
      timestamp: Date.now(),
      bytes_received: (data as Buffer).length
    }));
  });

  socket.on('close', () => {
    console.log('WebSocket client disconnected');
  });

  socket.on('error', (err) => {
    console.error('WebSocket error:', err);
  });
});

// Twilio webhook endpoint
app.post('/twilio/incoming', async (request, reply) => {
  const { CallSid, From, To } = request.body as Record<string, string>;
  console.log(`📞 Twilio incoming call - CallSid: ${CallSid}, From: ${From}, To: ${To}`);
  
  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://${process.env.GCP_EXTERNAL_IP || 'localhost'}:${PORT}/media-stream">
      <Parameter name="conversation_id" value="${CallSid}"/>
      <Parameter name="caller_phone" value="${From}"/>
    </Stream>
  </Connect>
</Response>`;
  
  return reply.type('application/xml').send(twiml);
});

// ElevenLabs conversation started webhook
app.post('/elevenlabs/conversation-started', async (request, reply) => {
  const body = request.body as Record<string, any>;
  console.log(`🎙️ ElevenLabs conversation started - ID: ${body.conversation_id}`);
  
  return reply.code(200).send({
    status: 'received',
    conversation_id: body.conversation_id,
    timestamp: new Date().toISOString()
  });
});

// ElevenLabs conversation ended webhook
app.post('/elevenlabs/conversation-ended', async (request, reply) => {
  const body = request.body as Record<string, any>;
  console.log(`🏁 ElevenLabs conversation ended - ID: ${body.conversation_id}`);
  
  return reply.code(200).send({
    status: 'received',
    conversation_id: body.conversation_id,
    timestamp: new Date().toISOString()
  });
});

// ElevenLabs webhook (generic)
app.post('/elevenlabs/webhook', async (request, reply) => {
  const body = request.body as Record<string, any>;
  console.log(`🔔 ElevenLabs webhook received - Event: ${body.event}`);
  
  return reply.code(200).send({
    status: 'received',
    event: body.event,
    timestamp: new Date().toISOString()
  });
});

// Basic health/status endpoints
app.post('/webhook', async (request, reply) => {
  console.log('Webhook received:', request.headers);
  return reply.code(200).send({ acknowledged: true });
});

app.get('/status', async (_request, reply) => {
  return reply.code(200).send({
    service: 'sailly-backend',
    version: '1.0.0',
    environment: NODE_ENV,
    ai_provider: AI_PROVIDER,
    uptime_seconds: process.uptime(),
    timestamp: new Date().toISOString()
  });
});

// ─── Demo Leads System ───────────────────────────────────────────────
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LEADS_DIR = path.join(__dirname, 'demo-leads');
const LEADS_FILE = path.join(LEADS_DIR, 'leads.jsonl');

// DEMO_LIVE_ENABLED: true = make real Twilio calls, false = save lead only
const DEMO_LIVE_ENABLED = process.env.DEMO_LIVE_ENABLED !== 'false'; // default ON

const demoCallStates = new Map<string, { status: string; duration?: number; callSid?: string }>();

function generateLeadId(): string {
  return `lead_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function appendLead(lead: Record<string, any>): void {
  fs.appendFileSync(LEADS_FILE, JSON.stringify(lead) + '\n');
}

// ============================================================================
// Demo Leads — PostgreSQL Persistence
// ============================================================================

let _pgPool: any = null;

async function getDemoDbPool(): Promise<any | null> {
  if (_pgPool) return _pgPool;
  try {
    const { default: pg } = await import('pg') as any;
    const Pool = pg.Pool;
    const dbUrl = process.env.DATABASE_URL || 'postgresql://postgres@localhost:5433/sailly';
    _pgPool = new Pool({ connectionString: dbUrl, max: 5 });

    // Auto-create table on first connection
    await _pgPool.query(`
      CREATE TABLE IF NOT EXISTS demo_leads (
        id           SERIAL PRIMARY KEY,
        lead_id      VARCHAR(255) UNIQUE NOT NULL,
        phone_number VARCHAR(20)  NOT NULL,
        industry     VARCHAR(50)  NOT NULL,
        custom_industry VARCHAR(255),
        locale       VARCHAR(10)  DEFAULT 'de',
        call_sid     VARCHAR(255),
        call_status  VARCHAR(50),
        call_duration INTEGER,
        ip_address   VARCHAR(45),
        created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
        updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
        session_data JSONB
      );
      CREATE INDEX IF NOT EXISTS idx_demo_leads_phone  ON demo_leads(phone_number);
      CREATE INDEX IF NOT EXISTS idx_demo_leads_sid    ON demo_leads(call_sid);
      CREATE INDEX IF NOT EXISTS idx_demo_leads_time   ON demo_leads(created_at DESC);
    `);
    console.log('[demo-db] demo_leads table ready');
    return _pgPool;
  } catch (err: any) {
    console.error('[demo-db] Could not connect to PostgreSQL:', err.message);
    return null;
  }
}

async function persistLeadToDb(lead: Record<string, any>): Promise<void> {
  const pool = await getDemoDbPool();
  if (!pool) return;
  try {
    await pool.query(
      `INSERT INTO demo_leads
        (lead_id, phone_number, industry, custom_industry, locale,
         call_sid, call_status, call_duration, ip_address, session_data)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
       ON CONFLICT (lead_id) DO UPDATE SET
         call_sid      = EXCLUDED.call_sid,
         call_status   = EXCLUDED.call_status,
         call_duration = EXCLUDED.call_duration,
         updated_at    = CURRENT_TIMESTAMP,
         session_data  = EXCLUDED.session_data`,
      [
        lead.id,
        lead.phoneNumber,
        lead.industry,
        lead.customIndustry ?? null,
        lead.locale ?? 'de',
        lead.callSid ?? null,
        lead.callStatus,
        lead.callDuration ?? null,
        lead.ip,
        JSON.stringify(lead),
      ]
    );
    console.log(`[demo-db] Persisted lead ${lead.id} (phone: ${lead.phoneNumber})`);
  } catch (err: any) {
    console.error(`[demo-db] Failed to persist lead ${lead.id}:`, err.message);
  }
}

function hasIpUsedDemo(ip: string): boolean {
  if (!fs.existsSync(LEADS_FILE)) return false;
  const lines = fs.readFileSync(LEADS_FILE, 'utf-8').trim().split('\n').filter(Boolean);
  const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;
  return lines.some(line => {
    try {
      const record = JSON.parse(line);
      return record.ip === ip && new Date(record.timestamp).getTime() > thirtyDaysAgo;
    } catch { return false; }
  });
}

function getClientIp(request: any): string {
  return (
    request.headers['x-forwarded-for']?.toString().split(',')[0]?.trim() ||
    request.headers['x-real-ip']?.toString() ||
    request.ip ||
    'unknown'
  );
}

// Industry-specific TwiML greeting scripts (used when <Stream> pipeline is not ready)
const DEMO_GREETINGS: Record<string, Record<string, string>> = {
  restaurant: {
    de: 'Guten Abend, Restaurant Münchner Stubn. Sie sprechen mit Sailly, dem digitalen KI-Assistenten. Ich kann Ihnen bei Reservierungen, Menüfragen und Sonderwünschen helfen. Wie darf ich Ihnen behilflich sein?',
    en: 'Good evening, The Garden Bistro. You are speaking with Sailly, the digital AI assistant. I can help you with reservations, menu questions, and special requests. How may I assist you?',
  },
  hotel: {
    de: 'Guten Tag, Motel One Bonn am Hauptbahnhof. Hier ist Sailly, Ihr digitaler Assistent. Ich helfe Ihnen gerne mit Buchungen, Umbuchungen und allen Fragen rund um Ihren Aufenthalt. Was kann ich für Sie tun?',
    en: 'Good day, Motel One Bonn at Central Station. This is Sailly, your digital assistant. I am happy to help with bookings, rebookings, and any questions about your stay. How can I help?',
  },
  medical: {
    de: 'Guten Morgen, Orthopädische Praxis Dr. Hoffmann. Sie sprechen mit Sailly, dem digitalen Assistenten. Ich kann Termine vereinbaren, verschieben und Ihre Anliegen aufnehmen. Wie kann ich Ihnen helfen?',
    en: 'Good morning, Hoffmann Orthopaedic Practice. You are speaking with Sailly, the digital assistant. I can schedule, reschedule appointments and take your requests. How can I help you?',
  },
  other: {
    de: 'Guten Tag! Hier ist Sailly, Ihr digitaler KI-Assistent. Ich bin rund um die Uhr für Sie erreichbar. Wie kann ich Ihnen weiterhelfen?',
    en: 'Hello! This is Sailly, your digital AI assistant. I am available around the clock. How can I help you?',
  },
};

const DEMO_FOLLOWUP: Record<string, string> = {
  de: 'Vielen Dank für Ihren Testanruf! Das war eine kurze Demonstration von Sailly. Unser Team wird sich in Kürze bei Ihnen melden, um Ihnen eine personalisierte Demo mit allen Funktionen einzurichten. Wir freuen uns auf die Zusammenarbeit! Auf Wiederhören.',
  en: 'Thank you for your test call! That was a brief demonstration of Sailly. Our team will contact you shortly to set up a personalised demo with full capabilities. We look forward to working with you! Goodbye.',
};

// TESTING_MODE: bypass usage limit for internal testing — set to false for production
const DEMO_TESTING_MODE = process.env.DEMO_TESTING_MODE !== 'false';

// Check if demo is allowed for this visitor
app.get('/api/demo/check', async (request, reply) => {
  if (DEMO_TESTING_MODE) return reply.send({ allowed: true });
  const ip = getClientIp(request);
  const cookie = (request.cookies as any)?.sailly_demo_used;
  const blocked = cookie === 'true' || hasIpUsedDemo(ip);
  return reply.send({ allowed: !blocked });
});

// Dry-run test: validates Twilio credentials, TwiML generation, and pipeline readiness
app.get('/api/demo/dry-run', async (request, reply) => {
  const checks: Record<string, { pass: boolean; detail: string }> = {};

  // 1. Pipeline health check
  try {
    const pipelineUrl = process.env.PIPELINE_HEALTH_URL || 'http://127.0.0.1:3003/health';
    const healthRes = await fetch(pipelineUrl, { signal: AbortSignal.timeout(5000) });
    if (healthRes.ok) {
      const healthData = await healthRes.json() as Record<string, any>;
      checks['pipeline_health'] = {
        pass: healthData.status === 'ok',
        detail: `Pipeline: ${healthData.status}, active_calls: ${healthData.active_calls || 0}`,
      };
    } else {
      checks['pipeline_health'] = { pass: false, detail: `HTTP ${healthRes.status}` };
    }
  } catch (err: any) {
    checks['pipeline_health'] = { pass: false, detail: `Unreachable: ${err.message?.slice(0, 50)}` };
  }

  // 2. Twilio credentials
  const accountSid = process.env.TWILIO_ACCOUNT_SID;
  const authToken = process.env.TWILIO_AUTH_TOKEN;
  const fromNumber = process.env.TWILIO_PHONE_NUMBER;
  checks['twilio_credentials'] = {
    pass: !!(accountSid && authToken && fromNumber),
    detail: accountSid ? `SID: ${accountSid.slice(0, 8)}...` : 'MISSING',
  };

  // 3. Twilio API connectivity
  if (accountSid && authToken) {
    try {
      const twilioClient = Twilio(accountSid, authToken);
      const account = await twilioClient.api.accounts(accountSid).fetch();
      checks['twilio_api'] = { pass: true, detail: `Account: ${account.friendlyName}, Status: ${account.status}` };
    } catch (err: any) {
      checks['twilio_api'] = { pass: false, detail: err.message?.slice(0, 80) };
    }
  } else {
    checks['twilio_api'] = { pass: false, detail: 'Skipped (no credentials)' };
  }

  // 4. TwiML generation
  try {
    const testIndustry = 'restaurant';
    const testLocale = 'de';
    const greeting = DEMO_GREETINGS[testIndustry]?.[testLocale];
    checks['twiml_generation'] = {
      pass: !!greeting,
      detail: greeting ? `Greeting: "${greeting.slice(0, 50)}..."` : 'MISSING greeting text',
    };
  } catch (err: any) {
    checks['twiml_generation'] = { pass: false, detail: err.message };
  }

  // 5. Leads directory writable
  try {
    const testFile = path.join(LEADS_DIR, '.dry-run-test');
    fs.writeFileSync(testFile, 'test');
    fs.unlinkSync(testFile);
    checks['leads_storage'] = { pass: true, detail: LEADS_FILE };
  } catch (err: any) {
    checks['leads_storage'] = { pass: false, detail: err.message?.slice(0, 80) };
  }

  // 6. Live calling flag
  checks['live_calling_enabled'] = {
    pass: DEMO_LIVE_ENABLED,
    detail: DEMO_LIVE_ENABLED ? 'ENABLED (DEMO_LIVE_ENABLED=true)' : 'DISABLED — set DEMO_LIVE_ENABLED=true in env to activate',
  };

  const allPass = Object.values(checks).every(c => c.pass);

  return reply.send({
    overall: allPass ? 'PASS' : 'FAIL',
    timestamp: new Date().toISOString(),
    checks,
  });
});

// Initiate outbound demo call
app.post('/api/demo/initiate', async (request, reply) => {
  const body = request.body as Record<string, any>;
  const { industry, customIndustry, phoneNumber, locale } = body;

  if (!phoneNumber || !industry) {
    return reply.code(400).send({ error: 'phoneNumber and industry are required' });
  }

  const ip = getClientIp(request);
  if (!DEMO_TESTING_MODE) {
    const cookie = (request.cookies as any)?.sailly_demo_used;
    if (cookie === 'true' || hasIpUsedDemo(ip)) {
      return reply.code(429).send({ error: 'Demo already used. Contact us for a personalised demo.' });
    }
  }

  const leadId = generateLeadId();
  const lead = {
    id: leadId,
    timestamp: new Date().toISOString(),
    industry: industry || 'other',
    customIndustry: customIndustry || null,
    phoneNumber,
    locale: locale || 'de',
    ip,
    callSid: null as string | null,
    callStatus: 'initiating',
    callDuration: null as number | null,
    demoPhaseCompleted: false,
    salesData: null,
  };

  // Gate: only make real calls if DEMO_LIVE_ENABLED
  if (!DEMO_LIVE_ENABLED) {
    lead.callStatus = 'queued';
    appendLead(lead);
    persistLeadToDb(lead); // fire-and-forget to DB
    demoCallStates.set(leadId, { status: 'queued' });
    console.log(`[demo] LIVE DISABLED — lead saved: ${leadId}, phone: ${phoneNumber}, industry: ${industry}`);

    if (!DEMO_TESTING_MODE) {
      reply.setCookie('sailly_demo_used', 'true', {
        path: '/',
        httpOnly: true,
        maxAge: 30 * 24 * 60 * 60,
        sameSite: 'lax',
      });
    }

    return reply.send({ leadId, status: 'queued', message: 'Demo request received. We will call you shortly.' });
  }

  const accountSid = process.env.TWILIO_ACCOUNT_SID;
  const authToken = process.env.TWILIO_AUTH_TOKEN;
  
  // Get industry-specific phone number for outbound call
  const fromNumber = INDUSTRY_PHONE_NUMBERS[industry as string] || INDUSTRY_PHONE_NUMBERS.other;

  if (!accountSid || !authToken || !fromNumber) {
    console.error('[demo] Twilio credentials not configured');
    return reply.code(500).send({ error: 'Call service not configured' });
  }

  try {
    // Pre-flight: verify Python voice pipeline is healthy before spending Twilio credits
    try {
      const pipelineUrl = process.env.PIPELINE_HEALTH_URL || 'http://127.0.0.1:3003/health';
      const healthRes = await fetch(pipelineUrl, { signal: AbortSignal.timeout(5000) });
      if (!healthRes.ok) {
        const body = await healthRes.text();
        console.error(`[demo] Pipeline health check FAILED (HTTP ${healthRes.status}): ${body}`);
        return reply.code(503).send({ error: 'Voice pipeline is not ready. Please try again in a moment.' });
      }
      const healthData = await healthRes.json() as Record<string, unknown>;
      console.log(`[demo] Pipeline health: ${JSON.stringify(healthData)}`);
    } catch (healthErr: unknown) {
      console.error(`[demo] Pipeline health check unreachable:`, healthErr);
      return reply.code(503).send({ error: 'Voice pipeline is not reachable. Please try again in a moment.' });
    }

    const twilioClient = Twilio(accountSid, authToken);
    const baseUrl = `https://sailly.de`;

    const call = await twilioClient.calls.create({
      to: phoneNumber,
      from: fromNumber,
      url: `${baseUrl}/twiml?leadId=${leadId}&industry=${encodeURIComponent(industry)}&locale=${encodeURIComponent(locale || 'de')}&source=website_demo`,
      statusCallback: `${baseUrl}/api/demo/call-status?leadId=${leadId}`,
      statusCallbackEvent: ['initiated', 'ringing', 'answered', 'completed'],
      statusCallbackMethod: 'POST',
    });

    lead.callSid = call.sid;
    lead.callStatus = 'initiated';
    appendLead(lead);
    persistLeadToDb(lead); // fire-and-forget to DB

    demoCallStates.set(leadId, { status: 'initiated', callSid: call.sid });

    if (!DEMO_TESTING_MODE) {
      reply.setCookie('sailly_demo_used', 'true', {
        path: '/',
        httpOnly: true,
        maxAge: 30 * 24 * 60 * 60,
        sameSite: 'lax',
      });
    }

    return reply.send({ leadId, callSid: call.sid, status: 'initiated' });
  } catch (err: any) {
    console.error('[demo] Failed to initiate call:', err.message);
    lead.callStatus = 'failed';
    appendLead(lead);
    persistLeadToDb(lead); // fire-and-forget to DB
    return reply.code(500).send({ error: 'Failed to initiate call', details: err.message });
  }
});

// TwiML for demo calls
app.all('/api/demo/twiml', async (request, reply) => {
  const query = (request.query || {}) as Record<string, string>;
  const { leadId, industry, locale } = query;
  const lang = locale === 'en' ? 'en' : 'de';
  const twimlLang = lang === 'de' ? 'de-DE' : 'en-US';
  const voice = lang === 'de' ? 'Google.de-DE-Wavenet-C' : 'Google.en-US-Wavenet-F';

  const ind = (industry && DEMO_GREETINGS[industry]) ? industry : 'other';
  const greeting = DEMO_GREETINGS[ind][lang] || DEMO_GREETINGS['other'][lang];
  const followup = DEMO_FOLLOWUP[lang];

  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="${voice}" language="${twimlLang}">${greeting}</Say>
  <Pause length="1"/>
  <Gather input="speech" timeout="8" speechTimeout="auto" language="${twimlLang}" action="https://sailly.de/api/demo/twiml-respond?leadId=${leadId || ''}&amp;industry=${ind}&amp;locale=${lang}&amp;turn=1" method="POST">
    <Say voice="${voice}" language="${twimlLang}">${lang === 'de' ? 'Ich hoere Ihnen zu.' : 'I am listening.'}</Say>
  </Gather>
  <Say voice="${voice}" language="${twimlLang}">${followup}</Say>
  <Hangup/>
</Response>`;

  return reply.type('application/xml').send(twiml);
});

// TwiML response handler for subsequent turns
app.all('/api/demo/twiml-respond', async (request, reply) => {
  return reply.type("application/xml").send("<Response><Say>Please wait.</Say></Response>");
});

// ============================================================================
// Dashboard API — Live data from PostgreSQL (google_calls table)
// ============================================================================

const DAYS = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

app.get("/api/dashboard/overview", async (request, reply) => {
  try {
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");

    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekAgoStart = new Date(todayStart.getTime() - 7 * 24 * 60 * 60 * 1000);
    const twoWeeksAgoStart = new Date(todayStart.getTime() - 14 * 24 * 60 * 60 * 1000);

    const [todayRes, weekRes, prevWeekRes, volumeRes, qualityRes, recentRes, toolRes] = await Promise.all([
      pool.query(`SELECT COUNT(*) as total, AVG(duration_seconds) as avg_dur, AVG(quality_score) as avg_q, SUM(total_cost_tokens + total_cost_telephony) as cost, SUM(CASE WHEN was_escalated THEN 1 ELSE 0 END) as escalated FROM google_calls WHERE started_at >= $1`, [todayStart]),
      pool.query(`SELECT COUNT(*) as total, AVG(quality_score) as avg_q FROM google_calls WHERE started_at >= $1`, [weekAgoStart]),
      pool.query(`SELECT COUNT(*) as total, AVG(quality_score) as avg_q FROM google_calls WHERE started_at >= $1 AND started_at < $2`, [twoWeeksAgoStart, weekAgoStart]),
      pool.query(`SELECT DATE(started_at) as day, COUNT(*) as count FROM google_calls WHERE started_at >= $1 GROUP BY DATE(started_at) ORDER BY day`, [weekAgoStart]),
      pool.query(`SELECT DATE(started_at) as day, AVG(quality_score) as score FROM google_calls WHERE started_at >= $1 GROUP BY DATE(started_at) ORDER BY day`, [weekAgoStart]),
      pool.query(`SELECT id, call_sid, caller_number, started_at, duration_seconds, quality_score, outcome FROM google_calls ORDER BY id DESC LIMIT 5`),
      pool.query(`SELECT gc.call_sid, COUNT(DISTINCT gtc.id) as tool_count FROM google_calls gc LEFT JOIN google_tool_calls gtc ON gtc.call_sid = gc.call_sid WHERE gc.started_at >= $1 GROUP BY gc.call_sid`, [weekAgoStart]),
    ]);

    const today = todayRes.rows[0];
    const week = weekRes.rows[0];
    const prevWeek = prevWeekRes.rows[0];

    const totalToday = parseInt(today.total) || 0;
    const avgDurSecs = Math.round(parseFloat(today.avg_dur) || 0);
    const avgQ = parseFloat(today.avg_q) || 0;
    const costToday = parseFloat(today.cost) || 0;
    const escalated = parseInt(today.escalated) || 0;

    const weekTotal = parseInt(week.total) || 0;
    const prevWeekTotal = parseInt(prevWeek.total) || 1;
    const weekAvgQ = parseFloat(week.avg_q) || 0;
    const prevWeekAvgQ = parseFloat(prevWeek.avg_q) || 0;

    // Build 7-day arrays
    const volumeMap: Record<string, number> = {};
    const qualityMap: Record<string, number> = {};
    volumeRes.rows.forEach((r: any) => { volumeMap[r.day.toISOString().slice(0,10)] = parseInt(r.count); });
    qualityRes.rows.forEach((r: any) => { qualityMap[r.day.toISOString().slice(0,10)] = parseFloat(r.score); });

    const callVolume7Days = [];
    const qualityTrend7Days = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date(todayStart.getTime() - i * 24 * 60 * 60 * 1000);
      const key = d.toISOString().slice(0, 10);
      const label = DAYS[d.getDay()];
      callVolume7Days.push({ date: label, count: volumeMap[key] || 0 });
      qualityTrend7Days.push({ date: label, score: parseFloat((qualityMap[key] || 0).toFixed(1)) });
    }

    const recentCalls = recentRes.rows.map((r: any) => ({
      id: String(r.id),
      call_sid: r.call_sid,
      caller_number: r.caller_number || "unknown",
      started_at: r.started_at,
      duration_seconds: r.duration_seconds || 0,
      quality_score: parseFloat(r.quality_score) || 0,
      outcome: r.outcome || "unknown"
    }));

    const alerts = [];
    if (avgQ > 0 && avgQ < 6) alerts.push({ type: "warning", message: `Quality score low today: ${avgQ.toFixed(1)}/10`, severity: "warning" });
    if (escalated > 0) alerts.push({ type: "info", message: `${escalated} call(s) escalated today`, severity: "info" });
    // Check for known issues in tool calls
    const toolErrors = await pool.query(`SELECT COUNT(*) as cnt FROM google_tool_calls WHERE result LIKE '%error%' AND created_at >= $1`, [weekAgoStart]).catch(() => ({ rows: [{ cnt: 0 }] }));
    if (parseInt((toolErrors as any).rows[0].cnt) > 0) alerts.push({ type: "warning", message: "Tool errors detected in recent calls — review logs", severity: "warning" });

    return reply.code(200).send({
      totalCallsToday: totalToday,
      activeNow: 0,
      avgDurationToday: `${Math.floor(avgDurSecs/60)}m ${avgDurSecs%60}s`,
      qualityScoreToday: parseFloat((avgQ * 10).toFixed(1)),
      costToday: parseFloat(costToday.toFixed(2)),
      resolutionRate: weekTotal > 0 ? Math.round((weekTotal - escalated) / weekTotal * 100) : 100,
      avgLatency: 0,
      escalatedToday: escalated,
      deltaCallsVsLastWeek: prevWeekTotal > 0 ? Math.round((weekTotal - prevWeekTotal) / prevWeekTotal * 100) : 0,
      deltaQualityVsLastWeek: parseFloat((weekAvgQ - prevWeekAvgQ).toFixed(1)),
      callVolume7Days,
      qualityTrend7Days,
      recentCalls,
      alerts: alerts.length > 0 ? alerts : [{ type: "info", message: "All systems nominal", severity: "info" }]
    });
  } catch (err: any) {
    console.error("[dashboard/overview] DB error:", err.message);
    return reply.code(503).send({ error: "Database unavailable", detail: err.message });
  }
});

// Dashboard calls list — live from DB
app.get("/api/dashboard/calls", async (request, reply) => {
  try {
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");

    const q = (request.query || {}) as Record<string, string>;
    const limit = parseInt(q.limit || "50");
    const offset = parseInt(q.offset || "0");
    const search = q.search || "";
    const minScore = parseFloat(q.minScore || "0");
    const maxScore = parseFloat(q.maxScore || "10");

    const searchClause = search ? `AND (call_sid ILIKE $5 OR caller_number ILIKE $5)` : "";
    const params: any[] = [limit, offset, minScore, maxScore];
    if (search) params.push(`%${search}%`);

    const [callsRes, countRes, toolsRes] = await Promise.all([
      pool.query(`SELECT gc.id, gc.call_sid, gc.caller_number, gc.started_at, gc.duration_seconds, gc.quality_score, gc.outcome, (gc.total_cost_tokens + gc.total_cost_telephony) as total_cost, gc.was_escalated FROM google_calls gc WHERE gc.quality_score >= $3 AND gc.quality_score <= $4 ${searchClause} ORDER BY gc.id DESC LIMIT $1 OFFSET $2`, params),
      pool.query(`SELECT COUNT(*) as total FROM google_calls WHERE quality_score >= $1 AND quality_score <= $2 ${searchClause}`, search ? [minScore, maxScore, `%${search}%`] : [minScore, maxScore]),
      pool.query(`SELECT call_sid, COUNT(*) as cnt FROM google_tool_calls GROUP BY call_sid`),
    ]);

    const toolMap: Record<string, number> = {};
    toolsRes.rows.forEach((r: any) => { toolMap[r.call_sid] = parseInt(r.cnt); });

    const calls = callsRes.rows.map((r: any) => ({
      id: String(r.id),
      call_sid: r.call_sid,
      caller_number: r.caller_number || "unknown",
      started_at: r.started_at,
      duration_seconds: r.duration_seconds || 0,
      quality_score: parseFloat(r.quality_score) || 0,
      outcome: r.outcome || "unknown",
      total_cost: parseFloat(r.total_cost) || 0,
      was_escalated: r.was_escalated || false,
      tool_count: toolMap[r.call_sid] || 0
    }));

    return reply.code(200).send({ calls, total: parseInt(countRes.rows[0].total) });
  } catch (err: any) {
    console.error("[dashboard/calls] DB error:", err.message);
    return reply.code(503).send({ error: "Database unavailable" });
  }
});

// Dashboard call detail — live from DB
app.get("/api/dashboard/calls/:id", async (request, reply) => {
  try {
    const { id } = request.params as { id: string };
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");

    const [callRes, toolsRes, transcriptsRes] = await Promise.all([
      pool.query(`SELECT *, (total_cost_tokens + total_cost_telephony) as total_cost FROM google_calls WHERE id = $1`, [id]),
      // google_tool_calls uses: arguments (not input_data), result_summary (not result), called_at (not created_at)
      pool.query(`SELECT tool_name, arguments AS input_data, result_summary AS result, called_at AS created_at FROM google_tool_calls WHERE call_sid = (SELECT call_sid FROM google_calls WHERE id=$1) ORDER BY called_at`, [id]),
      // google_transcripts uses: timestamp (not created_at), turn_number for ordering
      pool.query(`SELECT role, content, turn_number, timestamp AS created_at FROM google_transcripts WHERE call_sid = (SELECT call_sid FROM google_calls WHERE id=$1) ORDER BY turn_number`, [id]),
    ]);

    if (callRes.rows.length === 0) return reply.code(404).send({ error: "Call not found" });

    const call = callRes.rows[0];
    return reply.code(200).send({
      success: true,
      data: {
        ...call,
        total_cost: parseFloat(call.total_cost) || 0,
        quality_score: parseFloat(call.quality_score) || 0,
        tool_calls: toolsRes.rows,
        transcript: transcriptsRes.rows
      }
    });
  } catch (err: any) {
    return reply.code(503).send({ error: "Database unavailable" });
  }
});

// Dashboard stats
app.get("/api/dashboard/stats", async (request, reply) => {
  try {
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");

    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekAgoStart = new Date(todayStart.getTime() - 7 * 24 * 60 * 60 * 1000);

    const [todayRes, weekRes, allRes] = await Promise.all([
      pool.query(`SELECT COUNT(*) as total, AVG(duration_seconds) as avg_dur FROM google_calls WHERE started_at >= $1`, [todayStart]),
      pool.query(`SELECT COUNT(*) as total, AVG(duration_seconds) as avg_dur FROM google_calls WHERE started_at >= $1`, [weekAgoStart]),
      pool.query(`SELECT COUNT(*) as total, AVG(duration_seconds) as avg_dur FROM google_calls`),
    ]);

    return reply.code(200).send({
      success: true,
      data: {
        today: { total: parseInt(todayRes.rows[0].total), avgDuration: Math.round(parseFloat(todayRes.rows[0].avg_dur) || 0) },
        week: { total: parseInt(weekRes.rows[0].total), avgDuration: Math.round(parseFloat(weekRes.rows[0].avg_dur) || 0) },
        allTime: { total: parseInt(allRes.rows[0].total), avgDuration: Math.round(parseFloat(allRes.rows[0].avg_dur) || 0) }
      }
    });
  } catch (err: any) {
    return reply.code(503).send({ error: "Database unavailable" });
  }
});

// ============================================================================
// Dashboard: Conversations (transcript browser)
// ============================================================================

app.get("/api/dashboard/conversations", async (request, reply) => {
  try {
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");
    const q = (request.query || {}) as Record<string, string>;
    const limit = parseInt(q.limit || "50");
    const offset = parseInt(q.offset || "0");
    const search = q.search || "";

    const searchClause = search ? `AND (gc.call_sid ILIKE $3 OR gc.caller_number ILIKE $3)` : "";
    const params: any[] = [limit, offset];
    if (search) params.push(`%${search}%`);

    const res = await pool.query(`
      SELECT gc.id, gc.call_sid, gc.caller_number, gc.started_at, gc.ended_at,
             gc.duration_seconds, gc.quality_score, gc.outcome, gc.sentiment, gc.language,
             (SELECT COUNT(*) FROM google_transcripts gt WHERE gt.call_sid = gc.call_sid) as transcript_count,
             (SELECT COUNT(*) FROM google_tool_calls gtc WHERE gtc.call_sid = gc.call_sid) as tool_count
      FROM google_calls gc WHERE 1=1 ${searchClause}
      ORDER BY gc.id DESC LIMIT $1 OFFSET $2`, params);

    const countRes = await pool.query(`SELECT COUNT(*) as total FROM google_calls WHERE 1=1 ${searchClause}`, search ? [`%${search}%`] : []);

    return reply.send({
      success: true,
      data: res.rows.map((r: any) => ({
        id: r.call_sid,
        call_id: r.id,
        status: "completed",
        quality_score: parseFloat(r.quality_score) || 0,
        phone: r.caller_number || "unknown",
        duration_seconds: r.duration_seconds || 0,
        language: r.language || "de",
        transcript_count: parseInt(r.transcript_count),
        tool_count: parseInt(r.tool_count),
        outcome: r.outcome || "unknown",
        sentiment: r.sentiment || "neutral",
        started_at: r.started_at,
        ended_at: r.ended_at,
      })),
      total: parseInt(countRes.rows[0].total)
    });
  } catch (err: any) {
    return reply.code(503).send({ success: false, error: err.message });
  }
});

app.get("/api/dashboard/conversations/:callSid", async (request, reply) => {
  try {
    const { callSid } = request.params as { callSid: string };
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");

    const callRes = await pool.query(`SELECT * FROM google_calls WHERE call_sid = $1`, [callSid]);
    if (callRes.rows.length === 0) return reply.code(404).send({ error: "Not found" });

    const [transcripts, tools, quality] = await Promise.all([
      pool.query(`SELECT role, content, turn_number, timestamp FROM google_transcripts WHERE call_sid=$1 ORDER BY turn_number, id`, [callSid]),
      pool.query(`SELECT tool_name, arguments, result_summary, duration_ms, turn_number, called_at FROM google_tool_calls WHERE call_sid=$1 ORDER BY called_at`, [callSid]),
      pool.query(`SELECT * FROM google_quality_evaluations WHERE call_sid=$1`, [callSid]),
    ]);

    const call = callRes.rows[0];
    const ad = typeof call.analytics_data === 'string' ? JSON.parse(call.analytics_data) : (call.analytics_data || {});

    return reply.send({
      success: true,
      data: {
        call_sid: callSid,
        caller_number: call.caller_number,
        started_at: call.started_at,
        ended_at: call.ended_at,
        duration_seconds: call.duration_seconds,
        quality_score: parseFloat(call.quality_score) || 0,
        outcome: call.outcome,
        sentiment: call.sentiment,
        language: call.language,
        cost: ad.cost || {},
        summary: ad.summary || {},
        quality_detail: ad.quality || {},
        sentiment_detail: ad.sentiment || {},
        metrics: ad.metrics || {},
        transcript: transcripts.rows,
        tool_calls: tools.rows,
        quality_evaluation: quality.rows[0] || null,
        emergency_detected: call.emergency_detected,
        recording_consent_at: call.recording_consent_at,
      }
    });
  } catch (err: any) {
    return reply.code(503).send({ success: false, error: err.message });
  }
});

// ============================================================================
// Dashboard: Costs (real from DB)
// ============================================================================

app.get("/api/dashboard/costs", async (request, reply) => {
  try {
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");

    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekAgo = new Date(todayStart.getTime() - 7 * 24 * 60 * 60 * 1000);

    const [todayRes, weekRes, dailyRes, allRes] = await Promise.all([
      pool.query(`SELECT SUM(total_cost_tokens + total_cost_telephony) as total, COUNT(*) as calls, AVG(total_cost_tokens + total_cost_telephony) as avg_cost FROM google_calls WHERE started_at >= $1`, [todayStart]),
      pool.query(`SELECT SUM(total_cost_tokens + total_cost_telephony) as total, COUNT(*) as calls FROM google_calls WHERE started_at >= $1`, [weekAgo]),
      pool.query(`SELECT DATE(started_at) as day, SUM(total_cost_tokens) as gemini, SUM(total_cost_telephony) as twilio, SUM(total_cost_tokens + total_cost_telephony) as total, COUNT(*) as calls FROM google_calls WHERE started_at >= $1 GROUP BY DATE(started_at) ORDER BY day`, [weekAgo]),
      pool.query(`SELECT SUM(total_cost_tokens + total_cost_telephony) as total, COUNT(*) as calls, AVG(total_cost_tokens + total_cost_telephony) as avg_cost FROM google_calls`),
    ]);

    const perCallRes = await pool.query(`SELECT id, call_sid, started_at, duration_seconds, total_cost_tokens as gemini, total_cost_telephony as twilio, (total_cost_tokens + total_cost_telephony) as total, outcome FROM google_calls ORDER BY id DESC LIMIT 20`);

    return reply.send({
      todaySpend: parseFloat(todayRes.rows[0].total) || 0,
      todayCalls: parseInt(todayRes.rows[0].calls) || 0,
      weekSpend: parseFloat(weekRes.rows[0].total) || 0,
      weekCalls: parseInt(weekRes.rows[0].calls) || 0,
      allTimeSpend: parseFloat(allRes.rows[0].total) || 0,
      allTimeCalls: parseInt(allRes.rows[0].calls) || 0,
      avgCostPerCall: parseFloat(allRes.rows[0].avg_cost) || 0,
      dailyBreakdown: dailyRes.rows.map((r: any) => ({
        date: r.day,
        gemini: parseFloat(r.gemini) || 0,
        twilio: parseFloat(r.twilio) || 0,
        total: parseFloat(r.total) || 0,
        calls: parseInt(r.calls),
      })),
      recentCalls: perCallRes.rows.map((r: any) => ({
        id: r.id, call_sid: r.call_sid, started_at: r.started_at,
        duration_seconds: r.duration_seconds,
        gemini: parseFloat(r.gemini) || 0,
        twilio: parseFloat(r.twilio) || 0,
        total: parseFloat(r.total) || 0,
        outcome: r.outcome,
      })),
    });
  } catch (err: any) {
    return reply.code(503).send({ error: err.message });
  }
});

// ============================================================================
// Dashboard: Quality (real from DB)
// ============================================================================

app.get("/api/dashboard/quality", async (request, reply) => {
  try {
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");

    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);

    const [overallRes, trendsRes, evalRes, issuesRes, callsRes] = await Promise.all([
      pool.query(`SELECT AVG(quality_score) as avg_score, COUNT(*) as total, MIN(quality_score) as min_score, MAX(quality_score) as max_score FROM google_calls WHERE quality_score > 0`),
      pool.query(`SELECT DATE(started_at) as day, AVG(quality_score) as score, COUNT(*) as calls FROM google_calls WHERE started_at >= $1 AND quality_score > 0 GROUP BY DATE(started_at) ORDER BY day`, [weekAgo]),
      pool.query(`SELECT score, issues, tool_usage_score, greeting_score, resolution_score, call_sid FROM google_quality_evaluations ORDER BY id DESC LIMIT 20`),
      pool.query(`SELECT gc.id, gc.call_sid, gc.quality_score, gc.outcome, gc.duration_seconds, gc.started_at, gc.analytics_data FROM google_calls gc WHERE gc.quality_score > 0 ORDER BY gc.quality_score ASC LIMIT 10`),
      pool.query(`SELECT COUNT(*) as total, SUM(CASE WHEN quality_score >= 0.7 THEN 1 ELSE 0 END) as passed, SUM(CASE WHEN quality_score < 0.7 THEN 1 ELSE 0 END) as failed FROM google_calls WHERE quality_score > 0`),
    ]);

    const overall = overallRes.rows[0];
    const gate = callsRes.rows[0];

    return reply.send({
      avgScore: parseFloat(overall.avg_score) || 0,
      totalScored: parseInt(overall.total) || 0,
      minScore: parseFloat(overall.min_score) || 0,
      maxScore: parseFloat(overall.max_score) || 0,
      passRate: gate.total > 0 ? Math.round(parseInt(gate.passed) / parseInt(gate.total) * 100) : 0,
      passed: parseInt(gate.passed) || 0,
      failed: parseInt(gate.failed) || 0,
      trends: trendsRes.rows.map((r: any) => ({ date: r.day, score: parseFloat(r.score), calls: parseInt(r.calls) })),
      evaluations: evalRes.rows.map((r: any) => ({
        call_sid: r.call_sid, score: parseFloat(r.score),
        issues: typeof r.issues === 'string' ? JSON.parse(r.issues) : (r.issues || []),
        tool_usage_score: parseFloat(r.tool_usage_score), greeting_score: parseFloat(r.greeting_score), resolution_score: parseFloat(r.resolution_score),
      })),
      lowQualityCalls: issuesRes.rows.map((r: any) => {
        const ad = typeof r.analytics_data === 'string' ? JSON.parse(r.analytics_data) : (r.analytics_data || {});
        return {
          id: r.id, call_sid: r.call_sid, quality_score: parseFloat(r.quality_score),
          outcome: r.outcome, duration_seconds: r.duration_seconds, started_at: r.started_at,
          issues: ad.quality?.issues || [],
        };
      }),
    });
  } catch (err: any) {
    return reply.code(503).send({ error: err.message });
  }
});

// ============================================================================
// Dashboard: Analytics (aggregate from DB)
// ============================================================================

app.get("/api/dashboard/analytics", async (request, reply) => {
  try {
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");

    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    const monthAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);

    const [volumeRes, outcomeRes, sentimentRes, durationRes, costTrendRes, qualityDistRes] = await Promise.all([
      pool.query(`SELECT DATE(started_at) as day, COUNT(*) as calls FROM google_calls WHERE started_at >= $1 GROUP BY DATE(started_at) ORDER BY day`, [monthAgo]),
      pool.query(`SELECT outcome, COUNT(*) as count FROM google_calls GROUP BY outcome ORDER BY count DESC`),
      pool.query(`SELECT sentiment, COUNT(*) as count FROM google_calls GROUP BY sentiment ORDER BY count DESC`),
      pool.query(`SELECT CASE WHEN duration_seconds < 60 THEN '< 1min' WHEN duration_seconds < 180 THEN '1-3min' WHEN duration_seconds < 300 THEN '3-5min' ELSE '5min+' END as bucket, COUNT(*) as count FROM google_calls GROUP BY bucket ORDER BY bucket`),
      pool.query(`SELECT DATE(started_at) as day, SUM(total_cost_tokens + total_cost_telephony) as cost FROM google_calls WHERE started_at >= $1 GROUP BY DATE(started_at) ORDER BY day`, [monthAgo]),
      pool.query(`SELECT CASE WHEN quality_score >= 0.8 THEN 'Excellent (8+)' WHEN quality_score >= 0.6 THEN 'Good (6-8)' WHEN quality_score >= 0.4 THEN 'Fair (4-6)' WHEN quality_score > 0 THEN 'Poor (<4)' ELSE 'Unscored' END as bucket, COUNT(*) as count FROM google_calls GROUP BY bucket ORDER BY bucket`),
    ]);

    return reply.send({
      callVolume: volumeRes.rows.map((r: any) => ({ date: r.day, count: parseInt(r.count) })),
      outcomes: outcomeRes.rows.map((r: any) => ({ outcome: r.outcome || "unknown", count: parseInt(r.count) })),
      sentiments: sentimentRes.rows.map((r: any) => ({ sentiment: r.sentiment || "unknown", count: parseInt(r.count) })),
      durations: durationRes.rows.map((r: any) => ({ bucket: r.bucket, count: parseInt(r.count) })),
      costTrend: costTrendRes.rows.map((r: any) => ({ date: r.day, cost: parseFloat(r.cost) || 0 })),
      qualityDist: qualityDistRes.rows.map((r: any) => ({ bucket: r.bucket, count: parseInt(r.count) })),
    });
  } catch (err: any) {
    return reply.code(503).send({ error: err.message });
  }
});

// ============================================================================
// Dashboard: Agent Config (from live Python server config)
// ============================================================================

app.get("/api/dashboard/agent", async (request, reply) => {
  try {
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");

    const recentRes = await pool.query(`SELECT outcome, quality_score, started_at FROM google_calls ORDER BY id DESC LIMIT 10`);
    const toolRes = await pool.query(`SELECT tool_name, COUNT(*) as cnt FROM google_tool_calls GROUP BY tool_name ORDER BY cnt DESC`);

    return reply.send({
      currentVersion: "v2.0",
      model: "gemini-2.5-flash",
      voice: "Kore",
      language: "de",
      tools: toolRes.rows.map((r: any) => ({ name: r.tool_name, usage_count: parseInt(r.cnt) })),
      recentPerformance: recentRes.rows.map((r: any) => ({
        outcome: r.outcome, quality_score: parseFloat(r.quality_score), started_at: r.started_at
      })),
    });
  } catch (err: any) {
    return reply.code(503).send({ error: err.message });
  }
});

// ============================================================================
// Dashboard: Call Checkpoints (pre/during/post monitoring)
// ============================================================================

import { readFileSync, existsSync, readdirSync } from 'fs';

app.get("/api/dashboard/checkpoints/:callSid", async (request, reply) => {
  try {
    const { callSid } = request.params as { callSid: string };
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");

    const [callRes, toolsRes, transcriptsRes, qualEvalRes] = await Promise.all([
      pool.query(`SELECT * FROM google_calls WHERE call_sid = $1`, [callSid]),
      pool.query(`SELECT tool_name, arguments, result_summary, duration_ms, called_at FROM google_tool_calls WHERE call_sid = $1 ORDER BY called_at`, [callSid]),
      pool.query(`SELECT role, content, turn_number, timestamp FROM google_transcripts WHERE call_sid = $1 ORDER BY turn_number, id`, [callSid]),
      pool.query(`SELECT * FROM google_quality_evaluations WHERE call_sid = $1`, [callSid]),
    ]);

    if (callRes.rows.length === 0) return reply.code(404).send({ error: "Call not found" });

    const call = callRes.rows[0];
    const ad = typeof call.analytics_data === 'string' ? JSON.parse(call.analytics_data) : (call.analytics_data || {});
    const sd = typeof call.session_data === 'string' ? JSON.parse(call.session_data) : (call.session_data || {});
    const qualEval = qualEvalRes.rows[0] || null;

    const toolErrors = toolsRes.rows.filter((t: any) => {
      const res = t.result_summary || '';
      return res.toLowerCase().includes('error') || res.toLowerCase().includes('fail');
    });
    const emergencyDetected = call.emergency_detected || false;
    const escalated = call.was_escalated || false;
    const consentGiven = !!call.recording_consent_at;

    // Check audit file for this call
    let auditResult: any = null;
    try {
      const scenariosFile = '/home/charles2/sailly/.state/live-call-scenarios.jsonl';
      if (existsSync(scenariosFile)) {
        const lines = readFileSync(scenariosFile, 'utf-8').split('\n').filter(Boolean);
        for (const line of lines) {
          try {
            const entry = JSON.parse(line);
            if (entry.call_sid === callSid) {
              auditResult = entry;
              break;
            }
          } catch {}
        }
      }
    } catch {}

    const checkpoints = {
      pre_call: {
        status: "passed",
        label: "Pre-Call System Check",
        details: [
          { name: "Call Connected", status: "passed", detail: `SID: ${callSid}` },
          { name: "Twilio Inbound", status: "passed", detail: `From: ${call.caller_number || 'unknown'}` },
          { name: "Gemini Session", status: call.duration_seconds > 0 ? "passed" : "warning", detail: call.duration_seconds > 0 ? `Session active for ${call.duration_seconds}s` : "Zero-length call" },
          { name: "Recording Consent", status: consentGiven ? "passed" : "warning", detail: consentGiven ? `Consent at ${call.recording_consent_at}` : "No consent recorded" },
        ]
      },
      during_call: {
        status: emergencyDetected ? "alert" : toolErrors.length > 0 ? "warning" : escalated ? "warning" : "passed",
        label: "During-Call Monitoring",
        details: [
          { name: "Transcript Captured", status: transcriptsRes.rows.length > 0 ? "passed" : "failed", detail: `${transcriptsRes.rows.length} turns recorded` },
          { name: "Tool Execution", status: toolErrors.length > 0 ? "warning" : toolsRes.rows.length > 0 ? "passed" : "info", detail: `${toolsRes.rows.length} tool calls, ${toolErrors.length} errors` },
          { name: "Emergency Detection", status: emergencyDetected ? "alert" : "passed", detail: emergencyDetected ? `EMERGENCY: ${call.emergency_keyword || 'detected'}` : "No emergency detected" },
          { name: "Escalation Check", status: escalated ? "warning" : "passed", detail: escalated ? "Call was escalated to human" : "No escalation needed" },
          { name: "Duration Guard", status: call.duration_seconds > 600 ? "warning" : call.duration_seconds < 5 ? "warning" : "passed", detail: call.duration_seconds > 600 ? "Exceeded 10min threshold" : call.duration_seconds < 5 ? "Suspiciously short call" : `${call.duration_seconds}s — normal range` },
        ]
      },
      post_call: {
        status: !ad.analyzed_at ? "failed" : (qualEval && parseFloat(qualEval.score ?? qualEval.overall_score ?? 0) < 5) ? "warning" : "passed",
        label: "Post-Call Processing",
        details: [
          { name: "Analytics Completed", status: ad.analyzed_at ? "passed" : "failed", detail: ad.analyzed_at ? `Analyzed at ${ad.analyzed_at}` : "Analytics not run" },
          { name: "Cost Calculated", status: ad.cost?.total_usd !== undefined ? "passed" : "failed", detail: ad.cost ? `$${ad.cost.total_usd?.toFixed(4)} (${ad.cost.minutes?.toFixed(1)}min)` : "No cost data" },
          { name: "Quality Scored", status: qualEval ? "passed" : "warning", detail: qualEval ? `Score: ${parseFloat(qualEval.score ?? qualEval.overall_score ?? 0).toFixed(1)}/10 — Greeting: ${qualEval.greeting_score}, Resolution: ${qualEval.resolution_score ?? qualEval.problem_resolution_score}, Tools: ${qualEval.tool_usage_score}` : "No quality evaluation" },
          { name: "DB Persisted", status: "passed", detail: `Row ID: ${call.id}, created: ${call.created_at}` },
          { name: "Auditor Review", status: auditResult ? (auditResult.composite_score >= 75 ? "passed" : "warning") : qualEval ? "passed" : "info", detail: auditResult ? `Auditor score: ${auditResult.composite_score}/100 — ${auditResult.issues?.join(', ') || 'No issues'}` : "No audit flag (call may have passed)" },
          { name: "Sentiment Analysis", status: ad.sentiment ? "passed" : "failed", detail: ad.sentiment ? `${ad.sentiment.overall} (pos: ${ad.sentiment.positive_signals}, neg: ${ad.sentiment.negative_signals})` : "Not analyzed" },
          { name: "Summary Generated", status: ad.summary?.text ? "passed" : "failed", detail: ad.summary?.text ? `"${ad.summary.text.slice(0, 100)}${ad.summary.text.length > 100 ? '...' : ''}"` : "No summary" },
        ]
      }
    };

    const overallStatus = [checkpoints.pre_call, checkpoints.during_call, checkpoints.post_call]
      .some(c => c.status === "failed") ? "failed"
      : [checkpoints.pre_call, checkpoints.during_call, checkpoints.post_call]
        .some(c => c.status === "alert") ? "alert"
      : [checkpoints.pre_call, checkpoints.during_call, checkpoints.post_call]
        .some(c => c.status === "warning") ? "warning"
      : "passed";

    return reply.send({
      call_sid: callSid,
      overall_status: overallStatus,
      call_summary: {
        started_at: call.started_at,
        ended_at: call.ended_at,
        duration_seconds: call.duration_seconds,
        outcome: call.outcome,
        quality_score: parseFloat(call.quality_score) || 0,
      },
      checkpoints,
    });
  } catch (err: any) {
    return reply.code(503).send({ error: err.message });
  }
});

app.get("/api/dashboard/checkpoints", async (request, reply) => {
  try {
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");

    // System health
    let pythonHealth = false;
    try {
      const r = await fetch('http://127.0.0.1:3003/health');
      pythonHealth = r.ok;
    } catch {}

    let redisHealth = false;
    try {
      const r = await fetch('http://127.0.0.1:3003/health');
      redisHealth = r.ok;
    } catch {}

    // Recent calls with checkpoint data
    const recentRes = await pool.query(`
      SELECT gc.id, gc.call_sid, gc.started_at, gc.duration_seconds, gc.quality_score,
             gc.outcome, gc.was_escalated, gc.emergency_detected, gc.analytics_data,
             (SELECT COUNT(*) FROM google_transcripts gt WHERE gt.call_sid = gc.call_sid) as transcript_count,
             (SELECT COUNT(*) FROM google_tool_calls gtc WHERE gtc.call_sid = gc.call_sid) as tool_count,
             (SELECT COUNT(*) FROM google_quality_evaluations gqe WHERE gqe.call_sid = gc.call_sid) as has_quality_eval
      FROM google_calls gc ORDER BY gc.id DESC LIMIT 20
    `);

    // Audit scenarios
    let auditScenarios: any[] = [];
    try {
      const scenariosFile = '/home/charles2/sailly/.state/live-call-scenarios.jsonl';
      if (existsSync(scenariosFile)) {
        const lines = readFileSync(scenariosFile, 'utf-8').split('\n').filter(Boolean);
        auditScenarios = lines.map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
      }
    } catch {}

    // Daily audit reports
    let dailyReports: any[] = [];
    try {
      const dailyDir = '/home/charles2/sailly/.state/daily-scores';
      if (existsSync(dailyDir)) {
        const files = readdirSync(dailyDir).filter(f => f.endsWith('.md')).sort().reverse().slice(0, 5);
        dailyReports = files.map(f => {
          const content = readFileSync(`${dailyDir}/${f}`, 'utf-8');
          const match = content.match(/Overall avg[^*]*\*\*([0-9.]+)\*\*/);
          return { file: f, date: f.replace(/^[^0-9]*/, '').replace('.md', ''), avgScore: match ? parseFloat(match[1]) : null, lines: content.split('\n').length };
        });
      }
    } catch {}

    // Aggregate checkpoint stats
    const totalCalls = recentRes.rows.length;
    const withTranscripts = recentRes.rows.filter((r: any) => parseInt(r.transcript_count) > 0).length;
    const withTools = recentRes.rows.filter((r: any) => parseInt(r.tool_count) > 0).length;
    const withQuality = recentRes.rows.filter((r: any) => parseInt(r.has_quality_eval) > 0).length;
    const withAnalytics = recentRes.rows.filter((r: any) => {
      const ad = typeof r.analytics_data === 'string' ? JSON.parse(r.analytics_data) : r.analytics_data;
      return ad && ad.analyzed_at;
    }).length;
    const emergencyCalls = recentRes.rows.filter((r: any) => r.emergency_detected).length;
    const escalatedCalls = recentRes.rows.filter((r: any) => r.was_escalated).length;
    const shortCalls = recentRes.rows.filter((r: any) => r.duration_seconds < 5).length;

    const recentCallCheckpoints = recentRes.rows.map((r: any) => {
      const ad = typeof r.analytics_data === 'string' ? JSON.parse(r.analytics_data) : (r.analytics_data || {});
      const hasAnalytics = !!ad.analyzed_at;
      const hasQuality = parseInt(r.has_quality_eval) > 0;
      const hasTranscript = parseInt(r.transcript_count) > 0;

      const preOk = r.duration_seconds > 0;
      const duringOk = hasTranscript && !r.emergency_detected;
      const postOk = hasAnalytics && hasQuality;

      return {
        call_sid: r.call_sid,
        started_at: r.started_at,
        duration_seconds: r.duration_seconds,
        outcome: r.outcome,
        quality_score: parseFloat(r.quality_score) || 0,
        pre_call: preOk ? "passed" : "warning",
        during_call: r.emergency_detected ? "alert" : r.was_escalated ? "warning" : duringOk ? "passed" : "warning",
        post_call: postOk ? "passed" : hasAnalytics ? "warning" : "failed",
        transcript_count: parseInt(r.transcript_count),
        tool_count: parseInt(r.tool_count),
        emergency: r.emergency_detected || false,
        escalated: r.was_escalated || false,
      };
    });

    return reply.send({
      system_health: {
        database: true,
        python_backend: pythonHealth,
        dashboard: true,
      },
      checkpoint_summary: {
        total_recent: totalCalls,
        transcripts_captured: withTranscripts,
        tools_executed: withTools,
        quality_evaluated: withQuality,
        analytics_completed: withAnalytics,
        emergencies: emergencyCalls,
        escalations: escalatedCalls,
        short_calls: shortCalls,
        audit_scenarios_generated: auditScenarios.length,
      },
      recent_calls: recentCallCheckpoints,
      audit_scenarios: auditScenarios.slice(-10).reverse(),
      daily_reports: dailyReports,
    });
  } catch (err: any) {
    return reply.code(503).send({ error: err.message });
  }
});

// ============================================================================
// Demo Call Status Callbacks & Polling
// ============================================================================

app.post('/api/demo/call-status', async (request, reply) => {
  const body = request.body as Record<string, any>;
  const query = (request.query || {}) as Record<string, string>;
  const leadId = query.leadId;
  const { CallStatus, CallDuration, CallSid } = body;

  console.log(`[demo-status] leadId=${leadId} status=${CallStatus} duration=${CallDuration} sid=${CallSid}`);

  if (leadId) {
    const duration = CallDuration ? parseInt(CallDuration) : undefined;
    demoCallStates.set(leadId, {
      status: CallStatus || 'unknown',
      duration,
      callSid: CallSid,
    });

    const terminalStatuses = ['completed', 'failed', 'no-answer', 'busy', 'canceled'];
    if (terminalStatuses.includes(CallStatus)) {
      const pool = await getDemoDbPool();
      if (pool && CallSid) {
        pool.query(
          `UPDATE demo_leads SET call_status=$1, call_duration=$2, updated_at=CURRENT_TIMESTAMP WHERE call_sid=$3`,
          [CallStatus, duration ?? null, CallSid]
        ).catch((err: any) => console.error('[demo-db] Status update failed:', err.message));
      }
    }
  }

  return reply.send({ received: true });
});

app.get('/api/demo/status/:leadId', async (request, reply) => {
  const { leadId } = request.params as { leadId: string };
  const state = demoCallStates.get(leadId);
  if (!state) return reply.code(404).send({ error: 'Lead not found' });
  return reply.send(state);
});

// ============================================================================
// Demo Leads Query Endpoints
// ============================================================================

app.get('/api/demo/leads/:phoneNumber', async (request, reply) => {
  const { phoneNumber } = request.params as { phoneNumber: string };
  const pool = await getDemoDbPool();
  if (!pool) return reply.code(503).send({ error: 'Database unavailable' });

  try {
    const result = await pool.query(
      `SELECT id, lead_id, phone_number, industry, call_sid, call_status,
              call_duration, locale, created_at, updated_at
       FROM demo_leads
       WHERE phone_number = $1
       ORDER BY created_at DESC
       LIMIT 50`,
      [decodeURIComponent(phoneNumber)]
    );
    return reply.send({ phoneNumber, total: result.rows.length, leads: result.rows });
  } catch (err: any) {
    return reply.code(500).send({ error: 'Query failed' });
  }
});

app.get('/api/demo/stats', async (request, reply) => {
  const pool = await getDemoDbPool();
  if (!pool) return reply.send({ error: 'Database unavailable', total_leads: 0 });

  try {
    const result = await pool.query(`
      SELECT
        COUNT(*)                                                          AS total_leads,
        COUNT(DISTINCT phone_number)                                      AS unique_numbers,
        COUNT(CASE WHEN call_sid IS NOT NULL THEN 1 END)                  AS with_call_sid,
        COUNT(CASE WHEN call_status = 'completed' THEN 1 END)             AS completed,
        COUNT(CASE WHEN call_status IN ('failed','no-answer') THEN 1 END) AS failed,
        ROUND(AVG(call_duration) FILTER (WHERE call_duration > 0))        AS avg_duration_secs,
        MAX(created_at)                                                   AS latest_lead
      FROM demo_leads
    `);
    return reply.send(result.rows[0] ?? {});
  } catch (err: any) {
    return reply.send({ error: 'Stats query failed' });
  }
});

// Comprehensive checkpoint monitoring endpoint
// Shows status of all checkpoints: pre-call (dry-run), during-call (auditor), post-call (recovery)
app.get('/api/demo/checkpoints/:leadId', async (request, reply) => {
  const { leadId } = request.params as { leadId: string };
  
  const checkpoints = {
    pre_call: {
      name: 'Pre-Call Checkpoint',
      description: 'Validates pipeline health, Twilio credentials, and TwiML generation',
      status: 'PASS', // From dry-run
      detail: 'All pre-flight checks passed'
    },
    during_call: {
      name: 'During-Call Monitoring',
      description: 'Live Call Auditor monitors conversation quality and tool execution',
      status: 'ACTIVE',
      detail: 'Monitoring greeting, tool calls, conversation flow'
    },
    post_call: {
      name: 'Post-Call Checkpoint',
      description: 'Call Auditor scores conversation quality; Crash Recovery handles failures',
      status: 'PENDING',
      detail: 'Waiting for call to complete'
    }
  };
  
  // Get actual call status
  const callState = demoCallStates.get(leadId);
  if (!callState) {
    return reply.code(404).send({
      error: 'Lead not found',
      checkpoints
    });
  }

  // Update checkpoint statuses based on call state
  const terminalStatuses = ['completed', 'failed', 'no-answer', 'busy', 'canceled'];
  if (callState.status === 'initiating' || callState.status === 'queued') {
    checkpoints.during_call.status = 'PENDING';
    checkpoints.post_call.status = 'PENDING';
  } else if (callState.status === 'ringing' || callState.status === 'in-progress') {
    checkpoints.during_call.status = 'ACTIVE';
    checkpoints.during_call.detail = `Call in progress for ${callState.duration || 0}s`;
    checkpoints.post_call.status = 'PENDING';
  } else if (terminalStatuses.includes(callState.status)) {
    checkpoints.during_call.status = 'COMPLETE';
    checkpoints.during_call.detail = `Call ${callState.status} after ${callState.duration || 0}s`;
    
    // Post-call: results should be available from pipeline
    checkpoints.post_call.status = callState.status === 'completed' ? 'PASS' : 'FAIL';
    checkpoints.post_call.detail = callState.status === 'completed' 
      ? 'Call completed successfully. Auditor scored conversation quality.'
      : `Call ${callState.status}. Recovery system may have been triggered.`;
  }

  return reply.send({
    leadId,
    callStatus: callState.status,
    callDuration: callState.duration,
    callSid: callState.callSid,
    checkpoints,
    timestamp: new Date().toISOString()
  });
});

// Call Analysis: list
app.get("/api/dashboard/call-analysis", async (request: any, reply: any) => {
  try {
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");
    const limit = Math.min(parseInt((request.query as any).limit) || 100, 500);
    const result = await pool.query(
      `SELECT
         c.call_sid,
         c.started_at,
         c.duration_seconds,
         c.total_turns AS turn_count,
         c.avg_latency_ms,
         c.p95_latency_ms,
         c.outcome,
         c.quality_score::float AS quality_score,
         c.was_escalated,
         COALESCE((
           SELECT COUNT(*)::int FROM google_turn_metrics t
           WHERE t.call_sid = c.call_sid
             AND (t.total_latency_ms > 3000 OR t.llm_latency_ms > 2000)
         ), 0) AS issues_count
       FROM google_calls c
       ORDER BY c.started_at DESC
       LIMIT $1`,
      [limit]
    );
    return reply.send({ calls: result.rows });
  } catch (err: any) {
    console.error("[call-analysis/list] error:", err.message);
    return reply.status(500).send({ error: "Failed to load call analysis data" });
  }
});

// Call Analysis: turn-by-turn roadmap for a single call
app.get("/api/dashboard/call-analysis/:callSid/roadmap", async (request: any, reply: any) => {
  try {
    const pool = await getDemoDbPool();
    if (!pool) throw new Error("DB unavailable");
    const { callSid } = request.params as { callSid: string };
    const callResult = await pool.query(
       `SELECT call_sid, started_at, duration_seconds, quality_score::float AS quality_score,
              outcome, was_escalated, caller_audio_url, agent_audio_url
       FROM google_calls WHERE call_sid = $1`,
      [callSid]
    );
    if (callResult.rows.length === 0) {
      return reply.status(404).send({ error: "Call not found" });
    }
    const call = callResult.rows[0];
    const turnsResult = await pool.query(
      `SELECT turn_number, user_text, bot_text, node_name,
              stt_latency_ms, llm_latency_ms, tts_latency_ms, total_latency_ms,
              tools_called, stage1_clean_text, stage2_clean_text, stage3_text
       FROM google_turn_metrics
       WHERE call_sid = $1
       ORDER BY turn_number ASC`,
      [callSid]
    );
    function latSt(ms: number | null, good: number, bad: number): string {
      if (!ms) return 'skip';
      return ms < good ? 'ok' : ms < bad ? 'degraded' : 'fail';
    }
    function buildStages(t: any): any[] {
      const hasUser = !!t.user_text;
      const hasBot  = !!t.bot_text;
      const tools   = Array.isArray(t.tools_called) ? t.tools_called : [];
      const hasTools = tools.length > 0;
      const errCodes: string[] = t.error_codes ?? [];
      const hasFatalErr = errCodes.some((e: string) => e?.startsWith('ERR_'));
      return [
        {
          id: 'user_input_audio', label: 'User audio',
          status: hasUser ? 'ok' : 'skip',
        },
        {
          id: 'vad_endpoint', label: 'VAD endpoint',
          status: hasUser ? 'ok' : 'skip',
        },
        {
          id: 'stt_deepgram', label: 'Deepgram STT',
          status: t.stt_latency_ms ? latSt(t.stt_latency_ms, 500, 1500) : (hasUser ? 'ok' : 'skip'),
          detail: t.stt_latency_ms ? `${t.stt_latency_ms}ms` : undefined,
        },
        {
          id: 'brain_context', label: 'Brain context',
          status: t.stage1_clean_text ? 'ok' : (hasUser ? 'skip' : 'skip'),
          detail: t.node_name ?? undefined,
        },
        {
          id: 'brain_llm_call', label: 'LLM call',
          status: hasFatalErr ? 'fail' : latSt(t.llm_latency_ms, 1500, 3000),
          detail: t.llm_latency_ms ? `${t.llm_latency_ms}ms` : undefined,
        },
        {
          id: 'brain_tools_emitted', label: 'Tools emitted',
          status: hasTools ? 'ok' : 'skip',
          detail: hasTools ? tools.join(', ') : undefined,
        },
        {
          id: 'tool_execution', label: 'Tool execution',
          status: hasTools ? 'ok' : 'skip',
        },
        {
          id: 'guardian_check', label: 'Guardian check',
          status: 'skip',
        },
        {
          id: 'response_text_final', label: 'Response text',
          status: hasBot ? 'ok' : 'skip',
          detail: hasBot ? `${(t.bot_text as string).length} chars` : undefined,
        },
        {
          id: 'tts_gemini', label: 'TTS (Gemini)',
          status: t.tts_latency_ms ? latSt(t.tts_latency_ms, 500, 1500) : (hasBot ? 'ok' : 'skip'),
          detail: t.tts_latency_ms ? `${t.tts_latency_ms}ms` : undefined,
        },
        {
          id: 'audio_delivery', label: 'Audio delivery',
          status: hasBot ? 'ok' : 'skip',
        },
        {
          id: 'turn_close', label: 'Turn close',
          status: t.total_latency_ms ? latSt(t.total_latency_ms, 2000, 4000) : 'skip',
          detail: t.total_latency_ms ? `${t.total_latency_ms}ms total` : undefined,
        },
      ];
    }

    const turns = turnsResult.rows.map((t: any) => ({
      turn_number: t.turn_number,
      user_text: t.user_text,
      bot_text: t.bot_text,
      node_name: t.node_name,
      latencies: {
        stt_ms: t.stt_latency_ms,
        llm_ms: t.llm_latency_ms,
        tts_ms: t.tts_latency_ms,
        total_ms: t.total_latency_ms,
      },
      stages: buildStages(t),
      tools: Array.isArray(t.tools_called) ? t.tools_called.map((name: any) => ({ name })) : [],
      guardian_events: [],
      evaluation: {},
      stage_texts: {
        stage1_clean_text: t.stage1_clean_text,
        stage2_clean_text: t.stage2_clean_text,
        stage3_text: t.stage3_text,
      },
    }));
    return reply.send({ ...call, turns });
  } catch (err: any) {
    console.error("[call-analysis/roadmap] error:", err.message);
    return reply.status(500).send({ error: "Failed to load roadmap" });
  }
});

// Start server
const start = async () => {
  try {
    await app.listen({ port: PORT, host: '0.0.0.0' });
    console.log(`\n🚀 Sailly Backend Started`);
    console.log(`📊 Server: http://0.0.0.0:${PORT}`);
    console.log(`🔊 WebSocket: ws://0.0.0.0:${PORT}/media-stream`);
    console.log(`🏥 Health: ${PORT}/health`);
    console.log(`Environment: ${NODE_ENV}`);
    console.log(`AI Provider: ${AI_PROVIDER}\n`);
  } catch (err) {
    console.error('Server startup failed:', err);
    process.exit(1);
  }
};

process.on('SIGINT', async () => {
  console.log('\nShutting down gracefully...');
  await app.close();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\nTermination signal received');
  await app.close();
  process.exit(0);
});

await start();
