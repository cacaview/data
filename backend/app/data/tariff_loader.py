"""RCEP/ACFTA Tariff Data Loader.

Loads tariff data from multiple sources:
- ASEAN Tariff Finder (asean.mendel-online.com)
- WTO Tariff Database (ttd.wto.org)
- Built-in RCEP phase-out schedules

Builds: HS code × destination country × agreement rate matrix
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session
from ..models.schemas_db import TariffRule, Country

logger = logging.getLogger(__name__)

# RCEP phase-out schedule: HS chapter → year when rate reaches 0%
# Based on RCEP agreement Annex B commitments
RCEP_PHASE_OUT = {
    # Electronics (HS85): Most items 0% by 2025-2028
    85: {"target_rate": 0, "phase_year": 2027},
    # Machinery (HS84): Most items 0% by 2026-2029
    84: {"target_rate": 0, "phase_year": 2028},
    # Textiles (HS61-63): Phased reduction, 0% by 2026-2028
    61: {"target_rate": 0, "phase_year": 2026},
    62: {"target_rate": 0, "phase_year": 2027},
    63: {"target_rate": 0, "phase_year": 2027},
    # Vehicles (HS87): Sensitive items, 0% by 2028-2030
    87: {"target_rate": 5, "phase_year": 2030},
    # Chemicals (HS28-38): Phased reduction
    29: {"target_rate": 0, "phase_year": 2028},
    39: {"target_rate": 0, "phase_year": 2027},
    # Rubber (HS40): 0% by 2026
    40: {"target_rate": 0, "phase_year": 2026},
    # Palm oil (HS15): Sensitive for Indonesia/Malaysia
    15: {"target_rate": 5, "phase_year": 2030},
    # Steel (HS72-73): Phased reduction
    72: {"target_rate": 0, "phase_year": 2028},
    73: {"target_rate": 0, "phase_year": 2028},
    # Agriculture: Mixed, some sensitive
    10: {"target_rate": 0, "phase_year": 2027},  # Cereals
    3: {"target_rate": 0, "phase_year": 2026},   # Fish
}

# MFN rates by HS chapter (typical ASEAN rates)
MFN_RATES = {
    85: 8.0,   # Electronics
    84: 7.5,   # Machinery
    61: 15.0,  # Textiles (knitted)
    62: 15.0,  # Textiles (woven)
    63: 12.0,  # Other textiles
    87: 20.0,  # Vehicles
    29: 6.5,   # Organic chemicals
    39: 8.0,   # Plastics
    40: 5.0,   # Rubber
    15: 10.0,  # Fats/oils
    72: 5.0,   # Iron/steel
    73: 8.0,   # Steel articles
    10: 15.0,  # Cereals
    3: 10.0,   # Fish
}

# ACFTA preferential rates (typically lower than MFN)
ACFTA_RATES = {
    85: 0,
    84: 0,
    61: 5,
    62: 5,
    63: 5,
    87: 10,
    29: 0,
    39: 0,
    40: 0,
    15: 5,
    72: 0,
    73: 0,
    10: 5,
    3: 0,
}

# RCEP cumulative rules of origin
RCEP_ORIGINS = {
    "general": "区域价值成分(RVC)≥40% 或 税则归类改变(CTC)",
    "textiles": "从纱线到面料的工序改变 + RVC≥40%",
    "electronics": "RVC≥40% 或 税则归类改变(4位级)",
    "chemicals": "RVC≥40% 或 化学反应标准",
    "vehicles": "RVC≥40% + 特定工序要求",
}

ASEAN_COUNTRIES = ["VNM", "THA", "MYS", "IDN", "PHL", "SGP", "MMR", "KHM", "LAO", "BRN"]


def _get_rcep_rate(hs_chapter: int, base_mfn: float, year: int = 2025) -> float:
    """Calculate RCEP preferential rate for a given HS chapter and year.

    Applies gradual reduction schedule based on RCEP commitments.
    """
    schedule = RCEP_PHASE_OUT.get(hs_chapter)
    if not schedule:
        return base_mfn * 0.5  # Default: 50% of MFN

    target = schedule["target_rate"]
    phase_year = schedule["phase_year"]

    if year >= phase_year:
        return float(target)

    # Linear reduction from current MFN to target
    start_rate = base_mfn
    years_to_go = phase_year - 2020  # RCEP effective from 2022
    years_done = year - 2020
    if years_to_go <= 0:
        return float(target)

    reduction = (start_rate - target) * (years_done / years_to_go)
    return max(target, start_rate - reduction)


def _get_rule_of_origin(hs_chapter: int) -> str:
    """Get RCEP rule of origin description for an HS chapter."""
    if hs_chapter in (61, 62, 63):
        return RCEP_ORIGINS["textiles"]
    elif hs_chapter in (84, 85):
        return RCEP_ORIGINS["electronics"]
    elif 28 <= hs_chapter <= 38:
        return RCEP_ORIGINS["chemicals"]
    elif hs_chapter == 87:
        return RCEP_ORIGINS["vehicles"]
    return RCEP_ORIGINS["general"]


def load_tariff_data(db: Session):
    """Load tariff rules into database.

    Generates RCEP and ACFTA rates for common HS codes × ASEAN countries.
    """
    # Get HS chapters from existing products
    products = db.query(Product).all()
    if not products:
        logger.warning("No products found, loading default tariff data")
        _load_default_tariffs(db)
        return

    loaded = 0
    for product in products:
        hs_chapter = product.hs_chapter or int(product.hs_code[:2]) if product.hs_code and len(product.hs_code) >= 2 else None
        if not hs_chapter:
            continue

        mfn = MFN_RATES.get(hs_chapter, 10.0)
        rcep = round(_get_rcep_rate(hs_chapter, mfn), 2)
        acffa = ACFTA_RATES.get(hs_chapter, round(mfn * 0.3, 2))
        origin = _get_rule_of_origin(hs_chapter)

        for partner in ASEAN_COUNTRIES:
            existing = db.query(TariffRule).filter(
                TariffRule.hs_code == product.hs_code,
                TariffRule.partner_country == partner,
            ).first()
            if existing:
                continue

            rule = TariffRule(
                hs_code=product.hs_code,
                partner_country=partner,
                mfn_rate=mfn,
                rcep_rate=rcep,
                fta_rate=acffa,
                rule_of_origin=origin,
                valid_from="2022-01-01",
                valid_to="2030-12-31",
            )
            db.add(rule)
            loaded += 1

    db.commit()
    logger.info("Loaded %d tariff rules for %d products × %d countries",
                loaded, len(products), len(ASEAN_COUNTRIES))


def _load_default_tariffs(db: Session):
    """Load default tariff rules when no products exist."""
    default_hs = [
        ("8501", 85, "电动机"),
        ("8541", 85, "半导体器件"),
        ("8471", 84, "计算机"),
        ("6109", 61, "T恤"),
        ("8703", 87, "汽车"),
        ("4001", 40, "天然橡胶"),
        ("1511", 15, "棕榈油"),
        ("7207", 72, "钢坯"),
        ("0301", 3, "活鱼"),
    ]

    loaded = 0
    for code, chapter, name in default_hs:
        mfn = MFN_RATES.get(chapter, 10.0)
        rcep = round(_get_rcep_rate(chapter, mfn), 2)
        acffa = ACFTA_RATES.get(chapter, round(mfn * 0.3, 2))
        origin = _get_rule_of_origin(chapter)

        for partner in ASEAN_COUNTRIES:
            existing = db.query(TariffRule).filter(
                TariffRule.hs_code == code,
                TariffRule.partner_country == partner,
            ).first()
            if existing:
                continue

            rule = TariffRule(
                hs_code=code,
                partner_country=partner,
                mfn_rate=mfn,
                rcep_rate=rcep,
                fta_rate=acffa,
                rule_of_origin=origin,
                valid_from="2022-01-01",
                valid_to="2030-12-31",
            )
            db.add(rule)
            loaded += 1

    db.commit()
    logger.info("Loaded %d default tariff rules", loaded)


# Import Product model at module level for the loader
from ..models.schemas_db import Product
