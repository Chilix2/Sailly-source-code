"""
SMS/WhatsApp confirmation service for reservations and orders.
Production-ready implementation using WhatsApp templates for unlimited recipients.
Falls back to free-form messages (24-hour window) then SMS.
Message formatting matches legacy pipeline exactly.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

WHATSAPP_BUSINESS_NUMBER = "491634549834"
WHATSAPP_OPTIN_TEXT_DE = "Bitte kontaktiert mich in Zukunft per WhatsApp"
WHATSAPP_OPTIN_LINK = f"https://wa.me/{WHATSAPP_BUSINESS_NUMBER}?text={WHATSAPP_OPTIN_TEXT_DE.replace(' ', '%20')}"


def append_whatsapp_optin_link(message: str) -> str:
    """Append WhatsApp opt-in link to an SMS message."""
    return f"{message}\n\nWhatsApp: {WHATSAPP_OPTIN_LINK}"
BERLIN_TZ = ZoneInfo("Europe/Berlin")

# WhatsApp template names (must be created in Meta Business Manager)
WHATSAPP_TEMPLATES = {
    "reservation_confirmation": "reservation_confirmed",
    "order_confirmation_takeaway": "order_confirmed_takeaway",
    "order_confirmation_delivery": "order_confirmed_delivery",
}

async def send_confirmation(
    phone: str,
    message: str,
    channel: Optional[str] = None,
    template_type: Optional[str] = None,
    human_message: Optional[str] = None
) -> dict:
    """
    Send confirmation via WhatsApp or SMS, respecting opt-in status.

    Smart routing:
    - If phone is WhatsApp-opted-in: WhatsApp template -> freeform -> SMS fallback
    - If phone is NOT opted-in: SMS only (with WhatsApp opt-in link appended)
    - channel="sms" forces SMS; channel="whatsapp" forces WhatsApp attempt

    Args:
        phone: E.164 formatted phone number
        message: Pipe-delimited template params (for WhatsApp) or plain text
        channel: Force channel. If None, auto-detect via opt-in DB lookup.
        template_type: WhatsApp template type if using templates
        human_message: Human-readable text for SMS (used instead of pipe-delimited message)
    """
    if not phone or not message:
        return {"success": False, "method": None, "error": "Missing phone or message"}

    sms_body = human_message or message

    if channel == "sms":
        return await send_sms(phone, append_whatsapp_optin_link(sms_body))

    # Check WhatsApp opt-in from database
    opted_in = False
    try:
        from server.database import is_whatsapp_opted_in
        opted_in = await is_whatsapp_opted_in(phone)
    except Exception as e:
        logger.warning(f"Could not check WhatsApp opt-in for {phone}: {e}")

    if opted_in or channel == "whatsapp":
        if template_type:
            result = await send_whatsapp_template(phone, message, template_type)
            if result["success"]:
                return result

        result = await send_whatsapp_freeform(phone, sms_body)
        if result["success"]:
            return result

        logger.info(f"WhatsApp failed for {phone}, falling back to SMS")
        return await send_sms(phone, append_whatsapp_optin_link(sms_body))
    else:
        logger.info(f"Phone {phone} not WhatsApp-opted-in, sending SMS with opt-in link")
        return await send_sms(phone, append_whatsapp_optin_link(sms_body))



async def send_whatsapp_template(
    phone: str,
    message: str,
    template_type: str
) -> dict:
    """
    Send via Meta WhatsApp Cloud API using pre-approved templates.
    Required for production (unlimited recipients).
    
    Template must be created in Meta Business Manager and approved by Meta.
    
    Message format is pipe-delimited (param1|param2|param3...) and will be
    split into template variables {{1}}, {{2}}, {{3}}, etc.
    """
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    
    if not phone_number_id or not access_token:
        logger.debug("WhatsApp not configured (WHATSAPP_PHONE_NUMBER_ID or WHATSAPP_ACCESS_TOKEN missing)")
        return {"success": False, "method": None, "error": "WhatsApp not configured"}
    
    template_name = WHATSAPP_TEMPLATES.get(template_type)
    if not template_name:
        logger.warning(f"Unknown template type: {template_type}")
        return {"success": False, "method": None, "error": f"Unknown template: {template_type}"}
    
    try:
        import httpx
        
        # Normalize phone: Meta expects digits only (remove + prefix)
        normalized_phone = phone.lstrip("+")
        
        url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        # Parse pipe-delimited parameters from message
        parameters = [{"type": "text", "text": param.strip()} for param in message.split("|")]
        
        # Template with body parameters
        payload = {
            "messaging_product": "whatsapp",
            "to": normalized_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": "de",  # German
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": parameters
                    }
                ]
            }
        }
        
        from server.core.resilience import with_breaker, BreakerOpenError, SMS_BREAKER

        async def _do_post():
            async with httpx.AsyncClient(timeout=3.0) as client:
                return await client.post(url, json=payload, headers=headers)

        try:
            response = await with_breaker(SMS_BREAKER, _do_post())
        except BreakerOpenError:
            logger.warning("[whatsapp] breaker open — skipping send")
            return {"success": False, "method": None, "error": "breaker_open"}

        if response.status_code == 200:
            data = response.json()
            msg_id = data.get("messages", [{}])[0].get("id", "unknown")
            logger.info(f"WhatsApp template '{template_name}' sent to {phone} (msg_id: {msg_id})")
            return {"success": True, "method": "whatsapp"}
        else:
            error_text = response.text
            logger.error(f"WhatsApp template '{template_name}' failed for {phone}: HTTP {response.status_code}")
            logger.error(f"  Response body: {error_text}")
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", error_text)
                logger.error(f"  Meta API error: {error_msg}")
            except:
                pass
            return {"success": False, "method": None, "error": f"HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"WhatsApp template error for {phone}: {e}")
        return {"success": False, "method": None, "error": str(e)}


async def send_whatsapp_freeform(phone: str, message: str) -> dict:
    """
    Send via Meta WhatsApp Cloud API using free-form text messages.
    Works within 24-hour customer service window after first template message.
    For initial contact, use send_whatsapp_template() instead.
    """
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    
    if not phone_number_id or not access_token:
        logger.debug("WhatsApp not configured")
        return {"success": False, "method": None, "error": "WhatsApp not configured"}
    
    try:
        import httpx
        
        normalized_phone = phone.lstrip("+")
        url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": normalized_phone,
            "type": "text",
            "text": {"preview_url": True, "body": message},
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            logger.info(f"WhatsApp (freeform) sent to {phone}")
            return {"success": True, "method": "whatsapp"}
        else:
            error_text = response.text
            logger.warning(f"WhatsApp (freeform) failed for {phone}: {response.status_code} {error_text}")
            return {"success": False, "method": None, "error": f"HTTP {response.status_code}"}
    
    except Exception as e:
        logger.error(f"WhatsApp (freeform) error for {phone}: {e}")
        return {"success": False, "method": None, "error": str(e)}


async def send_whatsapp(phone: str, message: str) -> dict:
    """Legacy function for backward compatibility. Routes to template + freeform."""
    result = await send_whatsapp_template(phone, message, "reservation_confirmation")
    if result["success"]:
        return result
    return await send_whatsapp_freeform(phone, message)


async def send_sms(phone: str, message: str) -> dict:
    """Send via Twilio SMS."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    if not account_sid or not auth_token or not from_number:
        logger.debug("Twilio SMS not configured (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, or TWILIO_PHONE_NUMBER missing)")
        return {"success": False, "method": None, "error": "Twilio SMS not configured"}
    
    if os.getenv("SMS_DRY_RUN") == "true":
        logger.info(f"[SMS-DRY-RUN] Would send to {phone}: {message}")
        return {"success": False, "method": None, "error": "SMS_DRY_RUN mode"}
    
    try:
        from twilio.rest import Client
        
        client = Client(account_sid, auth_token)
        message_obj = await asyncio.to_thread(
            client.messages.create,
            from_=from_number,
            to=phone,
            body=message
        )
        
        logger.info(f"SMS sent to {phone} (SID: {message_obj.sid})")
        return {"success": True, "method": "sms"}
    
    except Exception as e:
        logger.error(f"SMS failed for {phone}: {e}")
        return {"success": False, "method": None, "error": str(e)}


def fire_and_forget(coro):
    """Fire off an async task in the background without blocking."""
    try:
        asyncio.create_task(coro)
    except RuntimeError:
        # No running event loop, schedule it
        logger.debug("No event loop for background task")


def format_reservation_message(
    name: str,
    date: str,
    time: str,
    party_size: int,
    restaurant_name: str = "Restaurant",  # tenant-specific fallback
    restaurant_address: Optional[str] = None,
) -> str:
    """
    Format reservation confirmation SMS / WhatsApp body.

    Fixes vs. legacy:
    - "fur" → "für" (proper UTF-8 umlaut).
    - Optional ``restaurant_address`` appended so the caller has the venue
      address in hand when they arrive.
    """
    try:
        date_obj = datetime.fromisoformat(date)
    except Exception:
        date_obj = None

    if date_obj:
        day_names = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag']
        month_names = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
        day_name = day_names[date_obj.weekday()]
        month_name = month_names[date_obj.month - 1]
        formatted_date = f"{day_name}, {date_obj.day}. {month_name}"
    else:
        formatted_date = date

    person_word = "Person" if party_size == 1 else "Personen"

    msg = (
        f"Sailly für {restaurant_name}\n"
        f"Reservierung bestätigt: {name}, {formatted_date} um {time} Uhr, "
        f"{party_size} {person_word}."
    )
    if restaurant_address:
        msg += f"\nAdresse: {restaurant_address}"
    msg += "\nBitte kommen Sie 5 Min. früher. Wir freuen uns auf Sie!"
    return msg


def format_order_message(
    order_id: str,
    order_items: str,
    order_type: str,
    total_price: float,
    delivery_address: Optional[str] = None,
    payment_link: Optional[str] = None,
    restaurant_name: str = "Restaurant",  # tenant-specific fallback
    restaurant_phone: str = "0228 3502 7000",
    delivery_fee: float = 0.00,
    estimated_minutes: Optional[int] = None,
) -> str:
    """
    Format order confirmation SMS / WhatsApp body (takeaway vs delivery).

    Fixes vs. legacy:
    - "fur" → "für" (proper UTF-8 umlaut).
    - ``estimated_minutes`` is plumbed in from the executor so each tenant's
      configured ETA shows up in the SMS (previously hard-coded to
      20 / 30–45 min).
    """
    # Sensible per-type defaults if the caller forgot to pass an ETA.
    if estimated_minutes is None:
        estimated_minutes = 20 if order_type == "takeaway" else 40

    if order_type == "takeaway":
        message = (
            f"Sailly für {restaurant_name}\n"
            f"Bestellung #{order_id}\n"
            f"Abholung ca. {estimated_minutes} Min.\n\n"
            f"{order_items}\n"
            f"Gesamt: {total_price:.2f}€"
        )
        if payment_link:
            message += f"\n\nBezahlen: {payment_link}"
        message += f"\nOder bar/Karte bei Abholung.\n\n{restaurant_phone}"
    else:
        message = (
            f"Sailly für {restaurant_name}\n"
            f"Bestellung #{order_id}\n"
            f"Lieferung ca. {estimated_minutes} Min."
        )
        if delivery_address:
            message += f"\n{delivery_address}"
        message += f"\n\n{order_items}"
        if delivery_fee > 0:
            message += f"\nLieferpauschale {delivery_fee:.2f}€"
        else:
            message += f"\nLieferung kostenlos (ab 20€ Warenwert)"
        message += f"\nGesamt: {total_price:.2f}€"
        if payment_link:
            message += f"\n\nBezahlen: {payment_link}"
        message += f"\nOder bar/Karte an der Tür.\n\n{restaurant_phone}"

    return message
