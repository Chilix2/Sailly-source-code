# Vertical Audit — Hardcoded Tenant Content

*Generated: Phase 5 C1 audit of `server/brain/` and `tools/`.*

This document classifies every occurrence of DOBOO/Bibimbap/Bulgogi/Japchae/Friedrichstraße
found in the codebase outside of `configs/tenants/` and test fixtures.

## Classification Key

- **MOVE-TO-YAML** — content belongs in `configs/tenants/<tenant>.yaml`; remove from Python
- **VERTICAL-GENERIC** — code is structurally generic but uses DOBOO data as a default/fallback; annotate with `# tenant-specific fallback`
- **DEAD-CODE** — legacy code path no longer exercised in production; safe to remove
- **EXAMPLE-ONLY** — appears in comments or docstring examples; acceptable

---

## server/brain/adk_turn_processor.py

| Line | Pattern | Content | Classification |
|------|---------|---------|----------------|
| 149 | Bibimbap | `"Ich möchte Bibimbap bestellen"` in module-level test stub | EXAMPLE-ONLY (doctest) |
| 480 | Friedrichstraße | Comment in address correction detection | EXAMPLE-ONLY (comment) |
| 1698 | DOBOO | Fallback farewell text `"Vielen Dank für Ihren Anruf bei DOBOO!"` | VERTICAL-GENERIC (uses `self._tenant.farewell_text` first) |
| 1755 | DOBOO | Same farewell fallback (second call site) | VERTICAL-GENERIC |
| 1940 | DOBOO | Comment: "Strip hallucinated features that don't exist at DOBOO" | EXAMPLE-ONLY (comment) |

**Action**: The farewell fallbacks at lines 1698/1755 are acceptable — `self._tenant.farewell_text` is used first; hardcoded string is a safety net. Add `# tenant-specific fallback` annotation to both.

---

## server/brain/tier2_runner.py

| Line | Pattern | Content | Classification |
|------|---------|---------|----------------|
| 195 | DOBOO | System prompt: `"Du bist Sailly, die KI-Rezeptionistin vom Restaurant DOBOO"` | MOVE-TO-YAML |
| 229 | Bibimbap/Bulgogi/Japchae | Full dish list hardcoded in system prompt | MOVE-TO-YAML |
| 284 | Bulgogi | Example in prompt rules | MOVE-TO-YAML |
| 291 | Bibimbap/Mochi-Eis | Example recommendation sentence | MOVE-TO-YAML |
| 300/307/311 | Bibimbap/Bulgogi | Example order sentences in prompt | MOVE-TO-YAML |
| 339 | Bibimbap | Example small-talk bridge | MOVE-TO-YAML |
| 362 | DOBOO | Greeting in prompt | MOVE-TO-YAML |
| 365/370 | Bibimbap/DOBOO | Example/summary lines | MOVE-TO-YAML |

**Action (C2)**: Replace hardcoded system prompt with tenant-config-driven template reading `restaurant_name`, `menu`, `greeting_line` from YAML.

---

## server/brain/conversation_state.py

| Line | Pattern | Content | Classification |
|------|---------|---------|----------------|
| 23-26 | Bibimbap/Bulgogi/Japchae/Mochi-Eis | `KNOWN_DISHES` default list | MOVE-TO-YAML (or VERTICAL-GENERIC if kept as static default) |
| 483/520 | Friedrichstraße | Comment explaining address parsing edge case | EXAMPLE-ONLY (comment) |
| 665/760/1449/1456/1511 | Bibimbap/Bulgogi | Comments/docstrings explaining deduplication logic | EXAMPLE-ONLY (comment) |
| 1535 | DOBOO | Comment: "Prefers cached_menu (real DOBOO data)" | EXAMPLE-ONLY (comment) |
| 1949 | Friedrichstraße | Comment: "so street numbers don't contaminate" | EXAMPLE-ONLY (comment) |
| 2094-2095 | Bibimbap | Comment: "Hallucination root cause" example | EXAMPLE-ONLY (comment) |

**Action**: The `KNOWN_DISHES` list (lines 23-26) should be loaded from tenant config at startup via `set_known_items()` (already called in ADKTurnProcessor). The static list becomes a generic empty default. Comments are fine as-is.

---

## server/brain/layer2/system_prompt.py

| Line | Pattern | Content | Classification |
|------|---------|---------|----------------|
| 31-33 | Bibimbap | Few-shot example turn | EXAMPLE-ONLY (training example, language-generic) |
| 47 | Bulgogi-Bowl | Few-shot dietary inquiry | EXAMPLE-ONLY |

**Action**: Few-shot examples use dish names as generic food examples; acceptable. If adding non-restaurant verticals, generalize to `{dish_name}` placeholders.

---

## server/brain/layer1/nodes/ (multiple files)

Various node prompt files contain DOBOO/dish names in their prompt text:

| File | Classification |
|------|----------------|
| `_prompts.py` | MOVE-TO-YAML (restaurant persona strings) |
| `greeting.py` | MOVE-TO-YAML (greeting mentions DOBOO) |
| `ordering.py` | MOVE-TO-YAML (dish names in examples) |
| `faq.py` | MOVE-TO-YAML (hours/address references) |
| `reservation.py`, `escalation.py`, `confirmation.py`, `goodbye.py`, `menu_browse.py`, `pre_order_confirm.py` | MOVE-TO-YAML (various DOBOO/dish references) |

**Action (C2)**: Replace hardcoded restaurant name + dish names with `{restaurant_name}` / `{menu_items}` template variables resolved from tenant config at node construction.

---

## server/brain/stt/deepgram_client.py

| Line | Pattern | Content | Classification |
|------|---------|---------|----------------|
| (none — new file) | — | — | — |

*The `deepgram_client.py` audit is clean. All config comes from tenant YAML.*

---

## tools/definitions.py

| Line | Pattern | Content | Classification |
|------|---------|---------|----------------|
| 102 | Bibimbap/Bulgogi | Description example string in parameter definition | EXAMPLE-ONLY (schema description) |

**Action**: Acceptable — this is an API schema description example, not data used in logic.

---

## tools/executor.py

| Line | Pattern | Content | Classification |
|------|---------|---------|----------------|
| 35-37 | DOBOO_LAT/DOBOO_LNG | Hardcoded GPS coordinates | MOVE-TO-YAML |
| 610 | DOBOO | `os.getenv("RESTAURANT_NAME", "DOBOO")` fallback | VERTICAL-GENERIC (env var override exists) |
| 656/741-742 | DOBOO_LAT/DOBOO_LNG | Default coordinates in `_get_parking_info` | MOVE-TO-YAML |
| 716-728 | DOBOO Korean Soulfood / Friedrichstraße | Hardcoded restaurant info dict | MOVE-TO-YAML |
| 829-841 | Bibimbap/Bulgogi/Japchae | Hardcoded fallback menu | MOVE-TO-YAML |
| 909 | DOBOO | Comment: "Canonical DOBOO dish list" | EXAMPLE-ONLY (comment) |

**Action (C2)**: Move coordinates, restaurant info, and default menu to `doboo.yaml`. Executor should load from tenant config at call time.

---

## Summary

| Classification | Count | Action |
|----------------|-------|--------|
| MOVE-TO-YAML | ~25 occurrences | Address in C2 |
| VERTICAL-GENERIC | ~5 occurrences | Annotate with comment; low priority |
| DEAD-CODE | 0 | — |
| EXAMPLE-ONLY | ~20 occurrences | No action needed |

**Critical path for C2**: `tier2_runner.py` system prompt, `executor.py` restaurant/menu defaults, `conversation_state.py` `KNOWN_DISHES`.
