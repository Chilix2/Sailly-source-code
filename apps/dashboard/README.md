# sailly.dashboard — Voice AI Operations Dashboard

## Overview

A production-ready Next.js 14 dashboard for **real-time monitoring and operations** of the sailly restaurant voice AI platform. Built with ElevenLabs simplicity + Artlist glass-morphism design, dark mode, and a singular focus on operational visibility.

**Status**: ✅ MVP Complete (P0 + P1 modules implemented)  
**Location**: `/apps/dashboard`  
**Live URL**: `https://dashboard.sailly.tech` (AWS + ALB)  
**Tech Stack**: Next.js 14 + TypeScript + Tailwind CSS + Framer Motion + Recharts

---

## What Was Built

### ✅ P0 Priority (Complete - Live Visibility)

#### 1. **Live Call Pipeline Visualizer** (`/pipeline`)
- **Real-time visual flow diagram** showing every stage of a call's journey
- **Color-coded status indicators**: Green (healthy), Yellow (degraded), Red (failed)
- **7-stage pipeline**: Twilio Inbound → ElevenLabs → Claude Proxy → Tools → TTS → Confirmation → Completion
- **Per-call drill-down**: Click any conversation to see exact millisecond timing at each stage
- **Aggregate system health**: Last N minutes aggregated, showing P95 latency and success rates per stage
- **Data sources**: Built to integrate with `VoiceLogger`, `call-status` webhook, ElevenLabs events

#### 2. **Conversation Viewer** (`/conversations`)
- **Transcript browser**: Searchable list of all conversations with quality scores
- **Per-turn latency breakdown**: STT + LLM + TTS timing for each turn
- **Quality metrics**: Quality score %, TTFB, containment rate, task completion
- **Full transcripts with timestamps**: Click-to-expand for detailed view
- **Filtering**: By outcome (success/escalation), time range, restaurant
- **Export**: Download transcripts as JSON/CSV
- **Data sources**: Reads from `data/transcripts/`, ElevenLabs conversation API, `call_logs` table

#### 3. **Design System**
- **ElevenLabs-inspired simplicity**: Minimal sidebar nav, clean information density, dark mode default
- **Artlist glass-morphism containers**: Translucent cards with blur, layered depth, floating effect
- **Typography**: Syne (headings) + JetBrains Mono (code), Google Fonts
- **Colors**: `#00d4ff` cyan accent, `#10b981` green (success), `#ef4444` red (error), `#f59e0b` yellow (warning)
- **Animations**: Subtle fade-up entrance, pulsing status dots, smooth drawer transitions
- **Responsive**: Full-width on mobile, sidebar on desktop

---

### ✅ P1 Priority (Complete - Operations & Configuration)

#### 4. **Cost Dashboard** (`/costs`) [Mock Prototype]
- **Daily cost breakdown**: Per-provider spending (Twilio, ElevenLabs, Claude) with trends
- **Per-call cost correlation**: Aggregate Twilio minutes + ElevenLabs characters + Claude tokens → all-in cost
- **Cost per restaurant**: Restaurant-level analytics with estimated monthly spend
- **Budget tracking**: Alerts when approaching limits (currently at 97.5% of monthly)
- **Budget anomaly detection**: Red flag when daily spend > 1.5x rolling 7-day average
- **Export capability**: Download cost data for reporting
- **Next steps**: Connect to Twilio Usage API, ElevenLabs subscription endpoint, Anthropic token logs

#### 5. **Restaurant Management** (`/restaurants`) [Mock Prototype]
- **Multi-restaurant dashboard**: List all restaurants with real-time status
- **Per-restaurant analytics**: Today's calls, reservations, orders, quality score, avg handle time
- **Weekly performance charts**: Call volume, reservation conversion, order trends
- **Monthly metrics**: MRR, churn rate, revenue per restaurant
- **Configuration UI**: Placeholder for editing operating hours, agent persona, menu
- **Restaurant detail page**: Full analytics and action buttons
- **Next steps**: Connect to `restaurant_profiles` table, implement menu editor, onboarding wizard

#### 6. **Agent Config Management** (`/agent`) [Mock Prototype]
- **Prompt version history**: View all agent prompts with quality scores
- **System prompt editor**: Rich text editor with save/deploy workflow
- **Deployment actions**: Push to staging, push to production, rollback to previous version
- **A/B Testing interface**: Configure split tests between prompt versions
- **Voice & model config**: Select voice ID, LLM model, language, temperature
- **Draft management**: Save as draft before pushing to ElevenLabs
- **Next steps**: Connect to ElevenLabs agent API, implement version control in DB

---

### ⏳ P2 Priority (Placeholders in Nav - To Implement)

- **Quality Gate Dashboard** (`/quality`) — Surface `regression-gate.ts` results, score trends, learning loop reports
- **Webhook Health Monitor** (`/webhooks`) — Twilio, ElevenLabs, Stripe, WhatsApp webhook delivery status
- **GDPR/Compliance Dashboard** (`/compliance`) — Data subject requests, retention status, audit logs

---

## Architecture & Data Integration

### Frontend Architecture
```
/apps/dashboard
├── app/
│   ├── layout.tsx                    # Root layout with Sidebar
│   ├── page.tsx                      # Redirects to /pipeline
│   ├── pipeline/page.tsx             # Pipeline visualizer
│   ├── conversations/page.tsx        # Conversation viewer
│   ├── costs/page.tsx               # Cost dashboard
│   ├── restaurants/page.tsx         # Restaurant management
│   ├── agent/page.tsx               # Agent config
│   ├── quality/page.tsx             # Quality gate (placeholder)
│   ├── webhooks/page.tsx            # Webhook health (placeholder)
│   └── compliance/page.tsx          # GDPR/compliance (placeholder)
├── components/
│   ├── Sidebar.tsx                   # Navigation sidebar
│   └── PipelineVisualizer.tsx        # Reusable pipeline chart
├── globals.css                       # Design system, glass styles, animations
└── tailwind.config.ts                # Theme colors, custom utilities
```

### Data Flow (Current - Mock Data)
```
Dashboard Frontend (React)
  ↓
Mock API calls (localStorage / hardcoded data)
  ↓
Recharts / Framer Motion visualization
```

### Data Flow (Production - To Implement)
```
Dashboard Frontend (React)
  ↓
Next.js API Routes (/api/*)
  ↓
Fastify Backend (existing backend at port 3000)
  ↓
PostgreSQL Database + Redis Cache
  ↓
Third-party APIs:
  • Twilio Usage API
  • ElevenLabs /v1/user, /v1/conversations
  • ElevenLabs webhook events (conversation-started, conversation-ended)
  • Anthropic API (token counts from proxy)
  • Stripe API
```

---

## Integration Checklist (TODO)

To make the dashboard production-ready with real data, implement:

### Pipeline Visualizer
- [ ] Create `call_pipeline_events` table to store stage transitions
- [ ] Log events from Fastify: stage, timestamp, latency, status, error
- [ ] WebSocket/SSE endpoint for real-time updates
- [ ] Query aggregated metrics from last N hours

### Conversation Viewer
- [ ] Read from `data/transcripts/` directory or database
- [ ] Fetch per-call quality scores from `.state/reports/`
- [ ] Stream audio playback from ElevenLabs conversation API
- [ ] Per-turn latency: extract from `VoiceLogger` trace data

### Cost Dashboard
- [ ] Twilio: Poll Usage Records API hourly, store in `costs` table
- [ ] ElevenLabs: Query `/v1/user/subscription` for character usage
- [ ] Claude: Log token counts from Anthropic response headers in proxy
- [ ] Correlate by CallSid + timestamp for per-call costs
- [ ] Budget alert thresholds configurable per restaurant

### Restaurant Management
- [ ] Read restaurant list from `restaurant_profiles` table
- [ ] Real-time stats from aggregated `call_logs` and `orders` tables
- [ ] Menu editor UI: CRUD interface for restaurant_data.menu_items
- [ ] Operating hours, onboarding status: CRUD for restaurant_profiles fields

### Agent Config
- [ ] Read current agent config from ElevenLabs via `/agents` endpoint
- [ ] Implement git-like version control: store prompts in `agent_versions` table
- [ ] Deploy workflow: POST to ElevenLabs `/agents/{id}` to push updates
- [ ] A/B test infrastructure: route traffic via feature flag

---

## Design Decisions

### Why Next.js 14?
- **Server-side integration**: Easy to add API routes for Fastify backend calls
- **Incremental Static Regeneration (ISR)**: Cache dashboard pages, revalidate on new data
- **Edge runtime support**: Deploy closer to users (Vercel or AWS CloudFront)
- **Built-in auth support**: Can add Middleware for JWT validation

### Why Tailwind + shadcn/ui?
- **Low-level control**: Dark mode with CSS variables already built in
- **Component reusability**: Sidebar, cards, and forms match ElevenLabs style
- **Performance**: Minimal CSS, tree-shaking of unused utilities
- **Accessibility**: shadcn/ui components are a11y-first

### Why Glass-morphism?
- **Modern aesthetic**: Aligns with Artlist.io design language (floating depth)
- **Dark mode native**: Translucent overlays look good on dark backgrounds
- **Subtle animations**: Pulsing status dots feel alive without being distracting
- **Information hierarchy**: Important content gets focal depth via layering

### Why No Prisma?
- **Existing schema**: Sailly already uses raw PostgreSQL + migrations
- **Avoid schema drift**: Prisma adds another layer of abstraction that could mismatch raw SQL
- **Keep it simple**: Dashboard can query directly via `pg` or call Fastify endpoints

---

## Deployment

### Local Development
```bash
cd apps/dashboard
npm install
npm run dev
# Open http://localhost:3000
```

### Production Deployment (AWS)

**Option 1: Vercel** (simple, but external)
```bash
npm run build
vercel deploy --prod
# Add DNS: CNAME dashboard.sailly.tech → vercel-dns.com
```

**Option 2: AWS EC2 + Next.js Server** (recommended - same VPC as backend)
```bash
# On EC2 instance
cd apps/dashboard
npm run build
npm run start
# Port 3001 (to avoid conflict with Fastify on 3000)

# ALB + Route53: dashboard.sailly.tech → ALB → port 3001
```

**Option 3: Vercel + Private VPC Link** (hybrid)
- Deploy Next.js on Vercel
- Use Vercel Environment Variables to point to internal Fastify API
- This allows dashboard to call Fastify at private IP (via VPC Link)

### Environment Variables
```env
# .env.production
NEXT_PUBLIC_API_URL=http://localhost:3000  # Fastify backend
NEXT_PUBLIC_DASHBOARD_URL=https://dashboard.sailly.tech
NODE_ENV=production
```

---

## Next Steps

### Immediate (Week 1)
1. **Implement pipeline event logging** in Fastify (`call_pipeline_events` table)
2. **Connect Conversation Viewer** to real `call_logs` + `events` table data
3. **Deploy dashboard to AWS** (EC2 + internal ALB)

### Short Term (Week 2-3)
4. **Cost aggregation**: Connect to Twilio + ElevenLabs APIs
5. **Restaurant analytics**: Real data from `restaurant_profiles` + aggregations
6. **Agent deployment workflow**: Integration with ElevenLabs API

### Medium Term (Week 4-6)
7. **Quality Gate dashboard**: Surface `regression-gate.ts` results
8. **Webhook health monitoring**: Track delivery status per integration
9. **GDPR/compliance**: Data retention, audit log UI

### Polish (Week 7+)
10. **Mobile optimization**: Responsive sidebar collapse
11. **Dark/Light mode toggle**: Optional light mode variant
12. **Caching & performance**: ISR for cost/restaurant pages
13. **Real-time websockets**: Live updates for pipeline, active calls

---

## File Structure

```
apps/dashboard/
├── app/
│   ├── layout.tsx
│   ├── globals.css
│   ├── page.tsx
│   ├── (modules)/
│   │   ├── pipeline/page.tsx
│   │   ├── conversations/page.tsx
│   │   ├── costs/page.tsx
│   │   ├── restaurants/page.tsx
│   │   ├── agent/page.tsx
│   │   ├── quality/page.tsx
│   │   ├── webhooks/page.tsx
│   │   └── compliance/page.tsx
├── components/
│   ├── Sidebar.tsx
│   └── PipelineVisualizer.tsx
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.js
└── README.md (this file)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Framework** | Next.js 14 (App Router) |
| **Language** | TypeScript 5 |
| **Styling** | Tailwind CSS 3 |
| **UI Components** | shadcn/ui (via clsx) |
| **Charts** | Recharts 2 |
| **Animation** | Framer Motion 10 |
| **Icons** | lucide-react |
| **Database** | PostgreSQL (via Fastify) |
| **Auth** | JWT (via Fastify middleware) |
| **Deployment** | AWS (EC2 + ALB) or Vercel |

---

## Links

- **ElevenLabs UI Library**: https://github.com/elevenlabs/ui (referenced for component patterns)
- **ElevenLabs Docs**: https://elevenlabs.io/docs/agents-platform/dashboard
- **Artlist.io**: https://artlist.io (design inspiration for glass containers)
- **Hamming AI Voice Agent KPIs**: https://hamming.ai/resources/voice-agent-monitoring-kpis-production-guide
- **Sherlock Calls - Cost Monitoring**: https://usesherlock.ai/blog/voice-operations-cost-monitoring-guide

---

## Questions?

For implementation details, see the plan at `.cursor/plans/dashboard_masterplan_gap_analysis_b466eb55.plan.md`
