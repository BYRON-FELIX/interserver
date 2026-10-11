"""
Minimal PayHero (legacy Swift Payment API) client.

Auth: HTTP Basic Auth with PAYHERO_USERNAME / PAYHERO_PASSWORD from settings.
"""

import base64
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PayHeroError(Exception):
    """Raised for PayHero configuration problems."""


class PayHeroClient:
    def __init__(self):
        self.username = getattr(settings, "PAYHERO_USERNAME", "") or ""
        self.password = getattr(settings, "PAYHERO_PASSWORD", "") or ""
        self.account_id = getattr(settings, "PAYHERO_ACCOUNT_ID", "") or ""
        self.stk_url = getattr(
            settings,
            "PAYHERO_STK_URL",
            "https://payherokenya.com/sps/portal/app/stk.php",
        )

    def _basic_auth_header(self) -> str:
        if not self.username or not self.password:
            raise PayHeroError(
                "PAYHERO_USERNAME / PAYHERO_PASSWORD are not configured in .env"
            )
        token = base64.b64encode(
            f"{self.username}:{self.password}".encode("utf-8")
        ).decode("ascii")
        return f"Basic {token}"

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize common Kenyan phone formats to 2547XXXXXXXX / 2541XXXXXXXX."""
        digits = "".join(character for character in str(phone) if character.isdigit())

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
        amount_kes: Decimal,
        phone: str,
        reference: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Initiate an STK push and return the provider response in a dict."""
        try:
            amount = Decimal(str(amount_kes))
            if not amount.is_finite():
                raise InvalidOperation
            amount = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError):
            return {
                "success": False,
                "error": "Amount must be a valid number greater than zero",
                "reference": reference,
            }

        if amount <= 0:
            return {
                "success": False,
                "error": "Amount must be greater than zero",
                "reference": reference,
            }

        if not self.account_id:
            return {
                "success": False,
                "error": "PAYHERO_ACCOUNT_ID is not configured in .env",
                "reference": reference,
            }

        normalized_phone = self.normalize_phone(phone)
        if len(normalized_phone) != 12:
            return {
                "success": False,
                "error": f"Invalid phone number format: {normalized_phone}",
                "reference": reference,
            }

        try:
            headers = {
                "Authorization": self._basic_auth_header(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        except PayHeroError as error:
            return {
                "success": False,
                "error": str(error),
                "reference": reference,
            }

        payload = {
            "account_id": self.account_id,
            "amount": int(amount),
            "phone": normalized_phone,
            "reference": reference,
            "description": description or reference,
        }

        try:
            response = requests.post(
                self.stk_url,
                json=payload,
                headers=headers,
                timeout=15,
            )
        except requests.RequestException as error:
            logger.exception("PayHero STK push transport error")
            return {
                "success": False,
                "error": f"Network error: {error}",
                "reference": reference,
                "phone": normalized_phone,
                "amount": int(amount),
            }

        try:
            body = response.json()
        except ValueError:
            body = {"raw_text": response.text}

        top_status = body.get("status") if isinstance(body, dict) else None
        inner = body.get("response", {}) if isinstance(body, dict) else {}
        inner_status = (
            str(inner.get("Status", "")).lower()
            if isinstance(inner, dict)
            else ""
        )

        success = (
            response.status_code == 200
            and isinstance(body, dict)
            and (
                top_status is True
                or str(top_status).lower() in {"success", "ok", "200"}
                or inner_status in {"success", "ok"}
            )
        )

        error_message = None if success else (
            (inner.get("Message") if isinstance(inner, dict) else None)
            or (body.get("message") if isinstance(body, dict) else None)
            or f"HTTP {response.status_code}"
        )

        return {
            "success": success,
            "raw": body,
            "http_status": response.status_code,
            "reference": reference,
            "phone": normalized_phone,
            "amount": int(amount),
            "error": error_message,
        }
