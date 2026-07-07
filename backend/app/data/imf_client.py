"""IMF Direction of Trade Statistics (DOTS) API Client.

Completely free, no API key required. SDMX 2.1/3.0 standard.
Provides bilateral trade flow data for validation against UN Comtrade.

API: http://dataservices.imf.org/REST/SDMX_JSON.svc/
"""
import httpx
import logging
from typing import Optional
from .cache import get_cached, set_cached

logger = logging.getLogger(__name__)

BASE_URL = "http://dataservices.imf.org/REST/SDMX_JSON.svc"

# ISO codes used by IMF
ASEAN_CHINA_CODES = {
    "CHN": "CHN", "VNM": "VNM", "THA": "THA", "MYS": "MYS",
    "IDN": "IDN", "PHL": "PHL", "SGP": "SGP", "MMR": "MMR",
    "KHM": "KHM", "LAO": "LAO", "BRN": "BRN",
}

# DOTS indicators
INDICATORS = {
    "TXG_FOB_USD": {"name_en": "Exports (FOB, USD)", "name_cn": "出口额（FOB，美元）"},
    "TMG_CIF_USD": {"name_en": "Imports (CIF, USD)", "name_cn": "进口额（CIF，美元）"},
    "TXG_VAL_USD": {"name_en": "Export Value", "name_cn": "出口值"},
    "TMG_VAL_USD": {"name_en": "Import Value", "name_cn": "进口值"},
}


def get_bilateral_data(reporter: str = "CHN", partner: str = "VNM",
                       indicator: str = "TXG_FOB_USD",
                       frequency: str = "A") -> list:
    """Get bilateral trade data from IMF DOTS.

    Args:
        reporter: Reporter country ISO code
        partner: Partner country ISO code
        indicator: DOTS indicator code
        frequency: "A" for annual, "M" for monthly

    Returns:
        List of data points with period and value
    """
    cache_key = f"imf_dots_{reporter}_{partner}_{indicator}_{frequency}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    try:
        # SDMX data query format
        key = f"{reporter}.{partner}.{indicator}.{frequency}"
        url = f"{BASE_URL}/CompactData/DOT/{key}"

        resp = httpx.get(url, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()

        # Parse SDMX JSON response
        dataset = data.get("CompactData", {}).get("DataSet", {})
        series = dataset.get("Series", {})

        if not series:
            logger.warning("IMF DOTS: no data for %s", key)
            return []

        # Handle single series (dict) or multiple series (list)
        if isinstance(series, dict):
            series = [series]

        result = []
        for s in series:
            obs = s.get("Obs", [])
            if isinstance(obs, dict):
                obs = [obs]
            for o in obs:
                period = o.get("@TIME_PERIOD", "")
                value = o.get("@OBS_VALUE")
                if value is not None:
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        continue
                    result.append({
                        "reporter": reporter,
                        "partner": partner,
                        "indicator": indicator,
                        "period": period,
                        "value": value,
                        "frequency": frequency,
                    })

        set_cached(cache_key, "imf_dots", result, ttl_hours=48)
        logger.info("IMF DOTS: fetched %d records for %s", len(result), key)
        return result

    except Exception as e:
        logger.error("IMF DOTS API error: %s", e)
        return []


def get_china_asean_trade(year: str = "2023", frequency: str = "A") -> dict:
    """Get China's bilateral trade with all ASEAN countries.

    Args:
        year: Year
        frequency: "A" for annual, "M" for monthly

    Returns:
        Dict with exports and imports data by partner
    """
    result = {}
    for country_code in ASEAN_CHINA_CODES:
        if country_code == "CHN":
            continue

        exports = get_bilateral_data("CHN", country_code, "TXG_FOB_USD", frequency)
        imports = get_bilateral_data("CHN", country_code, "TMG_CIF_USD", frequency)

        # Filter to requested year
        exports_filtered = [e for e in exports if year in str(e.get("period", ""))]
        imports_filtered = [i for i in imports if year in str(i.get("period", ""))]

        result[country_code] = {
            "exports": exports_filtered,
            "imports": imports_filtered,
            "total_export": sum(e["value"] for e in exports_filtered),
            "total_import": sum(i["value"] for i in imports_filtered),
        }

    return result


def validate_comtrade_data(comtrade_total: float, reporter: str, partner: str,
                           year: str = "2023") -> dict:
    """Cross-validate Comtrade data against IMF DOTS.

    Args:
        comtrade_total: Total trade value from Comtrade
        reporter: Country code
        partner: Partner country code
        year: Year

    Returns:
        Validation result with discrepancy info
    """
    imf_data = get_bilateral_data(reporter, partner, "TXG_FOB_USD", "A")
    imf_value = None
    for d in imf_data:
        if year in str(d.get("period", "")):
            imf_value = d["value"]
            break

    if imf_value is None:
        return {
            "validated": False,
            "reason": "IMF data not available",
            "comtrade_value": comtrade_total,
        }

    discrepancy = abs(comtrade_total - imf_value) / max(comtrade_total, imf_value) * 100

    return {
        "validated": True,
        "comtrade_value": comtrade_total,
        "imf_value": imf_value,
        "discrepancy_pct": round(discrepancy, 2),
        "consistent": discrepancy < 15,  # Less than 15% difference is acceptable
    }
