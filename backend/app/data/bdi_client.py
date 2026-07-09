"""Baltic Dry Index (BDI) Client.

Fetches the Baltic Dry Index - a benchmark for global shipping costs.
BDI tracks spot rates for Capesize, Panamax, and Supramax dry bulk vessels.
Rising BDI = increasing demand for shipping = growing trade activity.

API: Uses oilpriceapi.com free tier (no key needed for basic).
Fallback: Uses mock data based on historical BDI patterns.
"""
import httpx
import logging
import math
import random
from datetime import datetime, timezone
from typing import Optional
from .cache import get_cached, set_cached

logger = logging.getLogger(__name__)

BASE_URL = "https://api.oilpriceapi.com/v1"
BDI_FALLBACK_URL = "https://balticexchange.com/api/bdi"

# BDI vessel size categories
VESSEL_CATEGORIES = {
    "capesize": {
        "name_en": "Capesize",
        "weight_range": (100000, 200000),
        "description": "Largest dry bulk vessels, iron ore and coal",
    },
    "panamax": {
        "name_en": "Panamax",
        "weight_range": (60000, 80000),
        "description": "Mid-size vessels, grain and minor bulks",
    },
    "supramax": {
        "name_en": "Supramax",
        "weight_range": (45000, 60000),
        "description": "Smaller versatile vessels, steel and cement",
    },
    "handysize": {
        "name_en": "Handysize",
        "weight_range": (10000, 35000),
        "description": "Small bulk carriers, short-sea routes",
    },
}

# Major shipping routes with base rates (USD per ton, approximate)
SHIPPING_ROUTES = {
    ("CN_CNSHA", "BR_BRSSZ"): {"name": "China-Brazil", "base_rate": 28.0, "distance_nm": 10500},
    ("CN_CNSHA", "AU_AUMEL"): {"name": "China-Australia", "base_rate": 14.0, "distance_nm": 4800},
    ("CN_CNSHA", "US_USLAX"): {"name": "China-US West Coast", "base_rate": 22.0, "distance_nm": 6200},
    ("CN_CNSHA", "RU_RULED"): {"name": "China-Russia", "base_rate": 18.0, "distance_nm": 5500},
    ("CN_CNSHA", "ID_IDJKT"): {"name": "China-Indonesia", "base_rate": 10.0, "distance_nm": 2500},
    ("CN_CNSHA", "IN_INMUM"): {"name": "China-India", "base_rate": 16.0, "distance_nm": 4200},
    ("CN_CNSHA", "JP_JPTYO"): {"name": "China-Japan", "base_rate": 6.0, "distance_nm": 1100},
    ("VN_VNSGN", "US_USLAX"): {"name": "Vietnam-US", "base_rate": 25.0, "distance_nm": 7800},
    ("TH_THBKK", "EU_DEHAM"): {"name": "Thailand-EU", "base_rate": 30.0, "distance_nm": 8500},
    ("SG_SGSIN", "ZA_ZADUR"): {"name": "Singapore-South Africa", "base_rate": 20.0, "distance_nm": 6000},
}

# Origin/destination name aliases
LOCATION_ALIASES = {
    "china": "CN_CNSHA", "shanghai": "CN_CNSHA", "guangzhou": "CN_CNGZG",
    "shenzhen": "CN_CNSZX", "tianjin": "CN_CNTSN",
    "vietnam": "VN_VNSGN", "ho chi minh": "VN_VNSGN",
    "thailand": "TH_THBKK", "bangkok": "TH_THBKK",
    "indonesia": "ID_IDJKT", "jakarta": "ID_IDJKT",
    "malaysia": "MY_MYKUL", "kuala lumpur": "MY_MYKUL",
    "philippines": "PH_MNPHT", "manila": "PH_MNPHT",
    "singapore": "SG_SGSIN",
    "japan": "JP_JPTYO", "tokyo": "JP_JPTYO",
    "south korea": "KR_KRPUS", "busan": "KR_KRPUS",
    "india": "IN_INMUM", "mumbai": "IN_INMUM",
    "usa": "US_USLAX", "us": "US_USLAX", "los angeles": "US_USLAX",
    "europe": "EU_DEHAM", "germany": "EU_DEHAM", "hamburg": "EU_DEHAM",
    "brazil": "BR_BRSSZ", "santos": "BR_BRSSZ",
    "australia": "AU_AUMEL", "melbourne": "AU_AUMEL",
    "russia": "RU_RULED", "st petersburg": "RU_RULED",
    "south africa": "ZA_ZADUR", "durban": "ZA_ZADUR",
}


def _generate_mock_bdi_history(months: int = 24) -> list:
    """Generate realistic mock BDI monthly history data.

    Uses a sine-wave pattern with noise to simulate typical BDI volatility.
    BDI historically ranges from ~500 to ~3500.

    Args:
        months: Number of months of history to generate

    Returns:
        List of dicts with date, value, and vessel category breakdown
    """
    random.seed(42)  # Reproducible mock data
    now = datetime.now(timezone.utc)
    history = []

    # Base pattern: oscillating between 800 and 2500 with seasonal trends
    base_amplitude = 850.0
    base_offset = 1650.0
    period = 18.0  # ~18-month cycle typical of BDI

    for i in range(months, 0, -1):
        month_dt = now.replace(day=1)
        month_offset = i
        t = months - month_offset

        # Sine wave for cyclical pattern
        cycle = base_amplitude * math.sin(2 * math.pi * t / period)

        # Seasonal adjustment (shipping tends to be higher Q4-Q1)
        month_num = (now.month - month_offset) % 12 + 1
        seasonal = 150.0 * math.sin(2 * math.pi * (month_num - 3) / 12)

        # Random noise
        noise = random.gauss(0, 120)

        bdi_value = max(400, min(3800, int(base_offset + cycle + seasonal + noise)))

        # Break down by vessel category (proportional to typical market)
        capesize_weight = 0.45 + random.uniform(-0.05, 0.05)
        panamax_weight = 0.30 + random.uniform(-0.05, 0.05)
        supramax_weight = 1.0 - capesize_weight - panamax_weight

        year = (now.month - month_offset - 1) // 12
        month = (now.month - month_offset - 1) % 12 + 1
        date_str = f"{now.year + year}-{month:02d}"

        history.append({
            "date": date_str,
            "bdi_value": bdi_value,
            "capesize_index": int(bdi_value * capesize_weight * 2.2),
            "panamax_index": int(bdi_value * panamax_weight * 1.8),
            "supramax_index": int(bdi_value * supramax_weight * 1.5),
            "source": "mock",
        })

    return sorted(history, key=lambda x: x["date"])


def _resolve_location(name: str) -> Optional[str]:
    """Resolve a location name to a route key.

    Args:
        name: Location name or code (e.g. "china", "shanghai", "CN_CNSHA")

    Returns:
        Route key string, or None if not found
    """
    name_lower = name.lower().strip()
    if name_lower in LOCATION_ALIASES:
        return LOCATION_ALIASES[name_lower]
    # Check if it's already a route key
    upper = name.upper().strip()
    for key in LOCATION_ALIASES.values():
        if key == upper:
            return upper
    return None


def get_bdi_current() -> dict:
    """Get current BDI value with trend information.

    Returns:
        Dict with current BDI, change, trend, and vessel breakdown.
        Example: {
            "bdi_value": 1856,
            "change_pct": 2.3,
            "trend": "up",
            "vessel_indices": {...},
            "updated_at": "2024-01-15",
            "source": "api" | "mock"
        }
    """
    cache_key = "bdi_current"
    cached = get_cached(cache_key)
    if cached:
        return cached

    # Try fetching from API
    try:
        resp = httpx.get(f"{BASE_URL}/bdi", timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            result = {
                "bdi_value": data.get("data", {}).get("value", 0),
                "change_pct": data.get("data", {}).get("change_pct", 0),
                "trend": data.get("data", {}).get("trend", "unknown"),
                "updated_at": data.get("data", {}).get("date", ""),
                "source": "api",
            }
            set_cached(cache_key, "bdi", result, ttl_hours=6)
            logger.info("BDI current: %d (source=api)", result["bdi_value"])
            return result
    except Exception as e:
        logger.warning("BDI API unavailable, using mock data: %s", e)

    # Fallback to mock data based on recent history
    history = _generate_mock_bdi_history(3)
    if history:
        latest = history[-1]
        prev = history[-2] if len(history) > 1 else latest
        change = ((latest["bdi_value"] - prev["bdi_value"]) / prev["bdi_value"]) * 100
        trend = "up" if change > 0.5 else ("down" if change < -0.5 else "stable")
    else:
        latest = {"bdi_value": 1650, "capesize_index": 1630, "panamax_index": 890, "supramax_index": 410}
        change = 0.0
        trend = "stable"

    result = {
        "bdi_value": latest["bdi_value"],
        "change_pct": round(change, 1),
        "trend": trend,
        "vessel_indices": {
            "capesize": latest.get("capesize_index", 0),
            "panamax": latest.get("panamax_index", 0),
            "supramax": latest.get("supramax_index", 0),
        },
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "mock",
    }
    set_cached(cache_key, "bdi", result, ttl_hours=6)
    logger.info("BDI current: %d (source=mock)", result["bdi_value"])
    return result


def get_bdi_history(months: int = 24) -> list:
    """Get historical BDI monthly values.

    Args:
        months: Number of months of history (default 24)

    Returns:
        List of dicts with monthly BDI data, sorted by date ascending.
        Example: [{"date": "2023-01", "bdi_value": 1200, "source": "mock"}, ...]
    """
    cache_key = f"bdi_history_{months}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    try:
        resp = httpx.get(f"{BASE_URL}/bdi/history", params={"months": months}, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            records = data.get("data", [])
            result = [{"date": r["date"], "bdi_value": r["value"], "source": "api"} for r in records]
            set_cached(cache_key, "bdi", result, ttl_hours=12)
            logger.info("BDI history: fetched %d months (source=api)", len(result))
            return result
    except Exception as e:
        logger.warning("BDI history API unavailable, using mock data: %s", e)

    result = _generate_mock_bdi_history(months)
    set_cached(cache_key, "bdi", result, ttl_hours=12)
    logger.info("BDI history: generated %d months (source=mock)", len(result))
    return result


def get_shipping_cost_estimate(origin: str, destination: str, weight_tons: float) -> dict:
    """Estimate shipping cost between two ports based on BDI and route data.

    Args:
        origin: Origin port name or code (e.g. "shanghai", "CN_CNSHA")
        destination: Destination port name or code (e.g. "los angeles", "US_USLAX")
        weight_tons: Cargo weight in metric tons

    Returns:
        Dict with cost estimate, route info, and BDI context.
        Example: {
            "origin": "Shanghai",
            "destination": "Los Angeles",
            "weight_tons": 5000,
            "estimated_cost_usd": 110000,
            "cost_per_ton": 22.0,
            "route": "China-US West Coast",
            "distance_nm": 6200,
            "bdi_at_time": 1856,
            "vessel_recommendation": "panamax",
            "estimated_days": 14,
            "source": "mock"
        }
    """
    cache_key = f"bdi_shipping_{origin}_{destination}_{weight_tons}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    origin_key = _resolve_location(origin)
    dest_key = _resolve_location(destination)

    if not origin_key or not dest_key:
        logger.warning("Unknown location: origin=%s dest=%s", origin, destination)
        return {"error": f"Unknown location: origin='{origin}' or destination='{destination}'"}

    route_key = (origin_key, dest_key)
    reverse_key = (dest_key, origin_key)
    route_info = SHIPPING_ROUTES.get(route_key) or SHIPPING_ROUTES.get(reverse_key)

    # Get current BDI for cost scaling
    current_bdi = get_bdi_current()
    bdi_value = current_bdi.get("bdi_value", 1650)
    bdi_scale = bdi_value / 1650.0  # Normalize to baseline

    if route_info:
        base_rate = route_info["base_rate"]
        distance = route_info["distance_nm"]
        route_name = route_info["name"]
    else:
        # Estimate rate based on rough distance
        logger.info("No direct route found for %s -> %s, estimating", origin, destination)
        base_rate = 18.0  # Average rate
        distance = 5000  # Average distance
        route_name = f"{origin}-{destination} (estimated)"

    # Scale rate by current BDI
    adjusted_rate = base_rate * bdi_scale
    total_cost = adjusted_rate * weight_tons

    # Select appropriate vessel size
    if weight_tons > 80000:
        vessel = "capesize"
    elif weight_tons > 50000:
        vessel = "panamax"
    elif weight_tons > 30000:
        vessel = "supramax"
    else:
        vessel = "handysize"

    # Estimate transit time (average 15 knots for bulk carriers)
    estimated_days = max(2, int(distance / (15 * 24)))

    result = {
        "origin": origin,
        "destination": destination,
        "weight_tons": weight_tons,
        "estimated_cost_usd": round(total_cost, 2),
        "cost_per_ton": round(adjusted_rate, 2),
        "route": route_name,
        "distance_nm": distance,
        "bdi_at_time": bdi_value,
        "bdi_trend": current_bdi.get("trend", "stable"),
        "vessel_recommendation": vessel,
        "estimated_days": estimated_days,
        "source": "mock" if current_bdi.get("source") == "mock" else "api",
    }

    set_cached(cache_key, "bdi", result, ttl_hours=6)
    logger.info(
        "Shipping estimate: %s -> %s, %d tons = $%s",
        origin, destination, weight_tons, f"{total_cost:,.0f}",
    )
    return result
