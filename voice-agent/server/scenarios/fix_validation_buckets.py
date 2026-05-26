"""
Targeted scenarios for Fix Validation Loop.

12 buckets × 30 scenarios = 360 targeted scenarios (3 steps × 10 per bucket).

Sourcing strategy (in priority order):
1. Failing scenario IDs from the Demo Training Loop (ab_results.json)
2. Phase 1-4 scenarios filtered by expected_tools
3. Hand-crafted edge cases for buckets with insufficient coverage
   (ai_greeting has only 6 in phase files; get_weather has 0)
"""

from __future__ import annotations

from server.scenarios.base import AudioScenario, ScenarioTurn

# ---------------------------------------------------------------------------
# Phase scenario pools — filtered by expected_tools
# ---------------------------------------------------------------------------
from server.scenarios.phase1_scenarios import PHASE1_SCENARIOS
from server.scenarios.phase2_scenarios import PHASE2_SCENARIOS
from server.scenarios.phase3_scenarios import PHASE3_SCENARIOS
from server.scenarios.phase4_scenarios import PHASE4_SCENARIOS

_ALL = PHASE1_SCENARIOS + PHASE2_SCENARIOS + PHASE3_SCENARIOS + PHASE4_SCENARIOS
_BY_ID = {s.id: s for s in _ALL}


def _pick(ids: list[str], tool: str | None = None, n: int = 30,
          exclude: set | None = None) -> list:
    used = set(exclude or [])
    result = []
    for sid in ids:
        if sid in _BY_ID and sid not in used:
            result.append(_BY_ID[sid])
            used.add(sid)
    if tool and len(result) < n:
        for s in _ALL:
            if s.id in used:
                continue
            if tool in (s.expected_tools or []):
                result.append(s)
                used.add(s.id)
                if len(result) >= n:
                    break
    if len(result) < n:
        for s in _ALL:
            if s.id in used:
                continue
            result.append(s)
            used.add(s.id)
            if len(result) >= n:
                break
    return result[:n]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bucket 1 — ai_greeting  (Tier 1, 100% required, 6 failures in demo loop)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_GREET_PHASE_IDS = [
    "p1-greeting-01", "p1-location-01", "p1-location-02",
    "p1-parking-01", "p1-greeting-02",
]

_GREET_HANDCRAFTED = [
    AudioScenario(
        id="fix-greet-03", description="Greet 03", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Ja hallo?")],
        expected_tools=["ai_greeting"],
    ),
    AudioScenario(
        id="fix-greet-04", description="Greet 04", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Guten Tag.")],
        expected_tools=["ai_greeting"],
    ),
    AudioScenario(
        id="fix-greet-05", description="Greet 05", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Hallo, ist dort DOBOO?")],
        expected_tools=["ai_greeting"],
    ),
    AudioScenario(
        id="fix-greet-06", description="Greet 06", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="...")],
        expected_tools=["ai_greeting"],
    ),
    AudioScenario(
        id="fix-greet-07", description="Greet 07", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Ich würde gerne bestellen")],
        expected_tools=["ai_greeting", "get_menu"],
    ),
    AudioScenario(
        id="fix-greet-08", description="Greet 08", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Ich möchte einen Tisch reservieren")],
        expected_tools=["ai_greeting", "check_availability"],
    ),
    AudioScenario(
        id="fix-greet-09", description="Greet 09", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Hallo, ich bin Müller")],
        expected_tools=["ai_greeting"],
    ),
    AudioScenario(
        id="fix-greet-10", description="Greet 10", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Hallo wer seid ihr?")],
        expected_tools=["ai_greeting"],
    ),
    AudioScenario(
        id="fix-greet-11", description="Greet 11", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Äh, hallo?")],
        expected_tools=["ai_greeting"],
    ),
    AudioScenario(
        id="fix-greet-12", description="Greet 12", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Guten Abend")],
        expected_tools=["ai_greeting"],
    ),
    AudioScenario(
        id="fix-greet-13", description="Greet 13", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Hallo, ich hätte eine Frage")],
        expected_tools=["ai_greeting"],
    ),
    AudioScenario(
        id="fix-greet-14", description="Greet 14", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Tag! Kurze Frage zu den Öffnungszeiten")],
        expected_tools=["ai_greeting", "get_date_info"],
    ),
    AudioScenario(
        id="fix-greet-15", description="Greet 15", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Halloooo")],
        expected_tools=["ai_greeting"],
    ),
    AudioScenario(
        id="fix-greet-16", description="Greet 16", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Guten Morgen, kann ich was bestellen?")],
        expected_tools=["ai_greeting", "get_menu"],
    ),
    AudioScenario(
        id="fix-greet-17", description="Greet 17", phase="fix", category="greeting",
        turns=[ScenarioTurn(user_utterance="Spreche ich mit dem Restaurant?")],
        expected_tools=["ai_greeting"],
    ),
]

AI_GREETING_SCENARIOS = (_pick(_GREET_PHASE_IDS, tool="ai_greeting", n=15) + _GREET_HANDCRAFTED)[:30]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bucket 2 — verify_address  (Tier 1, 100% required, 41 failures in demo loop)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_ADDR_DEMO_IDS = [
    "p2-order-04", "p2-delivery-13", "p2-delivery-19", "p2-order-21",
    "p2-delivery-26", "p2-order-29", "p2-delivery-30", "p2-delivery-34",
]

# Key edge cases: address given AFTER order commit (previously broken)
_ADDR_EDGE = [
    AudioScenario(
        id="fix-addr-01", description="Addr 01", phase="fix", category="ordering",
        turns=[
            ScenarioTurn(user_utterance="Bibimbap bitte"),
            ScenarioTurn(user_utterance="0151 12345678"),
            ScenarioTurn(user_utterance="Ja"),
            ScenarioTurn(user_utterance="Lieferung bitte, Bornheimer Straße 10"),
        ],
        expected_tools=["ai_greeting", "get_menu", "create_order", "send_sms", "verify_address"],
    ),
    AudioScenario(
        id="fix-addr-02", description="Addr 02", phase="fix", category="ordering",
        turns=[
            ScenarioTurn(user_utterance="Bulgogi zum Liefern"),
            ScenarioTurn(user_utterance="0171 9876543"),
            ScenarioTurn(user_utterance="Ach, meine Adresse: Hauptstraße 5, 53111 Bonn"),
        ],
        expected_tools=["ai_greeting", "get_menu", "create_order", "send_sms", "verify_address"],
    ),
    AudioScenario(
        id="fix-addr-03", description="Addr 03", phase="fix", category="ordering",
        turns=[
            ScenarioTurn(user_utterance="Ich möchte Tteokbokki bestellen"),
            ScenarioTurn(user_utterance="Meine Nummer ist 0160 55566677"),
            ScenarioTurn(user_utterance="Tschüss"),
            ScenarioTurn(user_utterance="Ach warte, Lieferung an Riesstraße 3"),
        ],
        expected_tools=["ai_greeting", "get_menu", "create_order", "send_sms", "verify_address"],
    ),
    AudioScenario(
        id="fix-addr-04", description="Addr 04", phase="fix", category="ordering",
        turns=[
            ScenarioTurn(user_utterance="Ich wohne in der Poststraße 7 und möchte Japchae"),
            ScenarioTurn(user_utterance="0176 44455566"),
        ],
        expected_tools=["ai_greeting", "get_menu", "verify_address", "create_order", "send_sms"],
    ),
    AudioScenario(
        id="fix-addr-05", description="Addr 05", phase="fix", category="ordering",
        turns=[
            ScenarioTurn(user_utterance="Lieferung an Kaiserplatz 10 bitte, Mandu"),
            ScenarioTurn(user_utterance="0162 9988776"),
        ],
        expected_tools=["ai_greeting", "get_menu", "verify_address", "create_order", "send_sms"],
    ),
    AudioScenario(
        id="fix-addr-06", description="Addr 06", phase="fix", category="ordering",
        turns=[
            ScenarioTurn(user_utterance="Haben Sie auch die Tofu Bibimbap?"),
            ScenarioTurn(user_utterance="Dann die bitte. Telefon: 0153 11223344"),
            ScenarioTurn(user_utterance="Ja stimmt so. PLZ 53113"),
        ],
        expected_tools=["ai_greeting", "get_menu", "verify_address", "create_order", "send_sms"],
    ),
]

VERIFY_ADDRESS_SCENARIOS = (_pick(_ADDR_DEMO_IDS, tool="verify_address", n=24) + _ADDR_EDGE)[:30]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bucket 3 — create_order  (Tier 1, 100% required, 4 failures in demo loop)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_ORDER_DEMO_IDS = [
    "p3-impatient-11", "p3-sleepy-12", "p3-chaos-31", "p3-sleepy-39",
    "p3-angry-34", "p3-angry-01", "p3-chaos-02", "p3-accent-20",
]

CREATE_ORDER_SCENARIOS = _pick(_ORDER_DEMO_IDS, tool="create_order", n=30)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bucket 4 — send_sms  (Tier 1, 100% required)
# Validates that send_sms always follows create_order in the same turn.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_sms_scens = [
    s for s in _ALL
    if "send_sms" in (s.expected_tools or []) and "create_order" in (s.expected_tools or [])
]

SEND_SMS_SCENARIOS = _sms_scens[:30]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bucket 5 — create_reservation + check_availability
#            (Tier 1, 100% required, 31 failures combined in demo loop)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_RES_DEMO_IDS = [
    "p2-reservation-29", "p2-reservation-21", "p2-reservation-10",
    "p3-chaos-01", "p3-chaos-12", "p3-chaos-21", "p3-accent-25", "p3-sleepy-29",
]

_RES_EDGE = [
    AudioScenario(
        id="fix-res-01", description="Res 01", phase="fix", category="reservation",
        turns=[
            ScenarioTurn(user_utterance="Tisch für 4, Freitag 19 Uhr"),
        ],
        expected_tools=["ai_greeting", "get_date_info", "check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="fix-res-02", description="Res 02", phase="fix", category="reservation",
        turns=[
            ScenarioTurn(user_utterance="Reservierung bitte"),
            ScenarioTurn(user_utterance="Samstag, 20 Uhr, zu zweit"),
            ScenarioTurn(user_utterance="Müller"),
        ],
        expected_tools=["ai_greeting", "get_date_info", "check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="fix-res-03", description="Res 03", phase="fix", category="reservation",
        turns=[
            ScenarioTurn(user_utterance="Ich möchte für morgen Abend reservieren, zu dritt um halb acht"),
        ],
        expected_tools=["ai_greeting", "get_date_info", "check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="fix-res-04", description="Res 04", phase="fix", category="reservation",
        turns=[
            ScenarioTurn(user_utterance="Haben Sie Samstag Abend noch Platz für 6 Personen?"),
            ScenarioTurn(user_utterance="Um 19 Uhr"),
            ScenarioTurn(user_utterance="Name: Schmidt"),
        ],
        expected_tools=["ai_greeting", "get_date_info", "check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="fix-res-05", description="Res 05", phase="fix", category="reservation",
        # Compound: reservation + address
        turns=[
            ScenarioTurn(user_utterance="Tisch für 3 morgen 18 Uhr"),
            ScenarioTurn(user_utterance="Name Schmidt. Können Sie auch liefern an Hauptstr. 5?"),
        ],
        expected_tools=["ai_greeting", "get_date_info", "check_availability", "create_reservation", "verify_address"],
    ),
]

CREATE_RESERVATION_SCENARIOS = (_pick(_RES_DEMO_IDS, tool="create_reservation", n=25) + _RES_EDGE)[:30]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bucket 6 — get_date_info  (Tier 1, 100% required, 13 failures in demo loop)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_DATE_DEMO_IDS = [
    "p1-opening-hours-01", "p1-opening-hours-02", "p1-opening-hours-03",
    "p1-info-03", "p1-info-08", "p1-info-15", "p2-delivery-23", "p2-delivery-39",
]

_DATE_EDGE = [
    AudioScenario(
        id="fix-date-01", description="Date 01", phase="fix", category="ordering",
        turns=[
            ScenarioTurn(user_utterance="Bibimbap für übermorgen bestellen"),
            ScenarioTurn(user_utterance="0151 12345678"),
        ],
        expected_tools=["ai_greeting", "get_menu", "get_date_info", "create_order", "send_sms"],
    ),
    AudioScenario(
        id="fix-date-02", description="Date 02", phase="fix", category="reservation",
        turns=[
            ScenarioTurn(user_utterance="Tisch für nächsten Samstag bitte"),
            ScenarioTurn(user_utterance="Zu viert, um acht"),
        ],
        expected_tools=["ai_greeting", "get_date_info", "check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="fix-date-03", description="Date 03", phase="fix", category="reservation",
        turns=[
            ScenarioTurn(user_utterance="Haben Sie am Wochenende noch Platz?"),
            ScenarioTurn(user_utterance="Sonntag, zu zweit, 19 Uhr"),
        ],
        expected_tools=["ai_greeting", "get_date_info", "check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="fix-date-04", description="Date 04", phase="fix", category="faq",
        turns=[
            ScenarioTurn(user_utterance="Seid ihr nächsten Montag geöffnet?"),
        ],
        expected_tools=["ai_greeting", "get_date_info"],
    ),
    AudioScenario(
        id="fix-date-05", description="Date 05", phase="fix", category="reservation",
        turns=[
            ScenarioTurn(user_utterance="In einer Woche möchte ich reservieren"),
            ScenarioTurn(user_utterance="Donnerstag, 3 Personen, 18:30"),
        ],
        expected_tools=["ai_greeting", "get_date_info", "check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="fix-date-06", description="Date 06", phase="fix", category="reservation",
        turns=[
            ScenarioTurn(user_utterance="Kommenden Freitag, Tisch für 5"),
            ScenarioTurn(user_utterance="Um 20 Uhr"),
        ],
        expected_tools=["ai_greeting", "get_date_info", "check_availability", "create_reservation"],
    ),
]

GET_DATE_INFO_SCENARIOS = (_pick(_DATE_DEMO_IDS, tool="get_date_info", n=24) + _DATE_EDGE)[:30]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bucket 7 — check_availability  (Tier 1, 100% required, 5 failures in demo loop)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_AVAIL_DEMO_IDS = [
    "p2-reservation-36", "p2-reservation-27", "p2-reservation-93",
    "p3-chaos-33", "p3-angry-34", "p3-accent-28", "p3-order-availability-01",
]

CHECK_AVAILABILITY_SCENARIOS = _pick(_AVAIL_DEMO_IDS, tool="check_availability", n=30)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bucket 8 — get_weather  (Tier 1, 100% required — no existing failures,
#             but forced commit block was missing; all scenarios hand-crafted)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GET_WEATHER_SCENARIOS = [
    AudioScenario(
        id="fix-weather-01", description="Weather 01", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Wie ist das Wetter gerade?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-02", description="Weather 02", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Kann man bei euch draußen sitzen?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-03", description="Weather 03", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Haben Sie eine Terrasse?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-04", description="Weather 04", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Regnet es gerade in Bonn?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-05", description="Weather 05", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Ist es warm genug für draußen heute?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-06", description="Weather 06", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Haben Sie einen Biergarten?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-07", description="Weather 07", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Wie ist das Wetter heute Abend, lohnt sich ein Außentisch?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-08", description="Weather 08", phase="fix", category="reservation",
        turns=[
            ScenarioTurn(user_utterance="Ich möchte reservieren, aber nur wenn das Wetter gut ist"),
            ScenarioTurn(user_utterance="Samstag um 19 Uhr, zu zweit"),
        ],
        expected_tools=["ai_greeting", "get_weather", "get_date_info", "check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="fix-weather-09", description="Weather 09", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Ist der Außenbereich offen heute?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-10", description="Weather 10", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Sonnig oder regnerisch heute bei euch?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-11", description="Weather 11", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Ist es draußen kalt?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-12", description="Weather 12", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Kann ich auf der Terrasse sitzen trotz Regen?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-13", description="Weather 13", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Wie warm ist es draußen gerade?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-14", description="Weather 14", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Schneit es bei euch?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-15", description="Weather 15", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Gibt es Plätze im Freien?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-16", description="Weather 16", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Wie ist das Wetter heute Mittag?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-17", description="Weather 17", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Wir wollen gerne draußen essen")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-18", description="Weather 18", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Ist der Außensitzbereich geöffnet?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-19", description="Weather 19", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Können wir draußen sitzen, es ist schön sonnig heute")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-20", description="Weather 20", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Wetter-Check bitte für heute Abend, wir kommen zu fünft")],
        expected_tools=["ai_greeting", "get_weather", "get_date_info", "check_availability"],
    ),
    AudioScenario(
        id="fix-weather-21", description="Weather 21", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Brauche ich einen Regenschirm wenn ich zu euch komme?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-22", description="Weather 22", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Wie sind die Temperaturen heute in Bonn?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-23", description="Weather 23", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Stürmt es draußen? Wir wollten eigentlich auf die Terrasse.")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-24", description="Weather 24", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Wird es heute Abend noch regnen?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-25", description="Weather 25", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Wie warm wird es morgen? Wir planen draußen zu essen.")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-26", description="Weather 26", phase="fix", category="reservation",
        turns=[
            ScenarioTurn(user_utterance="Wetter für Freitag bitte, wir wollen draußen reservieren"),
            ScenarioTurn(user_utterance="Zu viert, 19 Uhr"),
        ],
        expected_tools=["ai_greeting", "get_weather", "get_date_info", "check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="fix-weather-27", description="Weather 27", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Gibt es bei euch eine überdachte Terrasse?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-28", description="Weather 28", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Ist es trocken genug für den Außenbereich?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-29", description="Weather 29", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Hallo, was sagt das Wetter für heute?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
    AudioScenario(
        id="fix-weather-30", description="Weather 30", phase="fix", category="faq",
        turns=[ScenarioTurn(user_utterance="Ist Biergarten-Wetter heute?")],
        expected_tools=["ai_greeting", "get_weather"],
    ),
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bucket 9 — task_score  (Tier 2, 60% required, 38 failures in demo loop)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_TASK_DEMO_IDS = [
    "p1-greeting-01", "p1-opening-hours-01", "p1-opening-hours-02", "p1-location-01",
    "p1-opening-hours-03", "p1-location-02", "p1-parking-01",
]
_task_base = _pick(_TASK_DEMO_IDS, n=10)
_task_extra_p3 = [s for s in PHASE3_SCENARIOS if s.id not in {x.id for x in _task_base}][:12]
_task_extra_p2 = [s for s in PHASE2_SCENARIOS if s.id not in {x.id for x in _task_base} and s.id not in {x.id for x in _task_extra_p3}][:8]

TASK_SCORE_SCENARIOS = (_task_base + _task_extra_p3 + _task_extra_p2)[:30]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bucket 10 — instruction_score  (Tier 2, 60% required, 6 failures in demo loop)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_INSTR_DEMO_IDS = [
    "p2-delivery-03", "p3-chaos-31", "p3-chaos-33", "p3-chaos-02",
    "p3-chaos-11", "p4-chaos-14", "p4-elderly-17",
]
_instr_base = _pick(_INSTR_DEMO_IDS, n=10)
_instr_extra_p4 = [s for s in PHASE4_SCENARIOS if s.id not in {x.id for x in _instr_base}][:12]
_instr_extra_p3 = [s for s in PHASE3_SCENARIOS if s.id not in {x.id for x in _instr_base} and s.id not in {x.id for x in _instr_extra_p4}][:8]

INSTRUCTION_SCORE_SCENARIOS = (_instr_base + _instr_extra_p4 + _instr_extra_p3)[:30]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bucket 11 — timeout  (Tier 2, 60% required, 8 failures in demo loop)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_TIMEOUT_DEMO_IDS = [
    "p1-info-06", "p1-transfer-16", "p2-information-37", "p3-chaos-31",
    "p3-chaos-30", "p3-order-change-01", "p3-angry-12", "p3-angry-22",
]
_timeout_base = _pick(_TIMEOUT_DEMO_IDS, n=10)
_timeout_extra_p3 = [
    s for s in PHASE3_SCENARIOS
    if s.id not in {x.id for x in _timeout_base} and ("angry" in s.id or "chaos" in s.id)
][:12]
_timeout_extra_p4 = [
    s for s in PHASE4_SCENARIOS
    if s.id not in {x.id for x in _timeout_base}
    and s.id not in {x.id for x in _timeout_extra_p3}
][:8]

TIMEOUT_SCENARIOS = (_timeout_base + _timeout_extra_p3 + _timeout_extra_p4)[:30]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bucket 12 — conversation_loop  (Tier 2, 60% required, 3 failures in demo loop)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_LOOP_DEMO_IDS = ["p4-chaos-14", "p4-hard_to_hear-13", "p4-angry-16"]
_loop_base = _pick(_LOOP_DEMO_IDS, n=5)
_loop_extra_p4 = [s for s in PHASE4_SCENARIOS if s.id not in {x.id for x in _loop_base}][:15]
_loop_extra_p3 = [
    s for s in PHASE3_SCENARIOS
    if s.id not in {x.id for x in _loop_base}
    and s.id not in {x.id for x in _loop_extra_p4}
    and ("chaos" in s.id or "angry" in s.id or "impatient" in s.id)
][:10]

CONVERSATION_LOOP_SCENARIOS = (_loop_base + _loop_extra_p4 + _loop_extra_p3)[:30]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Summary
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALL_FIX_BUCKETS = {
    "ai_greeting": AI_GREETING_SCENARIOS,
    "verify_address": VERIFY_ADDRESS_SCENARIOS,
    "create_order": CREATE_ORDER_SCENARIOS,
    "send_sms": SEND_SMS_SCENARIOS,
    "create_reservation": CREATE_RESERVATION_SCENARIOS,
    "get_date_info": GET_DATE_INFO_SCENARIOS,
    "check_availability": CHECK_AVAILABILITY_SCENARIOS,
    "get_weather": GET_WEATHER_SCENARIOS,
    "task_score": TASK_SCORE_SCENARIOS,
    "instruction_score": INSTRUCTION_SCORE_SCENARIOS,
    "timeout": TIMEOUT_SCENARIOS,
    "conversation_loop": CONVERSATION_LOOP_SCENARIOS,
}

if __name__ == "__main__":
    total = sum(len(v) for v in ALL_FIX_BUCKETS.values())
    print(f"Total fix validation scenarios: {total}")
    for name, scens in ALL_FIX_BUCKETS.items():
        print(f"  {name:30s}: {len(scens):3d} scenarios")
