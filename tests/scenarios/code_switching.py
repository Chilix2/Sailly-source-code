"""Code-switching (DE ⇄ EN/TR) regression scenarios.

These scenarios are consumed by the validation runner when a tenant is
configured with ``stt_language: multi``. Each entry is a list of caller
utterances that mix German with a second language on the same turn — a
common pattern for real German restaurant callers (e.g. Turkish or English
native speakers living in Bonn/Köln).

The scenarios are language-agnostic fixtures — the runner is responsible
for stitching them into a full dialog (greeting, order flow, etc.). We do
not assert on bot output here; WER (word error rate) is scored externally.
"""
from __future__ import annotations

CODE_SWITCHING_SCENARIOS = [
    {
        "id": "cs-de-en-order",
        "description": "English native speaker ordering in mixed German/English",
        "tenant_stt_language": "multi",
        "turns": [
            "Hi, guten Abend — I'd like to order some Bibimbap for delivery please.",
            "Yes, two please. Also one Bulgogi — medium spicy ist ok.",
            "Delivery zu Hauptstraße fünf, 53113 Bonn.",
            "My phone number ist null eins seven one — 1234567.",
            "Cash please, danke.",
        ],
    },
    {
        "id": "cs-de-tr-faq",
        "description": "Turkish/German code-switch asking about allergens",
        "tenant_stt_language": "multi",
        "turns": [
            "Merhaba, guten Tag. Ich wollte fragen — ist das Bibimbap glutenfrei?",
            "Tamam, dann nehme ich das. Ein Bibimbap bitte.",
            "Takeaway, lütfen.",
        ],
    },
    {
        "id": "cs-de-en-reservation",
        "description": "Mixed DE/EN reservation request on Friday night",
        "tenant_stt_language": "multi",
        "turns": [
            "Good evening, wir möchten einen Tisch reservieren für Freitag at seven pm.",
            "Four people. Für vier Personen, ja.",
            "Name is Müller — M-U-E-double-L-E-R.",
            "Telefonnummer zero one seven zero — one two three four.",
        ],
    },
]


if __name__ == "__main__":
    print(f"Loaded {len(CODE_SWITCHING_SCENARIOS)} code-switching scenarios")
    for s in CODE_SWITCHING_SCENARIOS:
        print(f"  {s['id']}: {s['description']} ({len(s['turns'])} turns)")
