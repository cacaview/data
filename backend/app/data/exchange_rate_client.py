"""ExchangeRate-API Client.

Free, no API key required. Daily updates.
Covers all 11 ASEAN + China currencies.

API: https://open.er-api.com/v6/latest/{base}
"""
import httpx
import logging
from typing import Optional
from .cache import get_cached, set_cached

logger = logging.getLogger(__name__)

BASE_URL = "https://open.er-api.com/v6/latest"

# ASEAN + China currencies of interest
ASEAN_CURRENCIES = [
    "CNY",  # Chinese Yuan
    "VND",  # Vietnamese Dong
    "THB",  # Thai Baht
    "MYR",  # Malaysian Ringgit
    "IDR",  # Indonesian Rupiah
    "PHP",  # Philippine Peso
    "SGD",  # Singapore Dollar
    "MMK",  # Myanmar Kyat
    "KHR",  # Cambodian Riel
    "LAK",  # Lao Kip
    "BND",  # Brunei Dollar
]

# Country code to currency mapping
COUNTRY_CURRENCY = {
    "CHN": "CNY", "CN": "CNY",
    "VNM": "VND", "VN": "VND",
    "THA": "THB", "TH": "THB",
    "MYS": "MYR", "MY": "MYR",
    "IDN": "IDR", "ID": "IDR",
    "PHL": "PHP", "PH": "PHP",
    "SGP": "SGD", "SG": "SGD",
    "MMR": "MMK", "MM": "MMK",
    "KHM": "KHR", "KH": "KHR",
    "LAO": "LAK", "LA": "LAK",
    "BRN": "BND", "BN": "BND",
}


def get_latest_rates(base: str = "USD") -> dict:
    """Get latest exchange rates for all ASEAN + China currencies.

    Args:
        base: Base currency (default USD)

    Returns:
        Dict with rates, e.g. {"CNY": 7.24, "VND": 25350, ...}
    """
    cache_key = f"exchange_rate_latest_{base}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    try:
        resp = httpx.get(f"{BASE_URL}/{base}", timeout=15.0)
        resp.raise_for_status()
        data = resp.json()

        if data.get("result") != "success":
            logger.error("ExchangeRate API error: %s", data)
            return {}

        rates = data.get("rates", {})
        # Filter to ASEAN + China currencies
        filtered = {k: v for k, v in rates.items() if k in ASEAN_CURRENCIES}
        filtered["base"] = base
        filtered["time_last_update_utc"] = data.get("time_last_update_utc", "")
        filtered["time_next_update_utc"] = data.get("time_next_update_utc", "")

        set_cached(cache_key, "exchange_rate", filtered, ttl_hours=12)
        logger.info("Fetched %d exchange rates (base=%s)", len(filtered) - 3, base)
        return filtered

    except Exception as e:
        logger.error("Failed to fetch exchange rates: %s", e)
        return {}


def get_rate(from_currency: str, to_currency: str) -> Optional[float]:
    """Get a specific exchange rate.

    Args:
        from_currency: Source currency (e.g. "USD")
        to_currency: Target currency (e.g. "CNY")

    Returns:
        Exchange rate, or None if unavailable
    """
    rates = get_latest_rates(from_currency)
    return rates.get(to_currency)


def get_country_rate(country_code: str, base: str = "USD") -> Optional[float]:
    """Get exchange rate for a specific country.

    Args:
        country_code: ISO country code (e.g. "VNM", "VN")
        base: Base currency (default USD)

    Returns:
        Exchange rate, or None if unavailable
    """
    currency = COUNTRY_CURRENCY.get(country_code.upper())
    if not currency:
        logger.warning("Unknown country code for currency: %s", country_code)
        return None
    return get_rate(base, currency)


def get_rates_summary() -> dict:
    """Get a summary of all ASEAN + China rates vs USD.

    Returns:
        Dict with rate info for each country
    """
    rates = get_latest_rates("USD")
    if not rates:
        return {"error": "Unable to fetch rates"}

    summary = {}
    country_names = {
        "CNY": ("China", "中国"),
        "VND": ("Vietnam", "越南"),
        "THB": ("Thailand", "泰国"),
        "MYR": ("Malaysia", "马来西亚"),
        "IDR": ("Indonesia", "印尼"),
        "PHP": ("Philippines", "菲律宾"),
        "SGD": ("Singapore", "新加坡"),
        "MMK": ("Myanmar", "缅甸"),
        "KHR": ("Cambodia", "柬埔寨"),
        "LAK": ("Laos", "老挝"),
        "BND": ("Brunei", "文莱"),
    }

    for currency in ASEAN_CURRENCIES:
        if currency in rates:
            name_en, name_cn = country_names.get(currency, (currency, currency))
            summary[currency] = {
                "country_en": name_en,
                "country_cn": name_cn,
                "rate_vs_usd": rates[currency],
                "inverse": round(1.0 / rates[currency], 6) if rates[currency] else None,
            }

    return summary
