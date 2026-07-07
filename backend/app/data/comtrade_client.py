"""UN Comtrade API Client.

Free tier: 500 calls/day, 100,000 records per call.
Provides bilateral trade data at HS6 level, monthly and annual.

API: https://comtradeplus.un.org
Python SDK: comtradeapicall (pip install)
"""
import httpx
import logging
import os
from typing import Optional
from .cache import get_cached, set_cached

logger = logging.getLogger(__name__)

# UN Comtrade API endpoints (new v1 API, no key required for basic access)
BASE_URL = "https://comtradeapi.un.org/public/v1/preview"

# ASEAN country codes (ISO M49 used by Comtrade)
ASEAN_CODES = {
    "CHN": "156", "VNM": "704", "THA": "764", "MYS": "458",
    "IDN": "360", "PHL": "608", "SGP": "702", "MMR": "104",
    "KHM": "116", "LAO": "418", "BRN": "096",
}

ASEAN_M49 = "704,764,458,360,608,702,104,116,418,096"  # All ASEAN
CHINA_M49 = "156"

# Trade flow codes
FLOW_EXPORT = "X"  # Export
FLOW_IMPORT = "M"  # Import
FLOW_REEXPORT = "RX"
FLOW_REIMPORT = "RM"


def _build_url(flow: str, reporter: str, partner: str,
               period: str, hs_level: str = "HS6") -> str:
    """Build Comtrade API URL.

    Args:
        flow: "X" (export) or "M" (import)
        reporter: M49 country code (e.g. "156" for China)
        partner: M49 partner code or "ALL"
        period: YYYYMM or YYYY format
        hs_level: "HS6", "HS4", "HS2"

    Returns:
        Complete API URL
    """
    # Map HS level to classification code
    cmdCode = "AG6" if hs_level == "HS6" else "AG4" if hs_level == "HS4" else "AG2"

    url = (
        f"{BASE_URL}/C/M/{cmdCode}"
        f"?reporterCode={reporter}"
        f"&partnerCode={partner}"
        f"&period={period}"
        f"&flowCode={flow}"
    )
    return url


def get_bilateral_trade(reporter: str = "156", partner: str = "704",
                        flow: str = "X", period: str = "2023",
                        hs_level: str = "HS6") -> list:
    """Get bilateral trade data between two countries.

    Args:
        reporter: Reporter country M49 code (default: China)
        partner: Partner country M49 code (default: Vietnam)
        flow: "X" for export, "M" for import
        period: Time period (YYYY or YYYYMM)
        hs_level: Aggregation level

    Returns:
        List of trade records
    """
    cache_key = f"comtrade_{reporter}_{partner}_{flow}_{period}_{hs_level}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    try:
        url = _build_url(flow, reporter, partner, period, hs_level)
        logger.info("Comtrade request: R=%s P=%s F=%s P=%s", reporter, partner, flow, period)
        resp = httpx.get(url, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()

        records = data.get("data", [])
        result = []
        for r in records:
            result.append({
                "reporter_code": r.get("reporterCode"),
                "reporter_name": r.get("reporterDesc"),
                "partner_code": r.get("partnerCode"),
                "partner_name": r.get("partnerDesc"),
                "flow_code": r.get("flowCode"),
                "flow_desc": r.get("flowDesc"),
                "commodity_code": r.get("cmdCode"),
                "commodity_desc": r.get("cmdDesc"),
                "period": r.get("period"),
                "trade_value": r.get("primaryValue", 0),
                "net_weight": r.get("netWgt", 0),
                "quantity": r.get("qty", 0),
                "year": r.get("refYear"),
                "month": r.get("refMonth"),
            })

        set_cached(cache_key, "comtrade", result, ttl_hours=24)
        logger.info("Comtrade: fetched %d records", len(result))
        return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("Comtrade rate limit reached (500/day). Use cached data.")
        else:
            logger.error("Comtrade HTTP error %d: %s", e.response.status_code, e)
        return []
    except Exception as e:
        logger.error("Comtrade API error: %s", e)
        return []


def get_china_to_asean_exports(partner_m49: str, year: str = "2023") -> list:
    """Get China's exports to a specific ASEAN country.

    Args:
        partner_m49: Partner country M49 code
        year: Year

    Returns:
        List of export records at HS6 level
    """
    return get_bilateral_trade(
        reporter=CHINA_M49, partner=partner_m49,
        flow=FLOW_EXPORT, period=year, hs_level="HS6"
    )


def get_china_asean_all_exports(year: str = "2023") -> dict:
    """Get China's exports to all ASEAN countries.

    Args:
        year: Year

    Returns:
        Dict mapping country code to list of export records
    """
    result = {}
    for name, m49 in ASEAN_CODES.items():
        if name == "CHN":
            continue
        data = get_china_to_asean_exports(m49, year)
        if data:
            result[name] = data
    return result


def get_trade_summary(reporter: str = "156", partner: str = "704",
                      year: str = "2023") -> dict:
    """Get a summary of bilateral trade (total export + import).

    Returns:
        Dict with total exports, imports, trade balance
    """
    exports = get_bilateral_trade(reporter, partner, FLOW_EXPORT, year, "HS2")
    imports = get_bilateral_trade(reporter, partner, FLOW_IMPORT, year, "HS2")

    total_export = sum(r.get("trade_value", 0) for r in exports)
    total_import = sum(r.get("trade_value", 0) for r in imports)

    return {
        "reporter": reporter,
        "partner": partner,
        "year": year,
        "total_export_usd": total_export,
        "total_import_usd": total_import,
        "trade_balance": total_export - total_import,
        "top_exports": sorted(exports, key=lambda x: x.get("trade_value", 0), reverse=True)[:10],
        "top_imports": sorted(imports, key=lambda x: x.get("trade_value", 0), reverse=True)[:10],
    }


def get_monthly_trend(reporter: str = "156", partner: str = "704",
                      flow: str = "X", year: str = "2023") -> list:
    """Get monthly trade trend for a specific year.

    Returns:
        List of monthly trade values
    """
    # Build period string for all months
    periods = ",".join(f"{year}{m:02d}" for m in range(1, 13))
    return get_bilateral_trade(reporter, partner, flow, periods, "AG2")
