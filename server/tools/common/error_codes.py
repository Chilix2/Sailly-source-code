"""
Structured error taxonomy per decision structured-codes (9.O4).

Every tool handler should return one of these codes in `ToolResult.error_code`
on a failure path.  The dispatcher writes the codes array to
`google_turn_metrics.error_codes` for dashboard queries (Task A3).

Usage:
    from server.tools.common.error_codes import ErrorCode
    return ToolResult(ok=False, error="validation failed", error_code=ErrorCode.TOOL_VALIDATION_FAILED)
"""


class ErrorCode:
    # ── Tool execution ─────────────────────────────────────────────────────────
    TOOL_VALIDATION_FAILED     = "ERR_TOOL_VALIDATION_FAILED"
    TOOL_DEPENDENCY_TIMEOUT    = "ERR_TOOL_DEPENDENCY_TIMEOUT"
    TOOL_DEPENDENCY_ERROR      = "ERR_TOOL_DEPENDENCY_ERROR"
    TOOL_AFTER_HOURS           = "ERR_TOOL_AFTER_HOURS"
    TOOL_QUANTITY_CAPPED       = "ERR_TOOL_QUANTITY_CAPPED"
    TOOL_MONETARY_CAP          = "ERR_TOOL_MONETARY_CAP"
    TOOL_DEPRECATED            = "ERR_TOOL_DEPRECATED"
    TOOL_NOT_IMPLEMENTED       = "ERR_NOT_IMPLEMENTED"

    # ── External services ──────────────────────────────────────────────────────
    MAPS_TIMEOUT               = "ERR_MAPS_TIMEOUT"
    MAPS_NOT_FOUND             = "ERR_MAPS_NOT_FOUND"
    MAPS_BREAKER_OPEN          = "ERR_MAPS_BREAKER_OPEN"
    TWILIO_ERROR               = "ERR_TWILIO_ERROR"
    TWILIO_BREAKER_OPEN        = "ERR_TWILIO_BREAKER_OPEN"
    SMS_SEND_FAILED            = "ERR_SMS_SEND_FAILED"
    SMS_BREAKER_OPEN           = "ERR_SMS_BREAKER_OPEN"
    WHATSAPP_TEMPLATE_FAILED   = "ERR_WHATSAPP_TEMPLATE_FAILED"
    WHATSAPP_BREAKER_OPEN      = "ERR_WHATSAPP_BREAKER_OPEN"

    # ── LLM ───────────────────────────────────────────────────────────────────
    LLM_429                    = "ERR_LLM_429"
    LLM_TIMEOUT                = "ERR_LLM_TIMEOUT"
    LLM_PARSE_FAILED           = "ERR_LLM_PARSE_FAILED"
    LLM_BREAKER_OPEN           = "ERR_LLM_BREAKER_OPEN"

    # ── STT ───────────────────────────────────────────────────────────────────
    STT_TIMEOUT                = "ERR_STT_TIMEOUT"
    STT_RECONNECT              = "ERR_STT_RECONNECT"
    STT_LOW_CONFIDENCE         = "ERR_STT_LOW_CONFIDENCE"

    # ── State / contract ──────────────────────────────────────────────────────
    INVALID_INTENT_TRANSITION  = "ERR_INVALID_INTENT_TRANSITION"
    SLOT_NOT_VERIFIED          = "ERR_SLOT_NOT_VERIFIED"
    MISSING_REQUIRED_SLOT      = "ERR_MISSING_REQUIRED_SLOT"
    DUPLICATE_ORDER            = "ERR_DUPLICATE_ORDER"

    # ── Safety / policy ────────────────────────────────────────────────────────
    RATE_LIMITED               = "ERR_RATE_LIMITED"
    STRICT_GATE_FAILED         = "ERR_STRICT_GATE_FAILED"
    TRANSFER_FAILED            = "ERR_TRANSFER_FAILED"
    FAQ_UNSUPPORTED            = "ERR_FAQ_UNSUPPORTED"
