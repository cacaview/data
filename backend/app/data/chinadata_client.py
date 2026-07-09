"""China Data Portal Client.

Fetches Chinese customs trade data from chinadata.live REST API.
Provides monthly import/export data for 106 partner countries.
Free, no API key required.

API: https://chinadata.live/api/
"""
import httpx
import logging
import math
import random
from datetime import datetime, timezone
from typing import Optional
from .cache import get_cached, set_cached

logger = logging.getLogger(__name__)

BASE_URL = "https://chinadata.live/api"

# Partner country codes used by chinadata (ISO numeric / custom)
PARTNER_CODES = {
    "USA": {"code": "842", "name_en": "United States", "name_cn": "美国"},
    "JPN": {"code": "392", "name_en": "Japan", "name_cn": "日本"},
    "KOR": {"code": "410", "name_en": "South Korea", "name_cn": "韩国"},
    "TWN": {"code": "0158", "name_en": "Taiwan", "name_cn": "台湾"},
    "DEU": {"code": "276", "name_en": "Germany", "name_cn": "德国"},
    "VNM": {"code": "704", "name_en": "Vietnam", "name_cn": "越南"},
    "AUS": {"code": "036", "name_en": "Australia", "name_cn": "澳大利亚"},
    "MYS": {"code": "458", "name_en": "Malaysia", "name_cn": "马来西亚"},
    "BRA": {"code": "076", "name_en": "Brazil", "name_cn": "巴西"},
    "RUS": {"code": "643", "name_en": "Russia", "name_cn": "俄罗斯"},
    "THA": {"code": "764", "name_en": "Thailand", "name_cn": "泰国"},
    "IND": {"code": "356", "name_en": "India", "name_cn": "印度"},
    "IDN": {"code": "360", "name_en": "Indonesia", "name_cn": "印尼"},
    "SGP": {"code": "702", "name_en": "Singapore", "name_cn": "新加坡"},
    "GBR": {"code": "826", "name_en": "United Kingdom", "name_cn": "英国"},
    "NLD": {"code": "528", "name_en": "Netherlands", "name_cn": "荷兰"},
    "PHL": {"code": "608", "name_en": "Philippines", "name_cn": "菲律宾"},
    "SAU": {"code": "682", "name_en": "Saudi Arabia", "name_cn": "沙特阿拉伯"},
    "MMR": {"code": "104", "name_en": "Myanmar", "name_cn": "缅甸"},
    "KHM": {"code": "116", "name_en": "Cambodia", "name_cn": "柬埔寨"},
}

# Top traded HS2 product categories for mock data
TOP_PRODUCT_CATEGORIES = [
    {"hs2": "85", "name_en": "Electrical machinery and equipment", "name_cn": "电气设备"},
    {"hs2": "84", "name_en": "Machinery and mechanical appliances", "name_cn": "机械器具"},
    {"hs2": "27", "name_en": "Mineral fuels and oils", "name_cn": "矿物燃料"},
    {"hs2": "72", "name_en": "Iron and steel", "name_cn": "钢铁"},
    {"hs2": "39", "name_en": "Plastics and articles thereof", "name_cn": "塑料制品"},
    {"hs2": "87", "name_en": "Vehicles other than railway", "name_cn": "车辆"},
    {"hs2": "29", "name_en": "Organic chemicals", "name_cn": "有机化学品"},
    {"hs2": "71", "name_en": "Precious stones and metals", "name_cn": "贵金属"},
    {"hs2": "61", "name_en": "Knitted or crocheted apparel", "name_cn": "针织服装"},
    {"hs2": "94", "name_en": "Furniture and bedding", "name_cn": "家具"},
    {"hs2": "62", "name_en": "Not knitted apparel", "name_cn": "非针织服装"},
    {"hs2": "03", "name_en": "Fish and crustaceans", "name_cn": "鱼及甲壳类"},
    {"hs2": "38", "name_en": "Miscellaneous chemical products", "name_cn": "杂项化学品"},
    {"hs2": "40", "name_en": "Rubber and articles thereof", "name_cn": "橡胶制品"},
    {"hs2": "73", "name_en": "Articles of iron or steel", "name_cn": "钢铁制品"},
]


def _resolve_partner_code(partner: str) -> Optional[str]:
    """Resolve a partner identifier to its numeric code.

    Args:
        partner: ISO alpha-3 code (e.g. "VNM") or numeric code

    Returns:
        Numeric code string, or None if not found
    """
    upper = partner.upper().strip()
    if upper in PARTNER_CODES:
        return PARTNER_CODES[upper]["code"]
    # Check if already a numeric code
    for info in PARTNER_CODES.values():
        if info["code"] == partner.strip():
            return partner.strip()
    return None


def _generate_mock_monthly_trade(year: int, month: Optional[int] = None) -> list:
    """Generate realistic mock monthly trade data.

    Args:
        year: Target year
        month: Specific month (1-12), or None for all months

    Returns:
        List of monthly trade records
    """
    random.seed(year * 100 + (month or 0))
    months = [month] if month else list(range(1, 13))
    result = []

    for m in months:
        if year > datetime.now(timezone.utc).year:
            continue
        if year == datetime.now(timezone.utc).year and m > datetime.now(timezone.utc).month:
            continue

        date_str = f"{year}-{m:02d}"
        # Seasonal pattern: exports tend to peak before Chinese New Year and Q4
        seasonal = 1.0 + 0.1 * math.sin(2 * 3.14159 * (m - 1) / 12)

        # Base values in billions USD
        base_export = 280.0 * seasonal
        base_import = 220.0 * seasonal

        result.append({
            "date": date_str,
            "year": year,
            "month": m,
            "exports_usd_billion": round(base_export + random.gauss(0, 20), 2),
            "imports_usd_billion": round(base_import + random.gauss(0, 18), 2),
            "trade_balance_billion": round(base_export - base_import + random.gauss(0, 5), 2),
            "yoy_export_pct": round(random.uniform(-5, 15), 1),
            "yoy_import_pct": round(random.uniform(-8, 12), 1),
            "source": "mock",
        })

    return result


def _generate_mock_partner_trade(partner_code: str, start_year: int, end_year: int) -> list:
    """Generate mock bilateral trade data for a partner country.

    Args:
        partner_code: Partner country numeric code
        start_year: Start year
        end_year: End year

    Returns:
        List of yearly bilateral trade records
    """
    # Find partner info for seeding
    partner_info = None
    for info in PARTNER_CODES.values():
        if info["code"] == partner_code:
            partner_info = info
            break

    partner_label = partner_info["name_en"] if partner_info else partner_code
    random.seed(hash(partner_code) % 10000 + start_year)

    # Trade volumes vary greatly by partner
    volume_factor = {
        "842": 2.5, "392": 1.5, "410": 1.4, "0158": 1.3,
        "276": 1.2, "704": 1.0, "036": 1.1, "458": 0.9,
        "076": 0.8, "643": 0.7, "764": 0.7, "356": 0.8,
        "360": 0.6, "702": 0.5, "826": 0.8, "528": 0.6,
        "608": 0.4, "682": 0.5, "104": 0.2, "116": 0.2,
    }.get(partner_code, 0.5)

    result = []
    for year in range(start_year, end_year + 1):
        growth = 1.0 + (year - start_year) * 0.05
        base_export = 120.0 * volume_factor * growth
        base_import = 95.0 * volume_factor * growth

        result.append({
            "partner_code": partner_code,
            "partner_name": partner_label,
            "year": year,
            "china_exports_billion": round(base_export + random.gauss(0, base_export * 0.1), 2),
            "china_imports_billion": round(base_import + random.gauss(0, base_import * 0.1), 2),
            "total_trade_billion": round(base_export + base_import + random.gauss(0, 5), 2),
            "trade_balance_billion": round(base_export - base_import + random.gauss(0, 3), 2),
            "source": "mock",
        })

    return result


def _generate_mock_top_products(partner_code: str, year: int, top_n: int = 10) -> list:
    """Generate mock top traded products for a partner country.

    Args:
        partner_code: Partner country numeric code
        year: Target year
        top_n: Number of top products to return

    Returns:
        List of top product records sorted by trade value
    """
    random.seed(hash(partner_code + str(year)) % 10000)

    products = []
    for cat in TOP_PRODUCT_CATEGORIES[:top_n]:
        export_val = random.uniform(5, 80)
        import_val = random.uniform(3, 60)
        products.append({
            "hs2_code": cat["hs2"],
            "product_name_en": cat["name_en"],
            "product_name_cn": cat["name_cn"],
            "partner_code": partner_code,
            "year": year,
            "china_export_billion": round(export_val, 2),
            "china_import_billion": round(import_val, 2),
            "total_trade_billion": round(export_val + import_val, 2),
            "unit_price_index": round(random.uniform(85, 120), 1),
            "source": "mock",
        })

    products.sort(key=lambda x: x["total_trade_billion"], reverse=True)
    return products[:top_n]



def get_china_monthly_trade(year: int, month: int = None) -> list:
    """Get China's monthly trade data (aggregate).

    Args:
        year: Target year (e.g. 2024)
        month: Specific month 1-12, or None for all months

    Returns:
        List of monthly trade records with exports, imports, balance.
        Example: [{"date": "2024-01", "exports_usd_billion": 310.2, ...}]
    """
    cache_key = f"chinadata_monthly_{year}_{month}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    try:
        params = {"year": year}
        if month:
            params["month"] = month
        resp = httpx.get(f"{BASE_URL}/trade/monthly", params=params, timeout=20.0)
        resp.raise_for_status()
        data = resp.json()

        records = data.get("data", [])
        result = []
        for r in records:
            result.append({
                "date": r.get("date", f"{year}-{r.get('month', 1):02d}"),
                "year": r.get("year", year),
                "month": r.get("month", 0),
                "exports_usd_billion": r.get("exports", 0),
                "imports_usd_billion": r.get("imports", 0),
                "trade_balance_billion": r.get("balance", 0),
                "yoy_export_pct": r.get("export_yoy", 0),
                "yoy_import_pct": r.get("import_yoy", 0),
                "source": "api",
            })

        set_cached(cache_key, "chinadata", result, ttl_hours=24)
        logger.info("China monthly trade: %d records for %s", len(result), year)
        return result

    except Exception as e:
        logger.warning("China Data API unavailable, using mock data: %s", e)

    result = _generate_mock_monthly_trade(year, month)
    set_cached(cache_key, "chinadata", result, ttl_hours=24)
    logger.info("China monthly trade: %d mock records for %s", len(result), year)
    return result


def get_china_partner_trade(partner_code: str, start_year: int, end_year: int) -> list:
    """Get bilateral trade data between China and a partner country.

    Args:
        partner_code: Partner ISO alpha-3 code (e.g. "VNM") or numeric code
        start_year: Start year (e.g. 2020)
        end_year: End year (e.g. 2024)

    Returns:
        List of yearly bilateral trade records.
        Example: [{"partner_code": "704", "year": 2023, "china_exports_billion": 137.5, ...}]
    """
    resolved = _resolve_partner_code(partner_code)
    if not resolved:
        logger.warning("Unknown partner code: %s", partner_code)
        return []

    cache_key = f"chinadata_partner_{resolved}_{start_year}_{end_year}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    try:
        resp = httpx.get(
            f"{BASE_URL}/trade/partner",
            params={"partner": resolved, "start": start_year, "end": end_year},
            timeout=20.0,
        )
        resp.raise_for_status()
        data = resp.json()

        records = data.get("data", [])
        result = []
        for r in records:
            result.append({
                "partner_code": resolved,
                "partner_name": r.get("partner_name", partner_code),
                "year": r.get("year", 0),
                "china_exports_billion": r.get("exports", 0),
                "china_imports_billion": r.get("imports", 0),
                "total_trade_billion": r.get("total", 0),
                "trade_balance_billion": r.get("balance", 0),
                "source": "api",
            })

        set_cached(cache_key, "chinadata", result, ttl_hours=24)
        logger.info("China-%s trade: %d records", partner_code, len(result))
        return result

    except Exception as e:
        logger.warning("China Data partner API unavailable, using mock: %s", e)

    result = _generate_mock_partner_trade(resolved, start_year, end_year)
    set_cached(cache_key, "chinadata", result, ttl_hours=24)
    logger.info("China-%s trade: %d mock records", partner_code, len(result))
    return result


def get_china_top_products(partner_code: str, year: int, top_n: int = 10) -> list:
    """Get top traded products between China and a partner country.

    Args:
        partner_code: Partner ISO alpha-3 code (e.g. "USA") or numeric code
        year: Target year
        top_n: Number of top products to return (default 10)

    Returns:
        List of top product records sorted by total trade value descending.
        Example: [{"hs2_code": "85", "product_name_en": "Electrical machinery", ...}]
    """
    resolved = _resolve_partner_code(partner_code)
    if not resolved:
        logger.warning("Unknown partner code: %s", partner_code)
        return []

    cache_key = f"chinadata_products_{resolved}_{year}_{top_n}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    try:
        resp = httpx.get(
            f"{BASE_URL}/trade/products",
            params={"partner": resolved, "year": year, "top": top_n},
            timeout=20.0,
        )
        resp.raise_for_status()
        data = resp.json()

        records = data.get("data", [])
        result = []
        for r in records:
            result.append({
                "hs2_code": r.get("hs2", ""),
                "product_name_en": r.get("name_en", ""),
                "product_name_cn": r.get("name_cn", ""),
                "partner_code": resolved,
                "year": year,
                "china_export_billion": r.get("exports", 0),
                "china_import_billion": r.get("imports", 0),
                "total_trade_billion": r.get("total", 0),
                "unit_price_index": r.get("price_index", 0),
                "source": "api",
            })

        set_cached(cache_key, "chinadata", result, ttl_hours=48)
        logger.info("China-%s top %d products for %d", partner_code, len(result), year)
        return result

    except Exception as e:
        logger.warning("China Data products API unavailable, using mock: %s", e)

    result = _generate_mock_top_products(resolved, year, top_n)
    set_cached(cache_key, "chinadata", result, ttl_hours=48)
    logger.info("China-%s top %d products for %d (mock)", partner_code, len(result), year)
    return result
