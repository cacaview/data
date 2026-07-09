"""China National Bureau of Statistics Client.

Fetches macroeconomic data from data.stats.gov.cn.
GDP, CPI, PMI, employment, FDI indicators.
No API key required - public REST API.

API: https://data.stats.gov.cn/easyquery.htm
"""
import httpx
import logging
import math
import random
from datetime import datetime, timezone
from typing import Optional
from .cache import get_cached, set_cached

logger = logging.getLogger(__name__)

BASE_URL = "https://data.stats.gov.cn/easyquery.htm"

# NBS indicator tree codes (m=A01 is national accounts root)
# These are the DBcode + sj (time dimension) codes for the NBS API
NBS_INDICATORS = {
    "gdp": {
        "dbcode": "hgnd", "rowcode": "zb", "wds": [],
        "dfwds": [{"wdcode": "zb", "valuecode": "A0201"}],
        "name_en": "GDP", "name_cn": "国内生产总值",
    },
    "gdp_quarterly": {
        "dbcode": "hgjd", "rowcode": "zb", "wds": [],
        "dfwds": [{"wdcode": "zb", "valuecode": "A0101"}],
        "name_en": "GDP Quarterly", "name_cn": "季度GDP",
    },
    "cpi": {
        "dbcode": "hgnd", "rowcode": "zb", "wds": [],
        "dfwds": [{"wdcode": "zb", "valuecode": "A0101"}],
        "name_en": "CPI", "name_cn": "居民消费价格指数",
    },
    "pmi": {
        "dbcode": "hgnd", "rowcode": "zb", "wds": [],
        "dfwds": [{"wdcode": "zb", "valuecode": "A0B01"}],
        "name_en": "PMI", "name_cn": "采购经理指数",
    },
    "employment": {
        "dbcode": "hgnd", "rowcode": "zb", "wds": [],
        "dfwds": [{"wdcode": "zb", "valuecode": "A0301"}],
        "name_en": "Employment", "name_cn": "就业",
    },
    "fdi": {
        "dbcode": "hgnd", "rowcode": "zb", "wds": [],
        "dfwds": [{"wdcode": "zb", "valuecode": "A0601"}],
        "name_en": "FDI", "name_cn": "外商直接投资",
    },
}

# ASEAN + China country codes for the macro overview
COUNTRY_MACRO = {
    "CHN": {"name_en": "China", "name_cn": "中国"},
    "VNM": {"name_en": "Vietnam", "name_cn": "越南"},
    "THA": {"name_en": "Thailand", "name_cn": "泰国"},
    "MYS": {"name_en": "Malaysia", "name_cn": "马来西亚"},
    "IDN": {"name_en": "Indonesia", "name_cn": "印尼"},
    "PHL": {"name_en": "Philippines", "name_cn": "菲律宾"},
    "SGP": {"name_en": "Singapore", "name_cn": "新加坡"},
    "MMR": {"name_en": "Myanmar", "name_cn": "缅甸"},
    "KHM": {"name_en": "Cambodia", "name_cn": "柬埔寨"},
    "LAO": {"name_en": "Laos", "name_cn": "老挝"},
    "BRN": {"name_en": "Brunei", "name_cn": "文莱"},
}


def _fetch_nbs_indicator(indicator_key: str, start_year: int, end_year: int) -> list:
    """Fetch a single indicator from the NBS API.

    Args:
        indicator_key: Key in NBS_INDICATORS dict
        start_year: Start year
        end_year: End year

    Returns:
        List of data points, or empty list on failure
    """
    cache_key = f"stats_gov_{indicator_key}_{start_year}_{end_year}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    ind_info = NBS_INDICATORS.get(indicator_key)
    if not ind_info:
        logger.error("Unknown NBS indicator: %s", indicator_key)
        return []

    try:
        # Build time dimension query
        periods = ",".join(str(y) for y in range(start_year, end_year + 1))
        dfwds = ind_info["dfwds"] + [{"wdcode": "sj", "valuecode": periods}]

        params = {
            "m": "QueryData",
            "dbcode": ind_info["dbcode"],
            "rowcode": ind_info["rowcode"],
            "colcode": "sj",
            "wds": "[]",
            "dfwds": str(dfwds).replace("'", '"'),
        }

        resp = httpx.get(BASE_URL, params=params, timeout=20.0)
        resp.raise_for_status()
        data = resp.json()

        if data.get("returncode") != 200:
            logger.warning("NBS API error for %s: %s", indicator_key, data.get("returncode"))
            return []

        records = data.get("returndata", {}).get("datanodes", [])
        result = []
        for r in records:
            wds = r.get("wds", [])
            code = r.get("code", "")
            value = r.get("data", {}).get("data", None)
            period = ""
            for wd in wds:
                if wd.get("wdcode") == "sj":
                    period = wd.get("valuecode", "")

            if value is not None:
                result.append({
                    "indicator": indicator_key,
                    "indicator_en": ind_info["name_en"],
                    "indicator_cn": ind_info["name_cn"],
                    "period": period,
                    "value": value,
                    "source": "api",
                })

        set_cached(cache_key, "stats_gov", result, ttl_hours=24)
        logger.info("NBS %s: fetched %d data points", indicator_key, len(result))
        return result

    except Exception as e:
        logger.warning("NBS API unavailable for %s, using mock: %s", indicator_key, e)
        return []


def _generate_mock_gdp(start_year: int, end_year: int) -> list:
    """Generate mock GDP quarterly data.

    Args:
        start_year: Start year
        end_year: End year

    Returns:
        List of quarterly GDP data points
    """
    random.seed(start_year * 10 + end_year)
    # China GDP base ~125 trillion CNY (2023), growing ~5% annually
    base_gdp = 125000.0  # billions CNY
    result = []

    for year in range(start_year, end_year + 1):
        year_factor = 1.0 + 0.05 * (year - 2023)
        # Q4 > Q1 seasonally (typical China pattern)
        quarterly_weights = [0.22, 0.24, 0.26, 0.28]

        for q in range(1, 5):
            gdp = base_gdp * year_factor * quarterly_weights[q - 1]
            gdp += random.gauss(0, gdp * 0.03)
            growth = 5.0 + random.gauss(0, 0.8)

            result.append({
                "indicator": "gdp",
                "indicator_en": "GDP",
                "indicator_cn": "国内生产总值",
                "period": f"{year}Q{q}",
                "value": round(gdp, 2),
                "unit": "billion_cny",
                "growth_yoy_pct": round(growth, 1),
                "source": "mock",
            })

    return result


def _generate_mock_cpi(start_year: int, end_year: int) -> list:
    """Generate mock CPI monthly data.

    Args:
        start_year: Start year
        end_year: End year

    Returns:
        List of monthly CPI data points
    """
    random.seed(start_year * 100 + end_year)
    result = []

    for year in range(start_year, end_year + 1):
        now = datetime.now(timezone.utc)
        max_month = 12
        if year == now.year:
            max_month = now.month

        for month in range(1, max_month + 1):
            # CPI base 100, typical China inflation ~2%
            base = 102.0 + (year - 2023) * 0.5
            # Seasonal pattern: food prices rise before Spring Festival
            seasonal = 0.3 * math.sin(2 * math.pi * (month - 1) / 12)
            noise = random.gauss(0, 0.3)
            cpi = base + seasonal + noise

            result.append({
                "indicator": "cpi",
                "indicator_en": "CPI",
                "indicator_cn": "居民消费价格指数",
                "period": f"{year}-{month:02d}",
                "value": round(cpi, 1),
                "base_period": "prev_year=100",
                "yoy_change_pct": round(cpi - 100 + random.gauss(0, 0.2), 1),
                "source": "mock",
            })

    return result


def _generate_mock_pmi(start_year: int, end_year: int) -> list:
    """Generate mock PMI monthly data.

    Args:
        start_year: Start year
        end_year: End year

    Returns:
        List of monthly PMI data points (manufacturing + services)
    """
    random.seed(start_year * 200 + end_year)
    result = []

    for year in range(start_year, end_year + 1):
        now = datetime.now(timezone.utc)
        max_month = 12
        if year == now.year:
            max_month = now.month

        for month in range(1, max_month + 1):
            # Manufacturing PMI hovers around 50 (expansion/contraction threshold)
            mfg_pmi = 50.2 + random.gauss(0, 1.2)
            # Services PMI typically higher than manufacturing
            svc_pmi = 52.5 + random.gauss(0, 1.5)

            result.append({
                "indicator": "pmi",
                "indicator_en": "PMI",
                "indicator_cn": "采购经理指数",
                "period": f"{year}-{month:02d}",
                "manufacturing_pmi": round(mfg_pmi, 1),
                "services_pmi": round(svc_pmi, 1),
                "composite_pmi": round((mfg_pmi + svc_pmi) / 2 + random.gauss(0, 0.5), 1),
                "manufacturing_expansion": mfg_pmi >= 50.0,
                "services_expansion": svc_pmi >= 50.0,
                "source": "mock",
            })

    return result


def _generate_mock_macro(country: str) -> dict:
    """Generate mock macro overview for a country.

    Args:
        country: ISO alpha-3 country code

    Returns:
        Dict with key macro indicators
    """
    country_info = COUNTRY_MACRO.get(country.upper())
    if not country_info:
        return {"error": f"Unknown country: {country}"}

    random.seed(hash(country) % 10000)

    # Scale factors by country (relative to China)
    scale = {
        "CHN": 1.0, "VNM": 0.04, "THA": 0.05, "MYS": 0.04,
        "IDN": 0.08, "PHL": 0.03, "SGP": 0.04, "MMR": 0.01,
        "KHM": 0.005, "LAO": 0.003, "BRN": 0.002,
    }.get(country.upper(), 0.02)

    return {
        "country": country,
        "country_en": country_info["name_en"],
        "country_cn": country_info["name_cn"],
        "year": datetime.now(timezone.utc).year,
        "gdp_billion_usd": round(17900 * scale + random.gauss(0, 100 * scale), 2),
        "gdp_growth_pct": round(random.uniform(2.5, 7.0), 1),
        "cpi_index": round(102.0 + random.gauss(0, 1.5), 1),
        "cpi_yoy_pct": round(random.uniform(0.5, 4.0), 1),
        "pmi_manufacturing": round(50.0 + random.gauss(0, 2.0), 1),
        "pmi_services": round(52.0 + random.gauss(0, 2.5), 1),
        "unemployment_pct": round(random.uniform(2.0, 6.5), 1),
        "fdi_inflow_billion_usd": round(180 * scale + random.gauss(0, 10 * scale), 2),
        "trade_gdp_ratio_pct": round(random.uniform(30, 120), 1),
        "source": "mock",
    }


def get_gdp_data(start_year: int, end_year: int) -> list:
    """Get China's quarterly GDP data.

    Args:
        start_year: Start year (e.g. 2018)
        end_year: End year (e.g. 2024)

    Returns:
        List of quarterly GDP data points with value and growth rate.
        Example: [{"period": "2023Q1", "value": 28499.6, "growth_yoy_pct": 4.5, ...}]
    """
    data = _fetch_nbs_indicator("gdp_quarterly", start_year, end_year)
    if data:
        return data

    result = _generate_mock_gdp(start_year, end_year)
    cache_key = f"stats_gov_gdp_{start_year}_{end_year}"
    set_cached(cache_key, "stats_gov", result, ttl_hours=24)
    logger.info("GDP data: %d mock quarterly points", len(result))
    return result


def get_cpi_data(start_year: int, end_year: int) -> list:
    """Get China's monthly CPI (inflation) data.

    Args:
        start_year: Start year (e.g. 2020)
        end_year: End year (e.g. 2024)

    Returns:
        List of monthly CPI data points with index value and YoY change.
        Example: [{"period": "2023-06", "value": 100.2, "yoy_change_pct": 0.2, ...}]
    """
    data = _fetch_nbs_indicator("cpi", start_year, end_year)
    if data:
        return data

    result = _generate_mock_cpi(start_year, end_year)
    cache_key = f"stats_gov_cpi_{start_year}_{end_year}"
    set_cached(cache_key, "stats_gov", result, ttl_hours=24)
    logger.info("CPI data: %d mock monthly points", len(result))
    return result


def get_pmi_data(start_year: int, end_year: int) -> list:
    """Get China's monthly PMI (manufacturing and services) data.

    Args:
        start_year: Start year (e.g. 2020)
        end_year: End year (e.g. 2024)

    Returns:
        List of monthly PMI data points with manufacturing, services, and composite.
        Example: [{"period": "2023-06", "manufacturing_pmi": 49.0, "services_pmi": 53.2, ...}]
    """
    data = _fetch_nbs_indicator("pmi", start_year, end_year)
    if data:
        return data

    result = _generate_mock_pmi(start_year, end_year)
    cache_key = f"stats_gov_pmi_{start_year}_{end_year}"
    set_cached(cache_key, "stats_gov", result, ttl_hours=24)
    logger.info("PMI data: %d mock monthly points", len(result))
    return result


def get_macro_indicators(country: str = "CHN") -> dict:
    """Get a combined macro overview for a country.

    For China (CHN), pulls from NBS API. For other ASEAN countries,
    provides mock data scaled by relative economic size.

    Args:
        country: ISO alpha-3 country code (default "CHN")

    Returns:
        Dict with GDP, CPI, PMI, employment, and FDI indicators.
        Example: {
            "country": "CHN",
            "gdp_billion_usd": 17900,
            "cpi_yoy_pct": 0.2,
            "pmi_manufacturing": 49.0,
            ...
        }
    """
    cache_key = f"stats_gov_macro_{country}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    if country.upper() == "CHN":
        # For China, aggregate from real API data
        current_year = datetime.now(timezone.utc).year
        gdp = get_gdp_data(current_year - 1, current_year)
        cpi = get_cpi_data(current_year - 1, current_year)
        pmi = get_pmi_data(current_year - 1, current_year)

        latest_cpi = cpi[-1] if cpi else {}
        latest_pmi = pmi[-1] if pmi else {}
        latest_gdp = gdp[-1] if gdp else {}

        # Try to fetch employment and FDI from NBS
        emp_data = _fetch_nbs_indicator("employment", current_year - 1, current_year)
        fdi_data = _fetch_nbs_indicator("fdi", current_year - 1, current_year)

        # Determine source based on whether API returned real data
        has_api = any(d.get("source") == "api" for d in gdp + cpi + pmi)

        result = {
            "country": "CHN",
            "country_en": "China",
            "country_cn": "中国",
            "year": current_year,
            "gdp_billion_cny": latest_gdp.get("value", 0),
            "gdp_growth_pct": latest_gdp.get("growth_yoy_pct", 0),
            "cpi_index": latest_cpi.get("value", 0),
            "cpi_yoy_pct": latest_cpi.get("yoy_change_pct", 0),
            "pmi_manufacturing": latest_pmi.get("manufacturing_pmi", 0),
            "pmi_services": latest_pmi.get("services_pmi", 0),
            "pmi_composite": latest_pmi.get("composite_pmi", 0),
            "unemployment_rate_pct": 5.2 if not emp_data else emp_data[-1].get("value", 5.2),
            "fdi_billion_usd": fdi_data[-1].get("value", 0) if fdi_data else 0,
            "data_points": {
                "gdp_count": len(gdp),
                "cpi_count": len(cpi),
                "pmi_count": len(pmi),
            },
            "source": "api" if has_api else "mock",
        }
    else:
        result = _generate_mock_macro(country)

    set_cached(cache_key, "stats_gov", result, ttl_hours=12)
    logger.info("Macro indicators for %s (source=%s)", country, result.get("source", "unknown"))
    return result
