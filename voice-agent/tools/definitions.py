"""
Gemini FunctionDeclarations for all Sailly tools.
Converted from legacy ElevenLabs webhook tool schemas.
"""


TOOL_DECLARATIONS = [
    {
        "name": "check_availability",
        "description": (
            "Prüft Tischverfügbarkeit UND Bestellstatus/Wartezeiten. "
            "Für Reservierungen: Datum, Uhrzeit, Personenanzahl übergeben. "
            "Für Bestellstatus/Wartezeit-Fragen: ohne Datum/Uhrzeit aufrufen."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Datum im Format YYYY-MM-DD (optional für Wartezeit-Fragen)"},
                "time": {"type": "string", "description": "Uhrzeit im Format HH:MM (optional für Wartezeit-Fragen)"},
                "party_size": {"type": "integer", "description": "Anzahl der Personen"},
            },
            "required": ["party_size"],
        },
    },
    {
        "name": "create_reservation",
        "description": "Erstelle eine bestätigte Reservierung. Erst aufrufen wenn alle Pflichtfelder bestätigt sind.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Datum im Format YYYY-MM-DD"},
                "time": {"type": "string", "description": "Uhrzeit im Format HH:MM"},
                "party_size": {"type": "integer", "description": "Anzahl der Personen"},
                "name": {"type": "string", "description": "Name des Gastes"},
                "phone": {"type": "string", "description": "Telefonnummer des Gastes"},
                "email": {"type": "string", "description": "E-Mail-Adresse (optional)"},
                "notes": {"type": "string", "description": "Besondere Wünsche (optional)"},
            },
            "required": ["date", "time", "party_size", "name", "phone"],
        },
    },
    {
        "name": "get_restaurant_info",
        "description": "Hole Informationen über das Restaurant (Öffnungszeiten, Menü, Lage, Parken etc.). Nie aus dem Gedächtnis.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Welche Information wird benötigt"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_menu",
        "description": "Hole die Speisekarte oder eine bestimmte Kategorie. Bei Menü-Fragen, Empfehlungen, Preisen oder Allergenen.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Kategorie: vorspeisen, hauptgerichte, sushi, desserts, beilagen, alle",
                },
            },
            "required": [],
        },
    },
    {
        "name": "create_order",
        "description": (
            "Erstelle eine Takeaway/Delivery-Bestellung mit Zahlungslink. "
            "Aufrufen nach vollständiger Bestellung (Name, Telefon, Gerichte bestätigt). "
            "PFLICHT bei Delivery: delivery_address MUSS immer übergeben werden — "
            "die exakt verifizierte Adresse aus verify_address. NIEMALS ohne delivery_address aufrufen wenn order_type=delivery."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name des Bestellers"},
                "phone": {"type": "string", "description": "Telefonnummer (E.164)"},
                "messaging_phone": {"type": "string", "description": "Nummer für SMS/WhatsApp-Bestätigung (E.164)"},
                "channel": {"type": "string", "description": "sms oder whatsapp"},
                "order_items": {"type": "string", "description": "Bestellte Gerichte mit Mengen (z.B. Gericht x2, Gericht x1)"},
                "order_type": {"type": "string", "description": "takeaway oder delivery"},
                "payment_method": {"type": "string", "description": "cash, card oder online"},
                "total_price": {"type": "number", "description": "Gesamtpreis in EUR"},
                "delivery_address": {"type": "string", "description": "Lieferadresse (nur delivery)"},
                "special_requests": {"type": "string", "description": "Besondere Wünsche (optional)"},
                "estimated_minutes": {"type": "number", "description": "Geschätzte Zeit in Minuten"},
            },
            "required": ["name", "phone", "messaging_phone", "channel", "order_items", "order_type", "payment_method", "total_price"],
        },
    },
    {
        "name": "get_date_info",
        "description": "Gibt den Wochentag und relative Info für ein Datum zurück. IMMER aufrufen bei Wochentag-Fragen.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Datum im Format YYYY-MM-DD oder deutsch (15. April 2026)"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_weather",
        "description": "Aktuelles Wetter für den Restaurantstandort (Bonn). Temperatur, Regen, Außenbereich-Empfehlung.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Ort (optional, Standard: Bonn)"},
            },
            "required": [],
        },
    },
    {
        "name": "transfer_to_human",
        "description": (
            "Leitet den Anruf an einen Mitarbeiter weiter. Aufrufen wenn: "
            "(1) Gast nach Mensch fragt, (2) Problem 3x ungelöst, (3) Frustration, (4) >8 Min ohne Abschluss."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "caller_requested | loop_detected | frustration | timeout",
                },
                "conversation_id": {"type": "string", "description": "Aktuelle conversation_id"},
                "call_sid": {"type": "string", "description": "Twilio Call SID"},
            },
            "required": ["reason"],
        },
    },
    {
        "name": "verify_address",
        "description": (
            "Validiere eine Lieferadresse oder Geschäftsadresse mit Google Geocoding API. "
            "Rufe auf, bevor eine Bestellung/Reservierung mit Adresse bestätigt wird. "
            "Wenn ungültig, höflich den Anrufer um die richtige Adresse bitten."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Vollständige Adresse (z.B. 'Hauptstr. 123, 12345 Berlin')"},
                "city": {"type": "string", "description": "Stadt (optional für Präzisierung)"},
                "country": {"type": "string", "description": "Land, default 'Deutschland'"},
            },
            "required": ["address"],
        },
    },
    {
        "name": "end_call",
        "description": "Beendet das Gespräch nach Verabschiedung. Aufrufen nur wenn der Anrufer sich verabschiedet hat.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Grund für call end: goodbye | completed | timeout"},
            },
            "required": [],
        },
    },
]
