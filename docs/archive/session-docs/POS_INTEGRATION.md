# POS Integration — Current State & Operational Gap

**Status:** Sprint 0 — documentation only. No live POS/KDS write path is wired yet.

This document describes how orders flow from Sailly to the restaurant **today**
and what must change before we can claim "end-to-end automated order capture".
It is the source of truth for the operational gap that the `pos_webhook_url`
tenant-config field (added in Sprint 0) is intended to close.

---

## Today's order path

```
caller → Sailly brain → tools.executor._create_order →
  ┌─ Redis idempotency key            (prevents dupes on pipeline retry)
  ├─ in-memory `order_store` dict      (process-local, lost on restart)
  └─ SMS/WhatsApp via sms_service.send_confirmation
        → Twilio (payment link to caller's phone)
```

`_create_order` does **not** POST to any POS, KDS, Toast/Square/Lightspeed,
Wolt or Lieferando endpoint. The confirmation SMS is the **only** external
write that leaves the server.

### How the kitchen currently sees orders

1. The customer receives the payment-link SMS (production Twilio) and pays.
2. A human team member watches an internal dashboard **or** the Twilio SMS
   inbox and manually re-keys the order into the POS.
3. There is no automated failure surface if the human forgets a step.

**This is acceptable for a single-pilot deployment with a staffed phone**
but it is **not** acceptable at scale. It is the biggest operational risk in
production today.

---

## What Sprint 1 will wire

Sprint 1 introduces `pos_webhook_url` (already added to `TenantConfig` in
Sprint 0). When set, `_create_order` will:

1. Write the order to durable Redis (`order:{call_sid}` hash, replacing the
   in-memory dict).
2. POST the canonical order payload to `pos_webhook_url` with exponential
   back-off (3 attempts, 1s → 3s → 9s).
3. Record success/failure on the order record so the dashboard can surface
   undelivered orders.
4. **Always** send the customer SMS — webhook failure does NOT fail the call.
   The order is recorded on our side and the kitchen is notified out-of-band.

### Canonical payload (Sprint 1, draft)

```json
{
  "order_id": "ord_<uuid>",
  "tenant_id": "doboo",
  "created_at": "2026-04-21T14:31:07Z",
  "customer": {
    "name": "Julius Müller",
    "phone": "+491701234567",
    "caller_id_confirmed": true,
    "bell_name": "Müller"
  },
  "delivery": {
    "type": "delivery",        // or "pickup"
    "address": "Hauptstraße 11, Bonn",
    "verified": true
  },
  "items": [
    {"name": "Bulgogi", "qty": 1, "unit_price_eur": 16.90},
    {"name": "Mandu",   "qty": 1, "unit_price_eur": 7.90}
  ],
  "totals": {
    "subtotal_eur": 24.80,
    "delivery_fee_eur": 0.00,
    "total_eur": 24.80
  },
  "eta_minutes": 35,
  "source": "sailly_voice",
  "call_sid": "twilio-XXXX"
}
```

### Supported POS targets (rollout order)

| # | Target | Priority | Notes |
|---|--------|----------|-------|
| 1 | Generic webhook (tenant-hosted) | High | Minimum viable — tenant owns the bridge |
| 2 | Lieferando / Takeaway.com | Medium | Partner API access required |
| 3 | Wolt Merchant API | Medium | EU partner priority |
| 4 | Lightspeed Restaurant | Low | Complex auth, covered by Sprint 3+ |

We deliberately do NOT integrate with Toast/Square first — they are
US-centric and DOBOO is the only near-term tenant.

---

## Security considerations (before enabling webhook POST)

- **No PII in logs.** Webhook URL is not logged at INFO. Payload is logged
  at DEBUG only with phone numbers redacted (last 4 digits).
- **Signed requests.** Sprint 1 will HMAC the payload with a per-tenant
  secret (`pos_webhook_secret`) in the `X-Sailly-Signature` header. The
  secret is NOT stored in the tenant YAML — only an env-var reference.
- **Idempotency.** The receiver MUST treat `order_id` as idempotent. Our
  retry loop does not assume the first POST failed cleanly.
- **Timeouts.** 5s per attempt; failing fast keeps the brain pipeline
  responsive. No synchronous wait on the webhook from inside `_create_order`.

---

## Current workaround (until Sprint 1 ships)

- Production traffic is single-tenant (DOBOO) with a human reviewer.
- The dashboard at `/calls` surfaces each completed call with its order
  summary. Staff watches this in real time during service hours.
- Any missed order falls through to the customer SMS — they still got the
  payment link, and a missing kitchen ticket is visible because payment
  arrives with no corresponding ticket.

**When this doc becomes obsolete:** once Sprint 1 merges `pos_webhook_url`
plumbing and a real tenant points it at a working webhook endpoint, delete
the "Today's order path" section and update this file to describe the new
flow.
