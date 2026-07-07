"""ETL Pipeline for multi-source data integration.

Handles data cleaning, HS code standardization, time series alignment,
and loading into SQLite database.

Data quality follows TC609 standard:
- Completeness: field fill rate
- Accuracy: outlier detection, cross-source consistency
- Timeliness: data update lag
- Consistency: country/HS code unification
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.database import SessionLocal
from ..models.schemas_db import TradeRecord, Country, Product
from . import comtrade_client, worldbank_client, imf_client
from . import exchange_rate_client, commodity_client

logger = logging.getLogger(__name__)

# Country code mapping: ISO alpha-3 → M49 → World Bank alpha-2
COUNTRY_MAP = {
    "CHN": {"m49": "156", "wb": "CN", "name_cn": "中国", "name_en": "China"},
    "VNM": {"m49": "704", "wb": "VN", "name_cn": "越南", "name_en": "Vietnam"},
    "THA": {"m49": "764", "wb": "TH", "name_cn": "泰国", "name_en": "Thailand"},
    "MYS": {"m49": "458", "wb": "MY", "name_cn": "马来西亚", "name_en": "Malaysia"},
    "IDN": {"m49": "360", "wb": "ID", "name_cn": "印尼", "name_en": "Indonesia"},
    "PHL": {"m49": "608", "wb": "PH", "name_cn": "菲律宾", "name_en": "Philippines"},
    "SGP": {"m49": "702", "wb": "SG", "name_cn": "新加坡", "name_en": "Singapore"},
    "MMR": {"m49": "104", "wb": "MM", "name_cn": "缅甸", "name_en": "Myanmar"},
    "KHM": {"m49": "116", "wb": "KH", "name_cn": "柬埔寨", "name_en": "Cambodia"},
    "LAO": {"m49": "418", "wb": "LA", "name_cn": "老挝", "name_en": "Laos"},
    "BRN": {"m49": "096", "wb": "BN", "name_cn": "文莱", "name_en": "Brunei"},
}

ASEAN_PARTNER_CODES = ["VNM", "THA", "MYS", "IDN", "PHL", "SGP", "MMR", "KHM", "LAO", "BRN"]


def init_country_data(db: Session):
    """Initialize country lookup table with ASEAN + China data.

    Args:
        db: Database session
    """
    for code, info in COUNTRY_MAP.items():
        existing = db.query(Country).filter(Country.code == code).first()
        if not existing:
            country = Country(
                code=code,
                name_cn=info["name_cn"],
                name_en=info["name_en"],
                asean_member=1 if code != "CHN" else 0,
                rcep_member=1,
            )
            db.add(country)
            logger.info("Added country: %s (%s)", info["name_cn"], code)

    db.commit()


def fetch_and_store_comtrade_data(db: Session, year: str = "2023",
                                   partners: Optional[list] = None,
                                   max_records: int = 500):
    """Fetch data from UN Comtrade and store in database.

    Args:
        db: Database session
        year: Year to fetch
        partners: List of partner ISO codes (default: all ASEAN)
        max_records: Maximum records per partner to store
    """
    if partners is None:
        partners = ASEAN_PARTNER_CODES

    total_stored = 0
    for partner in partners:
        m49 = COUNTRY_MAP.get(partner, {}).get("m49")
        if not m49:
            continue

        logger.info("Fetching Comtrade: China → %s (%s)", partner, year)
        records = comtrade_client.get_bilateral_trade(
            reporter="156", partner=m49, flow="X", period=year, hs_level="HS6"
        )

        if not records:
            logger.warning("No Comtrade data for China→%s, year=%s", partner, year)
            continue

        stored = 0
        for r in records[:max_records]:
            hs_code = r.get("commodity_code", "")
            hs_chapter = int(hs_code[:2]) if len(hs_code) >= 2 else None

            record = TradeRecord(
                year=r.get("year", int(year)),
                month=r.get("month", 1) or 1,
                reporter="CHN",
                partner=partner,
                hs_code=hs_code,
                hs_chapter=hs_chapter,
                trade_value_usd=r.get("trade_value", 0),
                quantity=r.get("quantity"),
                unit="USD",
                trade_flow="export" if r.get("flow_code") == "X" else "import",
                source="UN Comtrade",
            )
            db.add(record)
            stored += 1

        db.commit()
        total_stored += stored
        logger.info("Stored %d records for China→%s", stored, partner)

    logger.info("Comtrade ETL complete: %d total records stored", total_stored)
    return total_stored


def fetch_and_store_macro_data(db: Session, year_range: str = "2015:2025"):
    """Fetch macroeconomic data from World Bank and update country records.

    Args:
        db: Database session
        year_range: Year range for data
    """
    gdp_data = worldbank_client.get_gdp_data(year_range)
    for item in gdp_data:
        country_id = item.get("country_id", "")
        # Map World Bank alpha-2 to our alpha-3
        wb_to_alpha3 = {v["wb"]: k for k, v in COUNTRY_MAP.items()}
        alpha3 = wb_to_alpha3.get(country_id)

        if alpha3:
            country = db.query(Country).filter(Country.code == alpha3).first()
            if country and item.get("value"):
                # Update GDP with latest value
                country.gdp_billion_usd = round(item["value"] / 1e9, 2)
                logger.debug("Updated GDP for %s: %.2fB", alpha3, country.gdp_billion_usd)

    db.commit()
    logger.info("Macro data updated for %d countries", len(COUNTRY_MAP))


def get_data_quality_report(db: Session) -> dict:
    """Generate a data quality report following TC609 standard.

    Returns:
        Dict with quality metrics for each dimension
    """
    total = db.query(TradeRecord).count()
    if total == 0:
        return {"status": "no_data", "total_records": 0}

    # Completeness
    with_value = db.query(TradeRecord).filter(TradeRecord.trade_value_usd > 0).count()
    completeness = with_value / total * 100 if total > 0 else 0

    # Source distribution
    sources = db.query(TradeRecord.source, func.count()).group_by(TradeRecord.source).all()
    source_dist = {s[0] or "unknown": s[1] for s in sources}

    # Country coverage
    partners = db.query(TradeRecord.partner).distinct().count()

    # HS code coverage
    hs_codes = db.query(TradeRecord.hs_code).distinct().count()

    # Temporal coverage
    years = db.query(func.min(TradeRecord.year), func.max(TradeRecord.year)).first()

    return {
        "total_records": total,
        "completeness_pct": round(completeness, 2),
        "source_distribution": source_dist,
        "country_coverage": partners,
        "hs_code_coverage": hs_codes,
        "year_range": f"{years[0]}-{years[1]}" if years[0] else "N/A",
        "quality_score": round(completeness * 0.4 + min(partners / 10, 1) * 30 + min(hs_codes / 100, 1) * 30, 1),
    }


def run_full_etl(db: Session, year: str = "2023"):
    """Run the complete ETL pipeline.

    1. Initialize country data
    2. Fetch exchange rates (fast, no auth)
    3. Fetch World Bank macro data (fast, no auth)
    4. Fetch Comtrade trade data (rate limited: 500/day)
    5. Generate quality report

    Args:
        db: Database session
        year: Year for Comtrade data
    """
    logger.info("Starting full ETL pipeline for year %s", year)

    # Step 1: Country data
    init_country_data(db)

    # Step 2: Exchange rates (quick, ~1 second)
    logger.info("Fetching exchange rates...")
    rates = exchange_rate_client.get_latest_rates()
    logger.info("Exchange rates fetched: %d currencies", len(rates) - 3 if rates else 0)

    # Step 3: World Bank macro data (quick, ~5 seconds)
    logger.info("Fetching World Bank macro data...")
    fetch_and_store_macro_data(db)

    # Step 4: Comtrade data (rate limited — only fetch if no cached data)
    existing_count = db.query(TradeRecord).filter(TradeRecord.source == "UN Comtrade").count()
    if existing_count == 0:
        logger.info("No Comtrade data found, fetching from API...")
        fetch_and_store_comtrade_data(db, year, max_records=200)
    else:
        logger.info("Found %d existing Comtrade records, skipping fetch", existing_count)

    # Step 5: Quality report
    quality = get_data_quality_report(db)
    logger.info("ETL complete. Quality score: %.1f/100", quality.get("quality_score", 0))
    return quality
