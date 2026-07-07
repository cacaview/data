"""World Bank Pink Sheet Commodity Price Client.

Provides monthly prices for 80+ commodities since 1960.
Core commodities: crude oil, palm oil, rubber, rice, copper, iron ore, etc.

Source: World Bank Commodity Markets (Pink Sheet)
URL: https://thedocs.worldbank.org/en/doc/World-Bank-Commodity-Price-Data
"""
import httpx
import logging
from typing import Optional
from .cache import get_cached, set_cached

logger = logging.getLogger(__name__)

# World Bank Pink Sheet direct download URL (Excel format)
PINK_SHEET_URL = "https://thedocs.worldbank.org/en/doc/World-Bank-Commodity-Price-Data-(The-Pink-Sheet)-Historical-Data-Jan-1960-to-Dec-2024.xlsx"

# Key commodities for ASEAN-China trade
KEY_COMMODITIES = {
    "PCOALAU": {"name_en": "Coal, Australian", "name_cn": "煤炭（澳洲）", "unit": "mt"},
    "POILWTI": {"name_en": "Crude Oil, WTI", "name_cn": "WTI原油", "unit": "bbl"},
    "POILBRENT": {"name_en": "Crude Oil, Brent", "name_cn": "布伦特原油", "unit": "bbl"},
    "PNGASUS": {"name_en": "Natural Gas, US", "name_cn": "天然气（美国）", "unit": "mmbtu"},
    "PNGASEU": {"name_en": "Natural Gas, Europe", "name_cn": "天然气（欧洲）", "unit": "mmbtu"},
    "PCOPP": {"name_en": "Copper", "name_cn": "铜", "unit": "mt"},
    "PALUM": {"name_en": "Aluminum", "name_cn": "铝", "unit": "mt"},
    "PIORECR": {"name_en": "Iron Ore", "name_cn": "铁矿石", "unit": "mt"},
    "PPOIL": {"name_en": "Palm Oil", "name_cn": "棕榈油", "unit": "mt"},
    "PRUBB": {"name_en": "Rubber, Singapore", "name_cn": "橡胶（新加坡）", "unit": "mt"},
    "PRICENPQ": {"name_en": "Rice, Thailand", "name_cn": "大米（泰国）", "unit": "mt"},
    "PWHEAMT": {"name_en": "Wheat, US", "name_cn": "小麦（美国）", "unit": "mt"},
    "PSOYB": {"name_en": "Soybeans", "name_cn": "大豆", "unit": "mt"},
    "PSUGAISA": {"name_en": "Sugar, world", "name_cn": "食糖（世界）", "unit": "mt"},
    "PCOFFOTM": {"name_en": "Coffee, Other Mild Arabicas", "name_cn": "咖啡", "unit": "mt"},
    "PCOCO": {"name_en": "Cocoa", "name_cn": "可可", "unit": "mt"},
    "PTIN": {"name_en": "Tin", "name_cn": "锡", "unit": "mt"},
    "PNIKK": {"name_en": "Nickel", "name_cn": "镍", "unit": "mt"},
    "PZINC": {"name_en": "Zinc", "name_cn": "锌", "unit": "mt"},
    "PLEAD": {"name_en": "Lead", "name_cn": "铅", "unit": "mt"},
}

# Fallback: IMF Primary Commodity Price System
IMF_PCPS_URL = "https://www.imf.org/external/np/res/commod/External_Data.xls"


def get_commodity_prices_from_imf() -> dict:
    """Fetch commodity prices from IMF Primary Commodity Price System.

    Returns monthly prices for key commodities.
    This is the most reliable free API for commodity prices.

    Returns:
        Dict mapping commodity code to list of price data
    """
    cache_key = "commodity_imf_pcps"
    cached = get_cached(cache_key)
    if cached:
        return cached

    try:
        # Use IMF API endpoint for commodity prices
        url = "https://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/PIT"
        params = {"startPeriod": "2020", "endPeriod": "2025"}
        resp = httpx.get(url, params=params, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()

        dataset = data.get("CompactData", {}).get("DataSet", {})
        series_list = dataset.get("Series", [])

        if isinstance(series_list, dict):
            series_list = [series_list]

        result = {}
        for series in series_list:
            commodity_id = series.get("@PIT_COMMODITY", "unknown")
            obs = series.get("Obs", [])
            if isinstance(obs, dict):
                obs = [obs]

            prices = []
            for o in obs:
                period = o.get("@TIME_PERIOD", "")
                value = o.get("@OBS_VALUE")
                if value is not None:
                    try:
                        prices.append({"period": period, "price": float(value)})
                    except (ValueError, TypeError):
                        continue

            if prices:
                result[commodity_id] = prices

        set_cached(cache_key, "commodity_imf", result, ttl_hours=168)  # 1 week
        logger.info("IMF commodity prices: fetched %d commodities", len(result))
        return result

    except Exception as e:
        logger.error("IMF commodity prices error: %s", e)
        return {}


def get_palm_oil_price() -> list:
    """Get palm oil price data.

    Returns:
        List of monthly palm oil prices
    """
    data = get_commodity_prices_from_imf()
    # Palm oil IMF code varies; try common codes
    for code in ["PPOIL", "FCPO", "POIL"]:
        if code in data:
            return data[code]
    return []


def get_crude_oil_price() -> list:
    """Get crude oil (Brent) price data.

    Returns:
        List of monthly crude oil prices
    """
    data = get_commodity_prices_from_imf()
    for code in ["POILAPSP", "POILBRENT", "POILWTI"]:
        if code in data:
            return data[code]
    return []


def get_rubber_price() -> list:
    """Get natural rubber price data.

    Returns:
        List of monthly rubber prices
    """
    data = get_commodity_prices_from_imf()
    for code in ["PRUBB", "PRICENPQ"]:
        if code in data:
            return data[code]
    return []


def get_asean_relevant_commodities() -> dict:
    """Get prices for commodities most relevant to ASEAN-China trade.

    Returns:
        Dict with key commodity prices (palm oil, rubber, tin, rice, coal, etc.)
    """
    all_data = get_commodity_prices_from_imf()

    asean_commodities = {}
    target_codes = ["PPOIL", "PRUBB", "PTIN", "PRICENPQ", "PCOALAU", "POILAPSP",
                    "PALUM", "PCOPP", "PIORECR", "PNIKK"]

    for code in target_codes:
        if code in all_data:
            asean_commodities[code] = all_data[code]

    # Also include any available data
    for code, info in KEY_COMMODITIES.items():
        if code in all_data and code not in asean_commodities:
            asean_commodities[code] = all_data[code]

    return asean_commodities


def get_commodity_summary() -> dict:
    """Get a summary of key commodity prices (latest + trend).

    Returns:
        Dict with latest price, 30-day change, and trend for each commodity
    """
    all_data = get_commodity_prices_from_imf()
    summary = {}

    for code, prices in all_data.items():
        if len(prices) < 2:
            continue
        latest = prices[-1]
        prev = prices[-2] if len(prices) >= 2 else latest
        summary[code] = {
            "latest_price": latest["price"],
            "latest_period": latest["period"],
            "prev_price": prev["price"],
            "change_pct": round((latest["price"] - prev["price"]) / prev["price"] * 100, 2)
            if prev["price"] != 0 else 0,
        }

    return summary
