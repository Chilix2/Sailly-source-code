"""
30 targeted validation scenarios for ADK Runner fixes.

After applying Fixes 1-4 to the ADK architecture, these 30 scenarios validate
that the fixes actually work. 5 scenarios per root cause, testing variations
of the same failure pattern to ensure we haven't just patched the one original case.

Root causes:
  RC1: verify_address (Tool not exposed in nodes) - 5 scenarios
  RC2: get_date_info (Relative dates not detected) - 5 scenarios
  RC3: Large-party reservation (>20 people, create_reservation not forced) - 5 scenarios
  RC4: Sie/du (Informal address in ordering node) - 5 scenarios
  RC5: end_call (Goodbye not triggered after order, effective_min too high) - 5 scenarios
  RC6: Instruction/Frustration (Empathy+ node transition) - 5 scenarios
"""

from server.scenarios.tier2_scenarios import AudioScenario, ScenarioTurn

# ══════════════════════════════════════════════════════════════════════════
# RC1: verify_address (5 scenarios)
# ══════════════════════════════════════════════════════════════════════════

FIX_VALIDATION_SCENARIOS = [
    # RC1-01: Address as first utterance (greeting node)
    AudioScenario(
        id="fv-addr-01",
        phase="phase2",
        category="address",
        description="Customer provides delivery address upfront in greeting",
        turns=[
            ScenarioTurn(user_utterance="Guten Tag, ich möchte Bulgogi bestellen und liefern nach Friedrichstraße 45"),
            ScenarioTurn(user_utterance="Ja, das stimmt"),
            ScenarioTurn(user_utterance="Meine Nummer ist 0176 12345678"),
        ],
        expected_tools=["get_menu", "verify_address", "create_order", "send_sms"],
        n_runs=1,
    ),
    # RC1-02: Address mid-order (ordering node)
    AudioScenario(
        id="fv-addr-02",
        phase="phase2",
        category="address",
        description="Address provided during ordering phase",
        turns=[
            ScenarioTurn(user_utterance="Ich möchte Bibimbap bestellen"),
            ScenarioTurn(user_utterance="Liefern Sie auch zu Bornheimer Str. 20?"),
            ScenarioTurn(user_utterance="Prima, meine Nummer ist 0160 98765432"),
        ],
        expected_tools=["get_menu", "verify_address", "create_order", "send_sms"],
        n_runs=1,
    ),
    # RC1-03: Address with abbreviation (Str. instead of Straße)
    AudioScenario(
        id="fv-addr-03",
        phase="phase2",
        category="address",
        description="Street address with abbreviation",
        turns=[
            ScenarioTurn(user_utterance="Bestellen Sie zu Am Markt 3?"),
            ScenarioTurn(user_utterance="Ich hätte gerne Bulgogi"),
            ScenarioTurn(user_utterance="0171 55555555"),
        ],
        expected_tools=["get_menu", "verify_address", "create_order", "send_sms"],
        n_runs=1,
    ),
    # RC1-04: Address in FAQ context
    AudioScenario(
        id="fv-addr-04",
        phase="phase2",
        category="address",
        description="Customer asks about address delivery in FAQ then orders",
        turns=[
            ScenarioTurn(user_utterance="Liefert ihr zu Bonner Platz 10?"),
            ScenarioTurn(user_utterance="Schön, dann Japchae bitte"),
            ScenarioTurn(user_utterance="Telefon: 0170 33333333"),
        ],
        expected_tools=["get_menu", "verify_address", "create_order", "send_sms"],
        n_runs=1,
    ),
    # RC1-05: Multiple address verifications
    AudioScenario(
        id="fv-addr-05",
        phase="phase2",
        category="address",
        description="Address mentioned twice for confirmation",
        turns=[
            ScenarioTurn(user_utterance="Liefert ihr zur Königstraße 99?"),
            ScenarioTurn(user_utterance="Ja, zu Königstraße 99 ist korrekt, ich möchte zwei Mandu"),
            ScenarioTurn(user_utterance="0175 77777777"),
        ],
        expected_tools=["get_menu", "verify_address", "create_order", "send_sms"],
        n_runs=1,
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # RC2: get_date_info (5 scenarios)
    # ══════════════════════════════════════════════════════════════════════════

    # RC2-01: "Übermorgen" (the day after tomorrow)
    AudioScenario(
        id="fv-date-01",
        phase="phase2",
        category="date",
        description="Relative date: übermorgen (day after tomorrow)",
        turns=[
            ScenarioTurn(user_utterance="Ich möchte einen Tisch reservieren für übermorgen"),
            ScenarioTurn(user_utterance="Um 19 Uhr, 2 Personen"),
            ScenarioTurn(user_utterance="Name ist Müller"),
            ScenarioTurn(user_utterance="Ja, bitte buchen"),
        ],
        expected_tools=["check_availability", "get_date_info", "create_reservation"],
        n_runs=1,
    ),
    # RC2-02: "Nächsten Montag" (next Monday)
    AudioScenario(
        id="fv-date-02",
        phase="phase2",
        category="date",
        description="Relative date: nächsten Montag",
        turns=[
            ScenarioTurn(user_utterance="Reservierung für nächsten Montag, bitte"),
            ScenarioTurn(user_utterance="20 Uhr, 4 Personen"),
            ScenarioTurn(user_utterance="Name Schneider"),
            ScenarioTurn(user_utterance="Ja, korrekt"),
        ],
        expected_tools=["check_availability", "get_date_info", "create_reservation"],
        n_runs=1,
    ),
    # RC2-03: "In zwei Wochen" (in two weeks)
    AudioScenario(
        id="fv-date-03",
        phase="phase2",
        category="date",
        description="Relative date: in zwei Wochen",
        turns=[
            ScenarioTurn(user_utterance="Können Sie mich in zwei Wochen einen Tisch reservieren?"),
            ScenarioTurn(user_utterance="19:30 Uhr, 3 Personen"),
            ScenarioTurn(user_utterance="Bitte unter dem Namen Fischer"),
            ScenarioTurn(user_utterance="Stimmt, bitte buchen"),
        ],
        expected_tools=["check_availability", "get_date_info", "create_reservation"],
        n_runs=1,
    ),
    # RC2-04: "Kommenden Freitag" (coming Friday)
    AudioScenario(
        id="fv-date-04",
        phase="phase2",
        category="date",
        description="Relative date: kommenden Freitag",
        turns=[
            ScenarioTurn(user_utterance="Kommenden Freitag, bitte einen Tisch"),
            ScenarioTurn(user_utterance="21 Uhr, 2 Personen"),
            ScenarioTurn(user_utterance="Name Braun"),
            ScenarioTurn(user_utterance="Ja"),
        ],
        expected_tools=["check_availability", "get_date_info", "create_reservation"],
        n_runs=1,
    ),
    # RC2-05: "In drei Tagen" (in three days)
    AudioScenario(
        id="fv-date-05",
        phase="phase2",
        category="date",
        description="Relative date: in drei Tagen",
        turns=[
            ScenarioTurn(user_utterance="Tisch für in drei Tagen"),
            ScenarioTurn(user_utterance="20:00, 2 Personen, Name Wagner"),
            ScenarioTurn(user_utterance="Bitte buchen"),
        ],
        expected_tools=["check_availability", "get_date_info", "create_reservation"],
        n_runs=1,
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # RC3: Large-party reservation (>20 people) - 5 scenarios
    # ══════════════════════════════════════════════════════════════════════════

    # RC3-01: Exactly 21 people
    AudioScenario(
        id="fv-large-01",
        phase="phase2",
        category="reservation",
        description="Large group: 21 people",
        turns=[
            ScenarioTurn(user_utterance="Wir sind 21 Personen und möchten einen Tisch für morgen"),
            ScenarioTurn(user_utterance="Abends um 19 Uhr"),
            ScenarioTurn(user_utterance="Ja, bitte reservieren"),
            ScenarioTurn(user_utterance="Name ist Hoffmann"),
        ],
        expected_tools=["check_availability", "create_reservation"],
        n_runs=1,
    ),
    # RC3-02: 25 people with explicit booking intent
    AudioScenario(
        id="fv-large-02",
        phase="phase2",
        category="reservation",
        description="Large group: 25 people with 'ja buchen'",
        turns=[
            ScenarioTurn(user_utterance="25 Personen wollen einen Tisch für Freitag"),
            ScenarioTurn(user_utterance="20 Uhr, ja buchen!"),
            ScenarioTurn(user_utterance="Name Berg"),
        ],
        expected_tools=["check_availability", "create_reservation"],
        n_runs=1,
    ),
    # RC3-03: 30 people, multi-turn conversation
    AudioScenario(
        id="fv-large-03",
        phase="phase2",
        category="reservation",
        description="Large group: 30 people, extended conversation",
        turns=[
            ScenarioTurn(user_utterance="Guten Tag, wir sind Mitarbeiter eines Büros"),
            ScenarioTurn(user_utterance="30 Personen insgesamt"),
            ScenarioTurn(user_utterance="Für Donnerstag würde passen"),
            ScenarioTurn(user_utterance="19 Uhr"),
            ScenarioTurn(user_utterance="Ja, das ist perfekt"),
            ScenarioTurn(user_utterance="Name ist Richter"),
        ],
        expected_tools=["check_availability", "create_reservation"],
        n_runs=1,
    ),
    # RC3-04: 22 people with timeout trigger (must force commit after 3 turns in reservation)
    AudioScenario(
        id="fv-large-04",
        phase="phase2",
        category="reservation",
        description="Large group: 22 people, conversation extends to timeout trigger",
        turns=[
            ScenarioTurn(user_utterance="Ich bin Organisator einer Veranstaltung"),
            ScenarioTurn(user_utterance="22 Personen total"),
            ScenarioTurn(user_utterance="Nächsten Samstag"),
            ScenarioTurn(user_utterance="20 Uhr, Name Schmidt"),
        ],
        expected_tools=["check_availability", "create_reservation"],
        n_runs=1,
    ),
    # RC3-05: 20+ people with hesitation then confirmation
    AudioScenario(
        id="fv-large-05",
        phase="phase2",
        category="reservation",
        description="Large group: 23 people, hesitation then confirm",
        turns=[
            ScenarioTurn(user_utterance="Wir haben eine Betriebsfeier geplant"),
            ScenarioTurn(user_utterance="Wieviele Personen? Moment... 23 Leute"),
            ScenarioTurn(user_utterance="Freitag nächste Woche, 19 Uhr"),
            ScenarioTurn(user_utterance="Ja, gerne reservieren, Name Krämer"),
        ],
        expected_tools=["check_availability", "create_reservation"],
        n_runs=1,
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # RC4: Sie/du (Formal address in ordering node) - 5 scenarios
    # ══════════════════════════════════════════════════════════════════════════

    # RC4-01: Multi-turn order with special requests (invites informal "du")
    AudioScenario(
        id="fv-sie-01",
        phase="phase2",
        category="ordering",
        description="Multi-turn order: special request (no spice)",
        turns=[
            ScenarioTurn(user_utterance="Ich möchte Kimchi Jjigae, aber bitte ohne Schärfe"),
            ScenarioTurn(user_utterance="Und dazu noch Mandu"),
            ScenarioTurn(user_utterance="0175 99999999"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms"],
        n_runs=1,
    ),
    # RC4-02: Order with correction/clarification
    AudioScenario(
        id="fv-sie-02",
        phase="phase2",
        category="ordering",
        description="Ordering with correction: 'Nein, lieber...'",
        turns=[
            ScenarioTurn(user_utterance="Ich nehme Bulgogi"),
            ScenarioTurn(user_utterance="Nein, lieber zwei Japchae"),
            ScenarioTurn(user_utterance="0160 88888888"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms"],
        n_runs=1,
    ),
    # RC4-03: Order with patience/politeness check (repeated requests)
    AudioScenario(
        id="fv-sie-03",
        phase="phase2",
        category="ordering",
        description="Ordering with repeated attempts/patience",
        turns=[
            ScenarioTurn(user_utterance="Bibimbap bitte"),
            ScenarioTurn(user_utterance="Zum Mitnehmen"),
            ScenarioTurn(user_utterance="Meine Nummer: 0171 11111111"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms"],
        n_runs=1,
    ),
    # RC4-04: Order with customization dialogue
    AudioScenario(
        id="fv-sie-04",
        phase="phase2",
        category="ordering",
        description="Ordering with drink/side requests",
        turns=[
            ScenarioTurn(user_utterance="Ich hätte gerne Tofu Bibimbap und ein Getränk"),
            ScenarioTurn(user_utterance="Was können Sie empfehlen?"),
            ScenarioTurn(user_utterance="Dann Kimchi Jjigae dazu, Tel. 0175 22222222"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms"],
        n_runs=1,
    ),
    # RC4-05: Order after menu browse (formal address maintenance)
    AudioScenario(
        id="fv-sie-05",
        phase="phase2",
        category="ordering",
        description="Browse menu then order, maintain formality",
        turns=[
            ScenarioTurn(user_utterance="Was haben Sie vegetarisches?"),
            ScenarioTurn(user_utterance="Gut, dann Mandu"),
            ScenarioTurn(user_utterance="0170 55555555"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms"],
        n_runs=1,
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # RC5: end_call (Goodbye after order, effective_min=2) - 5 scenarios
    # ══════════════════════════════════════════════════════════════════════════

    # RC5-01: Short order + goodbye (3 turns total)
    AudioScenario(
        id="fv-end-01",
        phase="phase2",
        category="ordering",
        description="Short order: item + number + goodbye",
        turns=[
            ScenarioTurn(user_utterance="Bulgogi bitte"),
            ScenarioTurn(user_utterance="0175 11111111"),
            ScenarioTurn(user_utterance="Auf Wiedersehen"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms", "end_call"],
        n_runs=1,
    ),
    # RC5-02: Order with "Danke, Tschüss"
    AudioScenario(
        id="fv-end-02",
        phase="phase2",
        category="ordering",
        description="Goodbye with thanks: 'Danke, Tschüss'",
        turns=[
            ScenarioTurn(user_utterance="Japchae, bitte"),
            ScenarioTurn(user_utterance="0160 22222222"),
            ScenarioTurn(user_utterance="Danke, Tschüss"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms", "end_call"],
        n_runs=1,
    ),
    # RC5-03: Confirmed order + "Bis dann"
    AudioScenario(
        id="fv-end-03",
        phase="phase2",
        category="ordering",
        description="Order confirmation + 'Bis dann' goodbye",
        turns=[
            ScenarioTurn(user_utterance="Mandu"),
            ScenarioTurn(user_utterance="0171 33333333"),
            ScenarioTurn(user_utterance="Bis dann"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms", "end_call"],
        n_runs=1,
    ),
    # RC5-04: Quick order + "Vielen Dank"
    AudioScenario(
        id="fv-end-04",
        phase="phase2",
        category="ordering",
        description="Quick order + 'Vielen Dank' before goodbye",
        turns=[
            ScenarioTurn(user_utterance="Tofu Jjigae"),
            ScenarioTurn(user_utterance="0176 44444444"),
            ScenarioTurn(user_utterance="Vielen Dank, auf Wiedersehen"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms", "end_call"],
        n_runs=1,
    ),
    # RC5-05: Natural goodbye after order
    AudioScenario(
        id="fv-end-05",
        phase="phase2",
        category="ordering",
        description="Natural flow: order → goodbye",
        turns=[
            ScenarioTurn(user_utterance="Zwei Bibimbap bitte"),
            ScenarioTurn(user_utterance="0170 55555555"),
            ScenarioTurn(user_utterance="Alles klar, danke"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms", "end_call"],
        n_runs=1,
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # RC6: Instruction/Frustration (Empathy + correct node transition) - 5 scenarios
    # ══════════════════════════════════════════════════════════════════════════

    # RC6-01: Frustrated opening + order completion
    AudioScenario(
        id="fv-frust-01",
        phase="phase2",
        category="frustration",
        description="Frustration opener: 'Das ist unakzeptabel' → order",
        turns=[
            ScenarioTurn(user_utterance="Das ist unakzeptabel, warum antwortet keiner?"),
            ScenarioTurn(user_utterance="Okay, ich möchte Bulgogi bestellen"),
            ScenarioTurn(user_utterance="0175 66666666"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms"],
        n_runs=1,
    ),
    # RC6-02: Impatience complaint + resolution
    AudioScenario(
        id="fv-frust-02",
        phase="phase2",
        category="frustration",
        description="Impatience: 'Warum dauert das so lange?' → order",
        turns=[
            ScenarioTurn(user_utterance="Warum dauert das so lange, ich hätte gerne bestellen"),
            ScenarioTurn(user_utterance="Japchae"),
            ScenarioTurn(user_utterance="0160 77777777"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms"],
        n_runs=1,
    ),
    # RC6-03: Technical complaint + order
    AudioScenario(
        id="fv-frust-03",
        phase="phase2",
        category="frustration",
        description="Technical frustration: 'App kaputt' but then via phone",
        turns=[
            ScenarioTurn(user_utterance="Eure App ist kaputt, ich rufe lieber an"),
            ScenarioTurn(user_utterance="Mandu, bitte"),
            ScenarioTurn(user_utterance="0171 88888888"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms"],
        n_runs=1,
    ),
    # RC6-04: Skeptical customer → convinced → order
    AudioScenario(
        id="fv-frust-04",
        phase="phase2",
        category="frustration",
        description="Skepticism: 'Ich bin nicht sicher...' → convinced",
        turns=[
            ScenarioTurn(user_utterance="Ich bin nicht sicher, ob die Lieferung funktioniert"),
            ScenarioTurn(user_utterance="Okay, ich vertraue euch, Tofu Jjigae"),
            ScenarioTurn(user_utterance="0170 99999999"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms"],
        n_runs=1,
    ),
    # RC6-05: Demanding customer → empathy handling
    AudioScenario(
        id="fv-frust-05",
        phase="phase2",
        category="frustration",
        description="Demanding tone: 'Ich brauche das schnell' → calm order",
        turns=[
            ScenarioTurn(user_utterance="Ich brauche das schnell, kann ich Bibimbap in 20 Minuten haben?"),
            ScenarioTurn(user_utterance="Alles klar, bestellt"),
            ScenarioTurn(user_utterance="0176 00000000"),
        ],
        expected_tools=["get_menu", "create_order", "send_sms"],
        n_runs=1,
    ),
]
