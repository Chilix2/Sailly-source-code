"""
Multi-Intent Scenarios — Tests for handling 2-3 simultaneous customer intents.

These scenarios validate the dual-intent routing (select_node), intent stack
(mid-conversation pivots), and the LLM multi-intent prompt instruction added
to every node in conversation_nodes.py.

Target behaviours:
  • Bot addresses ALL mentioned intents, not just the first one
  • Correct tools are called for each intent
  • Node routing follows priority: order > reservation > faq

Scenario IDs: multi-01 through multi-10
"""

from server.scenarios.base import AudioScenario, ScenarioTurn

MULTI_INTENT_SCENARIOS = [

# ── multi-01: Order + Ask about opening hours ────────────────────────────────
AudioScenario(
    id="multi-01",
    phase="multi",
    category="multi_intent",
    description="Kunde möchte Bibimbap bestellen UND fragt nach Öffnungszeiten in einer Aussage",
    persona="neutral",
    noise_variant="clean",
    turns=[
        ScenarioTurn(
            user_utterance=(
                "Ich möchte Bibimbap bestellen, und können Sie mir auch sagen, "
                "wann Sie morgen geöffnet haben?"
            )
        ),
        ScenarioTurn(user_utterance="Lieferung bitte, meine Adresse ist Bonner Str. 5."),
        ScenarioTurn(user_utterance="Meine Nummer ist 0151 12345678."),
        ScenarioTurn(user_utterance="Danke, das war's."),
        ScenarioTurn(user_utterance="Auf Wiedersehen."),
    ],
    expected_tools=["get_menu", "get_date_info", "verify_address", "create_order", "send_sms"],
),

# ── multi-02: FAQ (hours + price) + ask about outdoor seating ────────────────
AudioScenario(
    id="multi-02",
    phase="multi",
    category="multi_intent",
    description="Dreifach-FAQ: Öffnungszeiten, Bulgogi-Preis und ob man draußen sitzen kann",
    persona="neutral",
    noise_variant="clean",
    turns=[
        ScenarioTurn(
            user_utterance=(
                "Wann habt ihr geöffnet, was kostet das Bulgogi, "
                "und kann man bei euch draußen sitzen?"
            )
        ),
        ScenarioTurn(user_utterance="Gut, und habt ihr heute Mittag noch Plätze?"),
        ScenarioTurn(user_utterance="Danke, ich komme dann vorbei."),
        ScenarioTurn(user_utterance="Tschüss."),
    ],
    expected_tools=["get_date_info", "get_menu", "faq"],
),

# ── multi-03: Order + FAQ (parking) ──────────────────────────────────────────
AudioScenario(
    id="multi-03",
    phase="multi",
    category="multi_intent",
    description="Bestellung + Parkplatz-Frage in einem Atemzug",
    persona="neutral",
    noise_variant="clean",
    turns=[
        ScenarioTurn(
            user_utterance=(
                "Ich will bestellen, aber zuerst: habt ihr Parkplätze in der Nähe?"
            )
        ),
        ScenarioTurn(user_utterance="Okay, dann bestelle ich Bulgogi zur Abholung."),
        ScenarioTurn(user_utterance="Meine Nummer ist 0176 99887766."),
        ScenarioTurn(user_utterance="Super, danke."),
        ScenarioTurn(user_utterance="Auf Wiederhören."),
    ],
    expected_tools=["faq", "get_menu", "create_order", "send_sms"],
),

# ── multi-04: Order + Reservation simultaneously ─────────────────────────────
AudioScenario(
    id="multi-04",
    phase="multi",
    category="multi_intent",
    description="Gleichzeitig: Bibimbap bestellen UND Tisch für morgen Abend reservieren",
    persona="neutral",
    noise_variant="clean",
    turns=[
        ScenarioTurn(
            user_utterance=(
                "Ich möchte Bibimbap zur Lieferung bestellen und gleichzeitig "
                "einen Tisch für morgen Abend um 19 Uhr für 2 Personen reservieren."
            )
        ),
        ScenarioTurn(user_utterance="Meine Adresse ist Friedrich-Ebert-Allee 10, Bonn."),
        ScenarioTurn(user_utterance="Meine Nummer ist 0151 55443322."),
        ScenarioTurn(user_utterance="Für die Reservierung, der Name ist Müller."),
        ScenarioTurn(user_utterance="Perfekt, vielen Dank!"),
    ],
    expected_tools=["get_menu", "verify_address", "create_order", "send_sms",
                    "check_availability", "create_reservation"],
),

# ── multi-05: Order + weather question ───────────────────────────────────────
AudioScenario(
    id="multi-05",
    phase="multi",
    category="multi_intent",
    description="Bestellung + Wetterfrage für Terrassenplanung",
    persona="neutral",
    noise_variant="clean",
    turns=[
        ScenarioTurn(
            user_utterance=(
                "Ich hätte gerne Tteokbokki zur Abholung. "
                "Und wie ist eigentlich das Wetter heute Nachmittag, ich überlege ob ich auf die Terrasse kann."
            )
        ),
        ScenarioTurn(user_utterance="Meine Nummer ist 0160 44556677."),
        ScenarioTurn(user_utterance="Danke, bis dann."),
        ScenarioTurn(user_utterance="Tschüss."),
    ],
    expected_tools=["get_menu", "get_weather", "create_order", "send_sms"],
),

# ── multi-06: Reservation + menu inquiry ─────────────────────────────────────
AudioScenario(
    id="multi-06",
    phase="multi",
    category="multi_intent",
    description="Reservierung + Speisekarte in einer Anfrage",
    persona="neutral",
    noise_variant="clean",
    turns=[
        ScenarioTurn(
            user_utterance=(
                "Ich möchte für Samstag um 20 Uhr für 4 Personen reservieren "
                "und würde auch gerne wissen, was es bei euch zu essen gibt."
            )
        ),
        ScenarioTurn(user_utterance="Mein Name ist Schmidt."),
        ScenarioTurn(user_utterance="Gibt es auch vegetarische Optionen?"),
        ScenarioTurn(user_utterance="Sehr gut, danke."),
        ScenarioTurn(user_utterance="Auf Wiedersehen."),
    ],
    expected_tools=["check_availability", "create_reservation", "get_menu"],
),

# ── multi-07: Mid-order pivot to FAQ ─────────────────────────────────────────
AudioScenario(
    id="multi-07",
    phase="multi",
    category="multi_intent",
    description="Mitte der Bestellung: Kunde fragt zwischendurch nach Lieferzeit",
    persona="neutral",
    noise_variant="clean",
    turns=[
        ScenarioTurn(user_utterance="Ich möchte Japchae bestellen."),
        ScenarioTurn(
            user_utterance=(
                "Lieferung bitte — und noch kurz: wie lange dauert die Lieferung bei euch normalerweise?"
            )
        ),
        ScenarioTurn(user_utterance="Okay, meine Adresse ist Poppelsdorfer Allee 3."),
        ScenarioTurn(user_utterance="0172 33445566."),
        ScenarioTurn(user_utterance="Super, vielen Dank."),
    ],
    expected_tools=["get_menu", "faq", "verify_address", "create_order", "send_sms"],
),

# ── multi-08: Order + ask about allergens ────────────────────────────────────
AudioScenario(
    id="multi-08",
    phase="multi",
    category="multi_intent",
    description="Bestellung + Allergenfrage gleichzeitig",
    persona="neutral",
    noise_variant="clean",
    turns=[
        ScenarioTurn(
            user_utterance=(
                "Ich möchte Mandu bestellen. Enthält das auch Nüsse? "
                "Ich habe eine Nussallergie."
            )
        ),
        ScenarioTurn(user_utterance="Gut, dann nehme ich die Mandu. Abholung bitte."),
        ScenarioTurn(user_utterance="Meine Nummer ist 0155 66778899."),
        ScenarioTurn(user_utterance="Danke und tschüss."),
    ],
    expected_tools=["get_menu", "faq", "create_order", "send_sms"],
),

# ── multi-09: Three intents in one breath (order + reservation + hours) ───────
AudioScenario(
    id="multi-09",
    phase="multi",
    category="multi_intent",
    description="Drei Anliegen: Bibimbap bestellen, Tisch für 4 reservieren, Öffnungszeiten",
    persona="neutral",
    noise_variant="clean",
    turns=[
        ScenarioTurn(
            user_utterance=(
                "Ich will Bibimbap bestellen, habt ihr morgen einen Tisch für 4 frei, "
                "und wie sind eure Öffnungszeiten?"
            )
        ),
        ScenarioTurn(user_utterance="Lieferung bitte, Adresse ist Am Hofgarten 2."),
        ScenarioTurn(user_utterance="Meine Nummer ist 0151 11223344."),
        ScenarioTurn(user_utterance="Für den Tisch: morgen um 19 Uhr, Name Schneider."),
        ScenarioTurn(user_utterance="Alles klar, danke."),
    ],
    expected_tools=["get_menu", "get_date_info", "verify_address", "create_order", "send_sms",
                    "check_availability", "create_reservation"],
),

# ── multi-10: Escalation + order ─────────────────────────────────────────────
AudioScenario(
    id="multi-10",
    phase="multi",
    category="multi_intent",
    description="Beschwerde über App-Problem UND trotzdem eine Bestellung aufgeben",
    persona="frustrated",
    noise_variant="clean",
    turns=[
        ScenarioTurn(
            user_utterance=(
                "Ihre App funktioniert nicht, ich kann nicht bestellen! "
                "Können Sie mir trotzdem Kimchi Jjigae zur Lieferung bestellen?"
            )
        ),
        ScenarioTurn(user_utterance="Meine Adresse: Universitätsstr. 7, Bonn."),
        ScenarioTurn(user_utterance="0160 98765432."),
        ScenarioTurn(user_utterance="Okay, danke. Und die App bitte reparieren."),
        ScenarioTurn(user_utterance="Tschüss."),
    ],
    expected_tools=["technical_issues_callback", "get_menu", "verify_address",
                    "create_order", "send_sms"],
),

]
