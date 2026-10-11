"""
USD <-> KES conversion with a 24-hour file cache.

Uses https://www.exchangerate-api.com via the EXCHANGE_RATE_API_KEY setting.
Falls back to EXCHANGE_RATE_FALLBACK_KES_PER_USD if the API is unavailable or
not configured.
"""

import json
import logging
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

CACHE_DIR = Path(settings.PROJECT_ROOT) / ".cache"
CACHE_FILE = CACHE_DIR / "exchange_rate.json"
CACHE_TTL_SECONDS = 60 * 60 * 24


def _fallback_rate() -> Decimal:
    rate = Decimal(str(settings.EXCHANGE_RATE_FALLBACK_KES_PER_USD))
    if not rate.is_finite() or rate <= 0:
        raise ValueError("The fallback KES-per-USD rate must be a positive number.")
    return rate


def _read_cache() -> Optional[Decimal]:
    if not CACHE_FILE.exists():
        return None
    try:
        with CACHE_FILE.open("r", encoding="utf-8") as cache_file:
            data = json.load(cache_file)
    except (OSError, json.JSONDecodeError):
        logger.warning("Could not read exchange-rate cache at %s.", CACHE_FILE)
        return None

    if not isinstance(data, dict):
        return None

    timestamp = data.get("timestamp")
    rate_value = data.get("kes_per_usd")
    if (
        not isinstance(timestamp, (int, float))
        or isinstance(timestamp, bool)
        or not isinstance(rate_value, (int, float, str))
    ):
        return None

    if time.time() - timestamp > CACHE_TTL_SECONDS:
        return None

    try:
        rate = Decimal(str(rate_value))
    except (InvalidOperation, TypeError, ValueError):
        return None

    if not rate.is_finite() or rate <= 0:
        return None
    return rate


def _write_cache(rate: Decimal) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with CACHE_FILE.open("w", encoding="utf-8") as cache_file:
            json.dump(
                {"timestamp": time.time(), "kes_per_usd": str(rate)},
                cache_file,
            )
    except OSError:
        logger.warning(
            "Could not write exchange-rate cache at %s.",
            CACHE_FILE,
            exc_info=True,
        )


def _fetch_live_rate() -> Optional[Decimal]:
    api_key = getattr(settings, "EXCHANGE_RATE_API_KEY", "") or ""
    if not api_key:
        return None

    url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/USD/KES"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        logger.warning("Could not fetch the live USD/KES exchange rate.")
        return None

    if not isinstance(payload, dict) or payload.get("result") != "success":
        return None

    try:
        rate = Decimal(str(payload["conversion_rate"]))
    except (KeyError, InvalidOperation, TypeError, ValueError):
        return None

    if not rate.is_finite() or rate <= 0:
        return None
    return rate


def get_kes_per_usd() -> Decimal:
    """Return the current USD -> KES exchange rate, preferring cache, API, fallback."""
    cached_rate = _read_cache()
    if cached_rate is not None:
        return cached_rate

    live_rate = _fetch_live_rate()
    if live_rate is not None:
        _write_cache(live_rate)
        return live_rate

    logger.warning("Using configured fallback USD/KES exchange rate.")
    return _fallback_rate()


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def usd_to_kes(amount_usd) -> Decimal:
    amount = Decimal(str(amount_usd))
    return _q2(amount * get_kes_per_usd())


def kes_to_usd(amount_kes) -> Decimal:
    amount = Decimal(str(amount_kes))
    return _q2(amount / get_kes_per_usd())


def format_price(amount_usd, currency: str = "USD") -> str:
    """Format a USD amount in USD or KES."""
    currency = (currency or "USD").upper()
    if currency == "KES":
        return f"KSh {usd_to_kes(amount_usd):,.2f}"
    return f"${_q2(Decimal(str(amount_usd))):,.2f}"
