"""
PayHero v2 Developer API client.

Auth: HTTP Basic Auth (base64-encoded username:password), sent as
      Authorization: Basic <token>
Endpoint: POST /api/v2/payments/initiate-stk-push
Payload: amount, phone_number, channel_id, provider, external_reference

Public API:
    client = PayHeroClient()
    resp = client.stk_push(
        amount_kes=Decimal("3500"),
        phone="254712345678",
        reference="INV-2026-0001",
    )
"""

import logging
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PayHeroError(Exception):
    """Raised for configuration or transport problems."""


class PayHeroClient:
    def __init__(self):
        self.api_url = getattr(settings, "PAYHERO_API_URL", "") or ""
        self.auth_token = getattr(settings, "PAYHERO_AUTH_TOKEN", "") or ""
        self.channel_id = getattr(settings, "PAYHERO_CHANNEL_ID", "") or ""

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """
        Normalize Kenyan phone numbers to 2547XXXXXXXX / 2541XXXXXXXX.
        """
        digits = "".join(ch for ch in str(phone) if ch.isdigit())

        if digits.startswith("254") and len(digits) == 12:
            return digits
        if digits.startswith("0") and len(digits) == 10:
            return "254" + digits[1:]
        if len(digits) == 9:
            return "254" + digits
        if digits.startswith("254") and len(digits) > 12:
            return digits[:12]
        return digits

    def stk_push(
        self,
        amount_kes,
        phone: str,
        reference: str,
        description: str = "",
    ) -> dict:
        """
        Initiate an STK push via the v2 Developer API.

        Returns a dict: {"success": bool, "raw": <server response>, "error": str}
        Never raises for HTTP/transport errors — always returns a dict.
        """
        amount = int(Decimal(str(amount_kes)).quantize(Decimal("1")))

        if amount <= 0:
            return {"success": False, "error": "Amount must be greater than zero"}

        if not self.auth_token:
            return {"success": False, "error": "PAYHERO_AUTH_TOKEN is not configured"}
        if not self.channel_id:
            return {"success": False, "error": "PAYHERO_CHANNEL_ID is not configured"}

        phone = self.normalize_phone(phone)
        if len(phone) != 12:
            return {"success": False, "error": f"Invalid phone number format: {phone}"}

        auth_token = self.auth_token.strip()
        headers = {
            "Authorization": (
                auth_token
                if auth_token.lower().startswith("basic ")
                else f"Basic {auth_token}"
            ),
            "Content-Type": "application/json",
        }

        payload = {
            "amount": amount,
            "phone_number": phone,
            "channel_id": self.channel_id,
            "provider": "m-pesa",
            "external_reference": reference,
        }

        try:
            resp = requests.post(
                self.api_url, json=payload, headers=headers, timeout=15
            )
        except requests.RequestException as e:
            logger.exception("PayHero v2 STK push transport error")
            return {"success": False, "error": f"Network error: {e}"}

        try:
            body = resp.json()
        except ValueError:
            body = {"raw_text": resp.text}

        # v2 success responses look like:
        # {"success": true, "status": "QUEUED", "reference": "...", ...}
        success = (
            resp.status_code in (200, 201)
            and isinstance(body, dict)
            and (
                body.get("success") is True
                or str(body.get("status", "")).upper() in {"QUEUED", "SUCCESS", "OK"}
            )
        )

        return {
            "success": success,
            "raw": body,
            "http_status": resp.status_code,
            "reference": reference,
            "phone": phone,
            "amount": amount,
            "error": None if success else (
                (body.get("message") if isinstance(body, dict) else None)
                or (body.get("detail") if isinstance(body, dict) else None)
                or f"HTTP {resp.status_code}"
            ),
        }
