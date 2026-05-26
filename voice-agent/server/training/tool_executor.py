"""
ToolExecutor -- Mock tool handlers for Tier 2.

get_menu, check_availability, create_order, create_reservation, verify_address, send_sms, etc.
Returns deterministic results based on scenario metadata.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OrderItem:
    """Menu item."""
    id: str
    name: str
    price: float
    available: bool = True


class ToolExecutor:
    """Execute mock tool calls for Tier 2."""

    def __init__(self):
        """Initialize with DOBOO menu data."""
        self.menu = self._init_menu()

    def _init_menu(self) -> Dict[str, List[OrderItem]]:
        """Initialize DOBOO menu — aligned with MENU_DISHES in call_auditor_de.py.
        Fix 2 (Iter 7): Replaced non-matching items (Gyeran Bap, Donkasu, California Roll,
        Ramyeon, etc.) with items that are in the auditor's MENU_DISHES set, so when the LLM
        picks a dish from the get_menu response, the hallucination check always passes.
        """
        return {
            "bowls": [
                OrderItem("bibimbap", "Bibimbap", 14.90),
                OrderItem("bulgogi", "Bulgogi", 16.90),
                OrderItem("tofu-bibimbap", "Tofu Bibimbap", 13.90),
            ],
            "hauptgerichte": [
                OrderItem("kimchi-jjigae", "Kimchi Jjigae", 13.90),
                OrderItem("japchae", "Japchae", 13.90),
                OrderItem("tteokbokki", "Tteokbokki", 11.90),
            ],
            "beilagen": [
                OrderItem("mandu", "Mandu", 7.90),
                OrderItem("tofu-jjigae", "Tofu Jjigae", 12.90),
            ],
            "desserts": [
                OrderItem("mochi-eis", "Mochi-Eis", 4.90),
            ],
        }

    async def get_menu(self, category: str) -> Dict[str, Any]:
        """Return menu items in category."""
        logger.debug(f"[Tool] get_menu(category={category})")
        items = self.menu.get(category, [])
        return {
            "category": category,
            "items": [
                {"id": i.id, "name": i.name, "price": i.price, "available": i.available}
                for i in items
            ],
        }

    async def check_availability(
        self,
        items: List[str],
        delivery_date: str,
        delivery_time: str,
    ) -> Dict[str, Any]:
        """Check if items are available for delivery."""
        logger.debug(f"[Tool] check_availability(items={items}, date={delivery_date}, time={delivery_time})")
        # Mock: all items available except Soju after 22:00
        available = {}
        for item in items:
            if item == "soju" and delivery_time > "22:00":
                available[item] = False
            else:
                available[item] = True
        return {"available": available, "delivery_window": f"{delivery_date} {delivery_time}"}

    async def create_order(
        self,
        customer_name: str,
        customer_phone: str,
        items: List[str],
        delivery_address: Optional[str] = None,
        delivery_time: Optional[str] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Create an order."""
        logger.debug(f"[Tool] create_order(name={customer_name}, phone={customer_phone}, items={items})")
        order_id = f"ORD-{hash(customer_phone) % 10000:05d}"
        return {
            "order_id": order_id,
            "status": "confirmed",
            "customer_name": customer_name,
            "items": items,
            "estimated_time": delivery_time or "30-45 Minuten",
            "total": 45.50,  # Mock total
        }

    async def create_reservation(
        self,
        customer_name: str,
        customer_phone: str,
        party_size: int,
        reservation_date: str,
        reservation_time: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Create a table reservation."""
        logger.debug(
            f"[Tool] create_reservation(name={customer_name}, party={party_size}, "
            f"date={reservation_date}, time={reservation_time})"
        )
        res_id = f"RES-{hash(customer_phone) % 10000:05d}"
        return {
            "reservation_id": res_id,
            "status": "confirmed",
            "customer_name": customer_name,
            "party_size": party_size,
            "date": reservation_date,
            "time": reservation_time,
            "table": f"Table {party_size}A",
        }

    async def verify_address(self, address: str) -> Dict[str, Any]:
        """Verify delivery address is valid."""
        logger.debug(f"[Tool] verify_address(address={address})")
        # Mock: reject fictional streets
        invalid_streets = ["Narnia", "Atlantis", "Oz"]
        is_valid = not any(street in address for street in invalid_streets)
        return {
            "address": address,
            "is_valid": is_valid,
            "deliverable": is_valid,
            "reason": "Address verified" if is_valid else "Fictional address",
        }

    async def send_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """Send SMS to customer."""
        logger.debug(f"[Tool] send_sms(phone={phone}, msg_len={len(message)})")
        return {
            "phone": phone,
            "message_sent": True,
            "message_id": f"SMS-{hash(phone) % 1000:04d}",
            "timestamp": "2026-04-01T12:00:00Z",
        }

    async def end_call(self, reason: str) -> Dict[str, Any]:
        """End call."""
        logger.debug(f"[Tool] end_call(reason={reason})")
        return {"call_ended": True, "reason": reason}

    async def transfer_to_human(self, reason: str) -> Dict[str, Any]:
        """Transfer to human agent."""
        logger.debug(f"[Tool] transfer_to_human(reason={reason})")
        return {"transferred": True, "reason": reason, "wait_time_estimated_secs": 120}

    async def callback_on_issue(
        self,
        phone: str,
        issue_type: str,
        callback_time_window: str = "1 hour",
    ) -> Dict[str, Any]:
        """Schedule callback for technical issues."""
        logger.debug(f"[Tool] callback_on_issue(phone={phone}, issue={issue_type})")
        return {
            "callback_scheduled": True,
            "phone": phone,
            "issue_type": issue_type,
            "callback_window": callback_time_window,
            "callback_id": f"CB-{hash(phone) % 10000:05d}",
        }

    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name."""
        tool_func = getattr(self, tool_name, None)
        if tool_func is None:
            return {"error": f"Tool {tool_name} not found"}
        try:
            result = await tool_func(**kwargs)
            logger.info(f"[Tool] {tool_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"[Tool] {tool_name} failed: {e}")
            return {"error": str(e)}
