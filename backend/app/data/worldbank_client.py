"""World Bank Open Data API Client.

Completely free, no API key required.
Provides GDP, population, FDI, trade ratios, and other macro indicators.

API: https://api.worldbank.org/v2/
"""
import httpx
import logging
from typing import Optional
from .cache import get_cached, set_cached

logger = logging.getLogger(__name__)

BASE_URL = "https://api.worldbank.org/v2"

# ASEAN + China country codes (ISO 3166-1 alpha-2 for World Bank API)
ASEAN_CHINA_CODES = "CN;VN;TH;MY;ID;PH;SG;MM;KH;LA;BN"

# ISO alpha-3 to alpha-2 mapping for World Bank
COUNTRY_ALPHA3_TO_2 = {
    "CHN": "CN", "VNM": "VN", "THA": "TH", "MYS": "MY",
    "IDN": "ID", "PHL": "PH", "SGP": "SG", "MMR": "MM",
    "KHM": "KH", "LAO": "LA", "BRN": "BN",
}

# Key World Bank indicators
INDICATORS = {
    "NY.GDP.MKTP.CD": {"name_en": "GDP (current US$)", "name_cn": "GDP（现价美元）"},
    "NY.GDP.MKTP.KD.ZG": {"name_en": "GDP growth (annual %)", "name_cn": "GDP增长率"},
    "SP.POP.TOTL": {"name_en": "Population, total", "name_cn": "总人口"},
    "BX.KLT.DINV.CD.WD": {"name_en": "FDI, net inflows", "name_cn": "FDI净流入"},
    "NE.TRD.GNFS.ZS": {"name_en": "Trade (% of GDP)", "name_cn": "贸易占GDP百分比"},
    "NE.EXP.GNFS.CD": {"name_en": "Exports of goods and services", "name_cn": "出口额"},
    "NE.IMP.GNFS.CD": {"name_en": "Imports of goods and services", "name_cn": "进口额"},
    "FP.CPI.TOTL.ZG": {"name_en": "Inflation, consumer prices", "name_cn": "通胀率"},
    "NY.GDP.PCAP.CD": {"name_en": "GDP per capita (current US$)", "name_cn": "人均GDP"},
}


def _fetch_indicator(indicator: str, countries: str = ASEAN_CHINA_CODES,
                     date_range: str = "2015:2025") -> list:
    """Fetch a single indicator for multiple countries.

    Args:
        indicator: World Bank indicator code
        countries: Semicolon-separated country codes
        date_range: Year range (e.g. "2015:2025")

    Returns:
        List of data points, each as dict
    """
    cache_key = f"wb_{indicator}_{countries}_{date_range}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    try:
        url = f"{BASE_URL}/country/{countries}/indicator/{indicator}"
        params = {"date": date_range, "format": "json", "per_page": 500}
        resp = httpx.get(url, params=params, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, list) or len(data) < 2:
            logger.warning("World Bank returned unexpected format for %s", indicator)
            return []

        records = data[1]  # First element is metadata, second is data
        if not records:
            return []

        result = []
        for r in records:
            if r.get("value") is not None:
                result.append({
                    "country_id": r["country"]["id"],
                    "country_name": r["country"]["value"],
                    "indicator_id": r["indicator"]["id"],
                    "indicator_name": r["indicator"]["value"],
                    "date": r["date"],
                    "value": r["value"],
                })

        set_cached(cache_key, "worldbank", result, ttl_hours=48)
        logger.info("World Bank: fetched %d records for %s", len(result), indicator)
        return result

    except Exception as e:
        logger.error("World Bank API error for %s: %s", indicator, e)
        return []


def get_macro_indicators(date_range: str = "2015:2025") -> dict:
    """Get all key macroeconomic indicators for ASEAN + China.

    Args:
        date_range: Year range

    Returns:
        Dict keyed by indicator code, each containing list of data points
    """
    result = {}
    for indicator_code in INDICATORS:
        data = _fetch_indicator(indicator_code, date_range=date_range)
        if data:
            result[indicator_code] = data
    return result


def get_gdp_data(date_range: str = "2015:2025") -> list:
    """Get GDP data for ASEAN + China.

    Returns:
        List of GDP data points
    """
    return _fetch_indicator("NY.GDP.MKTP.CD", date_range=date_range)


def get_trade_ratio(date_range: str = "2015:2025") -> list:
    """Get trade-to-GDP ratio for ASEAN + China.

    Returns:
        List of trade ratio data points
    """
    return _fetch_indicator("NE.TRD.GNFS.ZS", date_range=date_range)


def get_fdi_data(date_range: str = "2015:2025") -> list:
    """Get FDI net inflows for ASEAN + China.

    Returns:
        List of FDI data points
    """
    return _fetch_indicator("BX.KLT.DINV.CD.WD", date_range=date_range)


def get_country_profile(country_code: str, date_range: str = "2015:2025") -> dict:
    """Get comprehensive macro profile for a single country.

    Args:
        country_code: ISO alpha-3 code (e.g. "VNM")
        date_range: Year range

    Returns:
        Dict with all indicators for this country
    """
    alpha2 = COUNTRY_ALPHA3_TO_2.get(country_code.upper(), country_code.upper())
    result = {}
    for indicator_code, info in INDICATORS.items():
        data = _fetch_indicator(indicator_code, countries=alpha2, date_range=date_range)
        if data:
            result[indicator_code] = {
                "info": info,
                "data": data,
            }
    return result


def get_indicator_latest(indicator: str, countries: str = ASEAN_CHINA_CODES) -> dict:
    """Get the latest available value for an indicator per country.

    Args:
        indicator: World Bank indicator code
        countries: Semicolon-separated country codes

    Returns:
        Dict mapping country code to latest value
    """
    data = _fetch_indicator(indicator, countries)
    latest = {}
    for point in data:
        cid = point["country_id"]
        year = point["date"]
        if cid not in latest or year > latest[cid]["date"]:
            latest[cid] = point
    return {k: v["value"] for k, v in latest.items()}
