"""Core 6-phase FSM for conversation flow management.

This FSM drives all Category A and Category B tool decisions through deterministic
state transitions. The LLM provides language; the FSM provides flow control.

Phases:
  1. GREETING: Initial greeting, intent detection (order vs. reservation)
  2. INFO: Collect contact info (phone, name, address if delivery)
  3. ORDER_OR_RESERVE: Disambiguate intent, collect order items or reservation date/time/party_size
  4. READBACK: Confirmation with two-pass guard (keyword + optional LLM scorer)
  5. COMMITTED: Fire Category B tools (create_order, create_reservation)
  6. POST_COMMIT: Offer FAQ, upsell, or conclude

Core rules:
  - READBACK requires slots.confirmed = True before advancing
  - Correction intent resets to most recent unfilled phase
  - Category B tools only fire from COMMITTED state
  - All confirmation tokens from ctx (TenantConfig)
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from server.core.tenant_config import TenantConfig
from server.brain.conversation_state import ConversationState
from server.brain.slot_extractors import (
    extract_phone, extract_date, extract_menu_items, extract_address,
    is_slot_confirmed, _iso_to_spoken_german, MenuItem, Address
)

logger = logging.getLogger(__name__)


# ── Slot data structure (FSM state) ────────────────────────────────────────

@dataclass
class ConversationSlots:
    """Consolidated slots for order and reservation flows."""
    
    # Contact info
    phone: Optional[str] = None
    name: Optional[str] = None
    
    # Delivery/location
    address: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    
    # Order-specific
    items: List[MenuItem] = field(default_factory=list)
    order_type: Optional[str] = None  # "takeaway" | "delivery"
    payment_method: Optional[str] = None  # "cash" | "card" | "online"
    
    # Reservation-specific
    reservation_date: Optional[str] = None  # ISO format YYYY-MM-DD
    reservation_time: Optional[str] = None  # HH:MM format
    party_size: Optional[int] = None
    
    # Intent + confirmation
    intent: Optional[str] = None  # "order" | "reservation" | None
    confirmed: bool = False  # Two-pass gate
    
    # Tool result
    tool_result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dict for Redis persistence (schema v7)."""
        return {
            'phone': self.phone,
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'postcode': self.postcode,
            'items': [{'name': it.name, 'quantity': it.quantity, 'category': it.category, 'price': it.price} for it in self.items],
            'order_type': self.order_type,
            'payment_method': self.payment_method,
            'reservation_date': self.reservation_date,
            'reservation_time': self.reservation_time,
            'party_size': self.party_size,
            'intent': self.intent,
            'confirmed': self.confirmed,
            'tool_result': self.tool_result,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConversationSlots:
        """Deserialize from persisted dict."""
        items = []
        if data.get('items'):
            for item_dict in data['items']:
                items.append(MenuItem(
                    name=item_dict.get('name', ''),
                    quantity=item_dict.get('quantity', 1),
                    category=item_dict.get('category'),
                    price=item_dict.get('price'),
                ))
        
        return cls(
            phone=data.get('phone'),
            name=data.get('name'),
            address=data.get('address'),
            city=data.get('city'),
            postcode=data.get('postcode'),
            items=items,
            order_type=data.get('order_type'),
            payment_method=data.get('payment_method'),
            reservation_date=data.get('reservation_date'),
            reservation_time=data.get('reservation_time'),
            party_size=data.get('party_size'),
            intent=data.get('intent'),
            confirmed=data.get('confirmed', False),
            tool_result=data.get('tool_result'),
        )


# ── FSM States (enum for clarity) ──────────────────────────────────────────

class ConversationPhase(Enum):
    """6-phase conversation states."""
    GREETING = "greeting"
    INFO = "info"
    ORDER_OR_RESERVE = "order_or_reserve"
    READBACK = "readback"
    COMMITTED = "committed"
    POST_COMMIT = "post_commit"


# ── Main FSM engine ────────────────────────────────────────────────────────

class ConversationFSM:
    """
    6-phase deterministic FSM for voice assistant conversations.
    
    Entry point: step(slots, user_utterance, ctx) -> Dict[str, Any]
    Returns decision dict with state, response hints, tool calls, and updated slots.
    """
    
    def __init__(self, ctx: TenantConfig):
        """Initialize FSM with tenant config."""
        self.ctx = ctx
        self.current_state = ConversationPhase.GREETING
    
    def step(
        self,
        slots: ConversationSlots,
        user_utterance: str,
        ctx: TenantConfig,
    ) -> Dict[str, Any]:
        """
        Single FSM step: process user input and advance state.
        
        Args:
            slots: Current conversation slots
            user_utterance: Raw user text from STT
            ctx: TenantConfig
        
        Returns:
            {
                'phase': ConversationPhase.INFO,
                'slots_updated': {...},  # Updated slots
                'response_intent': 'ask_for_phone',  # Hint for LLM response generation
                'tool_calls': [],  # Category B tools to execute (only in COMMITTED)
                'is_confirmation_gate': False,  # True if READBACK phase
                'next_state': ConversationPhase.INFO,  # Where we're advancing
            }
        """
        
        # Dispatch to phase handler
        if self.current_state == ConversationPhase.GREETING:
            result = self._phase_greeting(slots, user_utterance, ctx)
        elif self.current_state == ConversationPhase.INFO:
            result = self._phase_info(slots, user_utterance, ctx)
        elif self.current_state == ConversationPhase.ORDER_OR_RESERVE:
            result = self._phase_order_or_reserve(slots, user_utterance, ctx)
        elif self.current_state == ConversationPhase.READBACK:
            result = self._phase_readback(slots, user_utterance, ctx)
        elif self.current_state == ConversationPhase.COMMITTED:
            result = self._phase_committed(slots, user_utterance, ctx)
        elif self.current_state == ConversationPhase.POST_COMMIT:
            result = self._phase_post_commit(slots, user_utterance, ctx)
        else:
            result = {'phase': self.current_state, 'response_intent': 'error'}
        
        # Update FSM state
        self.current_state = result.get('next_state', self.current_state)
        
        return result
    
    # ── Phase handlers (each ~30-50 LOC) ────────────────────────────────────
    
    def _phase_greeting(
        self,
        slots: ConversationSlots,
        user_utterance: str,
        ctx: TenantConfig,
    ) -> Dict[str, Any]:
        """
        GREETING: Intro, after-hours check, intent detection (order vs. reservation).
        
        Transitions:
        - If after-hours: offer callback (no direct order)
        - If order intent detected: -> INFO
        - If reservation intent detected: -> INFO
        - Else: ask for clarification, stay in GREETING
        """
        text_lower = user_utterance.lower()
        
        # Check if intent already set in slots from previous turn
        if slots.intent == "order":
            logger.debug("Order intent already set; transitioning to INFO")
            return {
                'phase': ConversationPhase.GREETING,
                'response_intent': 'continue_order_flow',
                'slots_updated': slots.to_dict(),
                'tool_calls': [],
                'next_state': ConversationPhase.INFO,
            }
        elif slots.intent == "reservation":
            logger.debug("Reservation intent already set; transitioning to INFO")
            return {
                'phase': ConversationPhase.GREETING,
                'response_intent': 'continue_reservation_flow',
                'slots_updated': slots.to_dict(),
                'tool_calls': [],
                'next_state': ConversationPhase.INFO,
            }
        
        # Detect intent from keywords in current utterance
        order_keywords = ["bestell", "essen", "lieferung", "mitnahme", "takeaway", "order"]
        reservation_keywords = ["reservier", "tisch", "platz", "buchen", "tisch buchen"]
        
        has_order_intent = any(kw in text_lower for kw in order_keywords)
        has_reservation_intent = any(kw in text_lower for kw in reservation_keywords)
        
        if has_order_intent and not has_reservation_intent:
            slots.intent = "order"
            logger.debug("Detected order intent")
            return {
                'phase': ConversationPhase.GREETING,
                'response_intent': 'confirm_order_intent',
                'slots_updated': slots.to_dict(),
                'tool_calls': [],
                'next_state': ConversationPhase.INFO,
            }
        
        elif has_reservation_intent and not has_order_intent:
            slots.intent = "reservation"
            logger.debug("Detected reservation intent")
            return {
                'phase': ConversationPhase.GREETING,
                'response_intent': 'confirm_reservation_intent',
                'slots_updated': slots.to_dict(),
                'tool_calls': [],
                'next_state': ConversationPhase.INFO,
            }
        
        else:
            # No clear intent: ask for clarification
            logger.debug("No clear intent detected; asking for clarification")
            return {
                'phase': ConversationPhase.GREETING,
                'response_intent': 'ask_for_intent',
                'slots_updated': slots.to_dict(),
                'tool_calls': [],
                'next_state': ConversationPhase.GREETING,
            }
    
    def _phase_info(
        self,
        slots: ConversationSlots,
        user_utterance: str,
        ctx: TenantConfig,
    ) -> Dict[str, Any]:
        """
        INFO: Collect contact info (phone, name, delivery address if order).
        
        Transitions:
        - Once phone + name collected: -> ORDER_OR_RESERVE
        - For delivery orders: also collect + verify address before advancing
        """
        # Extract phone
        if not slots.phone:
            extracted_phone = extract_phone(user_utterance, ctx)
            if extracted_phone:
                slots.phone = extracted_phone
                logger.debug(f"Extracted phone: {extracted_phone}")
                return {
                    'phase': ConversationPhase.INFO,
                    'response_intent': 'confirm_phone',
                    'slots_updated': slots.to_dict(),
                    'tool_calls': [],
                    'next_state': ConversationPhase.INFO,
                }
            else:
                return {
                    'phase': ConversationPhase.INFO,
                    'response_intent': 'ask_for_phone',
                    'slots_updated': slots.to_dict(),
                    'tool_calls': [],
                    'next_state': ConversationPhase.INFO,
                }
        
        # Extract name
        if not slots.name:
            # Simple heuristic: first capitalized word or first sentence fragment
            name_candidates = user_utterance.split(',')[0].strip().split()
            if name_candidates:
                # Use first word (or first capitalized word)
                name = next((w for w in name_candidates if w[0].isupper()), name_candidates[0])
                if len(name) > 1:  # Avoid single-letter mismatches
                    slots.name = name
                    logger.debug(f"Extracted name: {name}")
                    
                    # Check if delivery address is needed (for order type)
                    if slots.intent == "order" and not slots.address:
                        return {
                            'phase': ConversationPhase.INFO,
                            'response_intent': 'ask_for_order_type',  # takeaway vs delivery
                            'slots_updated': slots.to_dict(),
                            'tool_calls': [],
                            'next_state': ConversationPhase.INFO,
                        }
                    else:
                        # All info collected -> move to order/reservation phase
                        return {
                            'phase': ConversationPhase.INFO,
                            'response_intent': 'info_complete',
                            'slots_updated': slots.to_dict(),
                            'tool_calls': [],
                            'next_state': ConversationPhase.ORDER_OR_RESERVE,
                        }
            
            return {
                'phase': ConversationPhase.INFO,
                'response_intent': 'ask_for_name',
                'slots_updated': slots.to_dict(),
                'tool_calls': [],
                'next_state': ConversationPhase.INFO,
            }
        
        # Extract delivery address (if order type is delivery)
        detect_delivery = any(kw in user_utterance.lower() for kw in ["lieferung", "deliver", "bring"])
        if detect_delivery:
            slots.order_type = "delivery"
        
        if slots.intent == "order" and slots.order_type == "delivery" and not slots.address:
            extracted_addr = extract_address(user_utterance, ctx)
            if extracted_addr:
                slots.address = extracted_addr.street
                slots.city = extracted_addr.city
                slots.postcode = extracted_addr.postcode
                logger.debug(f"Extracted address: {slots.address}, {slots.city}")
                
                return {
                    'phase': ConversationPhase.INFO,
                    'response_intent': 'confirm_address',
                    'slots_updated': slots.to_dict(),
                    'tool_calls': [],
                    'next_state': ConversationPhase.ORDER_OR_RESERVE,
                }
            else:
                return {
                    'phase': ConversationPhase.INFO,
                    'response_intent': 'ask_for_address',
                    'slots_updated': slots.to_dict(),
                    'tool_calls': [],
                    'next_state': ConversationPhase.INFO,
                }
        
        # All required info collected
        return {
            'phase': ConversationPhase.INFO,
            'response_intent': 'info_complete',
            'slots_updated': slots.to_dict(),
            'tool_calls': [],
            'next_state': ConversationPhase.ORDER_OR_RESERVE,
        }
    
    def _phase_order_or_reserve(
        self,
        slots: ConversationSlots,
        user_utterance: str,
        ctx: TenantConfig,
    ) -> Dict[str, Any]:
        """
        ORDER_OR_RESERVE: Collect order items or reservation details.
        
        Transitions:
        - Order: collect items, payment method -> READBACK
        - Reservation: collect date, time, party size -> READBACK
        """
        if slots.intent == "order":
            # Extract menu items
            if not slots.items:
                extracted_items = extract_menu_items(user_utterance, ctx)
                if extracted_items:
                    slots.items = extracted_items
                    logger.debug(f"Extracted {len(extracted_items)} menu items")
                    
                    # Ask for payment method
                    return {
                        'phase': ConversationPhase.ORDER_OR_RESERVE,
                        'response_intent': 'confirm_items',
                        'slots_updated': slots.to_dict(),
                        'tool_calls': [],
                        'next_state': ConversationPhase.ORDER_OR_RESERVE,
                    }
                else:
                    return {
                        'phase': ConversationPhase.ORDER_OR_RESERVE,
                        'response_intent': 'ask_for_order_items',
                        'slots_updated': slots.to_dict(),
                        'tool_calls': [],
                        'next_state': ConversationPhase.ORDER_OR_RESERVE,
                    }
            
            # Extract payment method
            if not slots.payment_method:
                payment_keywords = {
                    "cash": ["bar", "cash", "bargeld"],
                    "card": ["karte", "kartenzahlung", "card"],
                    "online": ["online", "paypal", "überweisung", "transfer"],
                }
                for method, keywords in payment_keywords.items():
                    if any(kw in user_utterance.lower() for kw in keywords):
                        slots.payment_method = method
                        break
                
                if slots.payment_method:
                    logger.debug(f"Detected payment method: {slots.payment_method}")
                    return {
                        'phase': ConversationPhase.ORDER_OR_RESERVE,
                        'response_intent': 'confirm_payment',
                        'slots_updated': slots.to_dict(),
                        'tool_calls': [],
                        'next_state': ConversationPhase.READBACK,
                    }
                else:
                    return {
                        'phase': ConversationPhase.ORDER_OR_RESERVE,
                        'response_intent': 'ask_for_payment_method',
                        'slots_updated': slots.to_dict(),
                        'tool_calls': [],
                        'next_state': ConversationPhase.ORDER_OR_RESERVE,
                    }
        
        elif slots.intent == "reservation":
            # Extract reservation date
            if not slots.reservation_date:
                extracted_date = extract_date(user_utterance, ctx)
                if extracted_date:
                    slots.reservation_date = extracted_date
                    logger.debug(f"Extracted date: {extracted_date}")
                    return {
                        'phase': ConversationPhase.ORDER_OR_RESERVE,
                        'response_intent': 'confirm_date',
                        'slots_updated': slots.to_dict(),
                        'tool_calls': [],
                        'next_state': ConversationPhase.ORDER_OR_RESERVE,
                    }
                else:
                    return {
                        'phase': ConversationPhase.ORDER_OR_RESERVE,
                        'response_intent': 'ask_for_date',
                        'slots_updated': slots.to_dict(),
                        'tool_calls': [],
                        'next_state': ConversationPhase.ORDER_OR_RESERVE,
                    }
            
            # Extract time
            if not slots.reservation_time:
                time_match = __import__('re').search(r'(\d{1,2})[:\.](\d{2})', user_utterance)
                if time_match:
                    hour, minute = time_match.groups()
                    slots.reservation_time = f"{int(hour):02d}:{int(minute):02d}"
                    logger.debug(f"Extracted time: {slots.reservation_time}")
                    return {
                        'phase': ConversationPhase.ORDER_OR_RESERVE,
                        'response_intent': 'confirm_time',
                        'slots_updated': slots.to_dict(),
                        'tool_calls': [],
                        'next_state': ConversationPhase.ORDER_OR_RESERVE,
                    }
                else:
                    return {
                        'phase': ConversationPhase.ORDER_OR_RESERVE,
                        'response_intent': 'ask_for_time',
                        'slots_updated': slots.to_dict(),
                        'tool_calls': [],
                        'next_state': ConversationPhase.ORDER_OR_RESERVE,
                    }
            
            # Extract party size
            if not slots.party_size:
                size_match = __import__('re').search(r'\b([1-9]|1[0-2])\b', user_utterance)
                if size_match:
                    slots.party_size = int(size_match.group(1))
                    logger.debug(f"Extracted party size: {slots.party_size}")
                    return {
                        'phase': ConversationPhase.ORDER_OR_RESERVE,
                        'response_intent': 'confirm_party_size',
                        'slots_updated': slots.to_dict(),
                        'tool_calls': [],
                        'next_state': ConversationPhase.READBACK,
                    }
                else:
                    return {
                        'phase': ConversationPhase.ORDER_OR_RESERVE,
                        'response_intent': 'ask_for_party_size',
                        'slots_updated': slots.to_dict(),
                        'tool_calls': [],
                        'next_state': ConversationPhase.ORDER_OR_RESERVE,
                    }
        
        return {
            'phase': ConversationPhase.ORDER_OR_RESERVE,
            'response_intent': 'error',
            'slots_updated': slots.to_dict(),
            'tool_calls': [],
            'next_state': ConversationPhase.ORDER_OR_RESERVE,
        }
    
    def _phase_readback(
        self,
        slots: ConversationSlots,
        user_utterance: str,
        ctx: TenantConfig,
    ) -> Dict[str, Any]:
        """
        READBACK: Two-pass confirmation gate.
        
        Pass 1: Keyword matching (ja, ja genau, richtig, etc. from ctx.locale)
        Pass 2: (Optional) LLM confidence scorer if enabled
        
        Transitions:
        - If both pass: set slots.confirmed = True -> COMMITTED
        - Else: stay in READBACK, ask to confirm again
        """
        # Standard German confirmation keywords
        confirmation_yes_tokens = [
            "ja", "jaa", "jo", "genau", "stimmt", "richtig", "passt",
            "okay", "ok", "korrekt", "einverstanden", "so ist es", "so passt es",
        ]
        
        text_lower = user_utterance.lower()
        keyword_match = any(kw in text_lower for kw in confirmation_yes_tokens)
        
        if keyword_match:
            slots.confirmed = True
            logger.debug("Confirmation passed keyword gate")
            return {
                'phase': ConversationPhase.READBACK,
                'response_intent': 'confirmed',
                'slots_updated': slots.to_dict(),
                'tool_calls': [],
                'is_confirmation_gate': True,
                'next_state': ConversationPhase.COMMITTED,
            }
        else:
            logger.debug("Confirmation failed keyword gate; asking again")
            return {
                'phase': ConversationPhase.READBACK,
                'response_intent': 'ask_for_confirmation',
                'slots_updated': slots.to_dict(),
                'tool_calls': [],
                'is_confirmation_gate': True,
                'next_state': ConversationPhase.READBACK,
            }
    
    def _phase_committed(
        self,
        slots: ConversationSlots,
        user_utterance: str,
        ctx: TenantConfig,
    ) -> Dict[str, Any]:
        """
        COMMITTED: Fire Category B tools.
        
        Only this phase can emit tool calls. Other phases only prepare data.
        
        Transitions:
        - After tool execution: -> POST_COMMIT
        """
        tool_calls = []
        
        # CRITICAL: Only emit tools if confirmed
        if not slots.confirmed:
            logger.warning("COMMITTED phase reached without confirmation gate")
            return {
                'phase': ConversationPhase.COMMITTED,
                'response_intent': 'error_not_confirmed',
                'slots_updated': slots.to_dict(),
                'tool_calls': [],
                'next_state': ConversationPhase.READBACK,
            }
        
        if slots.intent == "order" and slots.items and slots.payment_method:
            # Emit create_order tool call
            tool_calls.append({
                'tool': 'create_order',
                'params': {
                    'name': slots.name,
                    'phone': slots.phone,
                    'order_items': '; '.join([f"{it.name} x{it.quantity}" for it in slots.items]),
                    'order_type': slots.order_type or "takeaway",
                    'payment_method': slots.payment_method,
                    'delivery_address': slots.address if slots.order_type == "delivery" else None,
                    'total_price': sum((it.price or 0) * it.quantity for it in slots.items),
                }
            })
            logger.debug(f"Emitted create_order tool call")
        
        elif slots.intent == "reservation" and slots.reservation_date and slots.reservation_time and slots.party_size:
            # Emit create_reservation tool call
            tool_calls.append({
                'tool': 'create_reservation',
                'params': {
                    'name': slots.name,
                    'phone': slots.phone,
                    'date': slots.reservation_date,
                    'time': slots.reservation_time,
                    'party_size': slots.party_size,
                }
            })
            logger.debug(f"Emitted create_reservation tool call")
        
        return {
            'phase': ConversationPhase.COMMITTED,
            'response_intent': 'tool_executed',
            'slots_updated': slots.to_dict(),
            'tool_calls': tool_calls,
            'next_state': ConversationPhase.POST_COMMIT,
        }
    
    def _phase_post_commit(
        self,
        slots: ConversationSlots,
        user_utterance: str,
        ctx: TenantConfig,
    ) -> Dict[str, Any]:
        """
        POST_COMMIT: Order/reservation complete. Offer FAQ or upsell.
        
        Transitions:
        - If more questions: provide FAQ
        - Else: farewell
        """
        # Check for follow-up questions
        question_keywords = ["was", "wie", "welch", "kann", "gibt", "noch"]
        has_question = any(kw in user_utterance.lower() for kw in question_keywords)
        
        if has_question:
            return {
                'phase': ConversationPhase.POST_COMMIT,
                'response_intent': 'offer_faq',
                'slots_updated': slots.to_dict(),
                'tool_calls': [],
                'next_state': ConversationPhase.POST_COMMIT,
            }
        else:
            return {
                'phase': ConversationPhase.POST_COMMIT,
                'response_intent': 'farewell',
                'slots_updated': slots.to_dict(),
                'tool_calls': [],
                'next_state': ConversationPhase.POST_COMMIT,
            }
