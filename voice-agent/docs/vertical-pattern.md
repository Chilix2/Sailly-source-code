# How to Add Restaurant #2 — Vertical Pattern Guide

This guide explains the multi-tenant architecture of Sailly and the steps
required to onboard a new restaurant vertical without touching shared brain code.

---

## Core Principle

> **All restaurant-specific content lives in `configs/tenants/<id>.yaml`.
> The brain (`server/brain/`) and tools (`tools/`) are vertical-agnostic.**

A CI check (`scripts/verify_no_hardcoded_tenants.py`) enforces this boundary
and will fail the build if DOBOO/Bibimbap/etc. appear in brain code without
the `# tenant-specific fallback` annotation.

---

## Step 1 — Create the YAML file

Copy `configs/tenants/doboo.yaml` to `configs/tenants/<new_id>.yaml`.

Edit these sections:

```yaml
tenant_id: <new_id>          # e.g. "kimchilove"
restaurant_name: "Kimchi Love Korean BBQ"
cuisine_type: "Koreanisch (BBQ, Hot Pot, Bibimbap)"

location:
  address: "Musterstraße 1, 12345 Berlin"
  city: "Berlin"
  lat: 52.5200
  lng: 13.4050
  parking: "Öffentliches Parkhaus 200m entfernt"

opening_hours:
  monday:    "12:00–22:00"
  # ... etc
  formatted: "Mo–So 12:00–22:00"

menu:
  categories:
    - name: "Hauptgerichte"
      items:
        - name: "Galbi"
          price: 19.90
          description: "Marinierte Rinderrippen vom Grill"
          vegetarian: false
          allergens: ["Soja", "Sesam"]
        # ... more items

audio:
  stt_model: "flux-general-de"
  stt_endpoint: "wss://api.eu.deepgram.com/v2/listen"
  stt_endpointing_ms: 700
  smart_format: true

twilio_numbers:
  - "+4930123456789"

greeting_line: "Hallo, hier ist Sailly, die KI-Assistentin von Kimchi Love. Was kann ich für Sie tun?"
farewell_text: "Vielen Dank für Ihren Anruf bei Kimchi Love! Auf Wiedersehen."
```

---

## Step 2 — Validate the YAML

Run the schema validator to catch missing required fields:

```bash
python -c "
from server.configs.tenant_schema import load_and_validate
schema = load_and_validate('configs/tenants/kimchilove.yaml')
print(f'Valid: {schema.restaurant_name} ({schema.tenant_id})')
"
```

---

## Step 3 — Route Twilio calls

In your Twilio console, configure the webhook for the new number to point to:

```
POST https://<your-server>/twilio/voice?tenant=kimchilove
```

The `TenantRegistry` in `server/core/tenant_config.py` will load the correct
YAML based on the `tenant` query param.

---

## Step 4 — Verify CI guard passes

```bash
python scripts/verify_no_hardcoded_tenants.py --root .
# Should print: [CI] Vertical boundary check PASSED
```

---

## What the brain reads from tenant config

| Brain file | Field read |
|------------|-----------|
| `adk_turn_processor.py` | `farewell_text`, `restaurant_name` (via `self._tenant`) |
| `tier2_runner.py` | `restaurant_name`, `location.address`, `opening_hours.formatted` |
| `main.py` | `audio.stt_model`, `audio.stt_endpoint`, `stt_language` |
| `stt/keyterm_loader.py` | `menu.categories[].items[].name` + `asr_keywords()` |
| `node_manager.py` | `greeting_line`, `agent_name`, `hours_formatted` |

---

## What you do NOT need to touch

- `server/brain/` — vertical-agnostic; reads everything via `self._tenant`
- `tools/` — reads restaurant name from `os.getenv("RESTAURANT_NAME")` or tenant config
- `server/configs/tenant_schema.py` — add new optional fields only if needed

---

## CI enforcement

`.github/workflows/ci.yml` runs `scripts/verify_no_hardcoded_tenants.py` on
every push and pull request targeting `main`. A failing check blocks the merge.

To temporarily allow a hardcoded value (e.g. a reasonable runtime fallback),
annotate the line with `# tenant-specific fallback`:

```python
farewell = self._tenant.farewell_text if self._tenant else "Auf Wiedersehen."  # tenant-specific fallback
```
