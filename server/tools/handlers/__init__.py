"""
Phase 6 tool handlers — one module per tool.

Registration:
  ALL_HANDLERS maps tool name → handle() coroutine so the executor bridge
  can delegate to the correct handler without a long if/elif chain.

PR-7 (FINDING-012): six new handler modules added for tools that previously
fell through to the broken legacy path. Five are fail-clean stubs
(modify_order, cancel_order, order_status, modify_reservation,
cancel_reservation); capture_catering_lead implements the DB write directly
per Phase 4 C4 decision.
"""
from __future__ import annotations

from server.tools.handlers.create_order import handle as _create_order_handle
from server.tools.handlers.create_reservation import handle as _create_reservation_handle
from server.tools.handlers.verify_address import handle as _verify_address_handle
from server.tools.handlers.send_sms import handle as _send_sms_handle
from server.tools.handlers.transfer_to_human import handle as _transfer_handle
from server.tools.handlers.end_call import handle as _end_call_handle
from server.tools.handlers.get_menu import handle as _get_menu_handle
from server.tools.handlers.get_date_info import handle as _get_date_info_handle
from server.tools.handlers.faq import handle as _faq_handle
# PR-7 / FINDING-012 — new handlers
from server.tools.handlers.modify_order import handle as _modify_order_handle
from server.tools.handlers.cancel_order import handle as _cancel_order_handle
from server.tools.handlers.order_status import handle as _order_status_handle
from server.tools.handlers.modify_reservation import handle as _modify_reservation_handle
from server.tools.handlers.cancel_reservation import handle as _cancel_reservation_handle
from server.tools.handlers.capture_catering_lead import handle as _capture_catering_lead_handle

ALL_HANDLERS: dict = {
    # ── Core ordering & reservations ─────────────────────────────────────────
    "create_order": _create_order_handle,
    "create_reservation": _create_reservation_handle,
    # ── Phase 3 stub handlers (PR-7) ─────────────────────────────────────────
    "modify_order": _modify_order_handle,
    "cancel_order": _cancel_order_handle,
    "order_status": _order_status_handle,
    "modify_reservation": _modify_reservation_handle,
    "cancel_reservation": _cancel_reservation_handle,
    "capture_catering_lead": _capture_catering_lead_handle,
    # ── Utility & support ────────────────────────────────────────────────────
    "verify_address": _verify_address_handle,
    "send_sms": _send_sms_handle,
    "transfer_to_human": _transfer_handle,
    "transfer_to_tier2": _transfer_handle,  # alias
    "end_call": _end_call_handle,
    "get_menu": _get_menu_handle,
    "get_date_info": _get_date_info_handle,
    "faq": _faq_handle,
}
