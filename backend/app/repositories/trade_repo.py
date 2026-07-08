"""Trade data repository.

Encapsulates all database queries against the trade_records table.
Route handlers should not import SQLAlchemy directly — they should
call these functions instead.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import REPORTER_CODE
from app.models.schemas_db import Country, TradeRecord


# === Time range helpers ===

def get_latest_year(db: Session) -> Optional[int]:
    """Return the most recent year in the trade_records table."""
    return db.query(func.max(TradeRecord.year)).scalar()


def get_latest_year_for_partner(db: Session, partner: str) -> Optional[int]:
    """Latest year of trade with a specific partner."""
    return (
        db.query(func.max(TradeRecord.year))
        .filter(TradeRecord.partner == partner, TradeRecord.reporter == REPORTER_CODE)
        .scalar()
    )


# === Aggregate value queries ===

def sum_trade_value(
    db: Session,
    *,
    year: int,
    partner: Optional[str] = None,
    section: Optional[str] = None,
) -> float:
    """Sum trade_value_usd for the given filters (coalesced to 0)."""
    q = db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 0.0)).filter(
        TradeRecord.year == year,
        TradeRecord.reporter == REPORTER_CODE,
    )
    if partner:
        q = q.filter(TradeRecord.partner == partner)
    if section:
        q = q.filter(TradeRecord.hs_section == section)
    return float(q.scalar() or 0.0)


def sum_trade_value_grouped(
    db: Session,
    *,
    year: int,
    group_by: str,  # 'partner' or 'hs_section'
) -> List[Tuple[str, float]]:
    """Group-by sum of trade_value_usd.

    Args:
        group_by: 'partner' or 'hs_section'

    Returns:
        List of (key, total_value) tuples
    """
    column = TradeRecord.partner if group_by == "partner" else TradeRecord.hs_section
    rows = (
        db.query(column.label("key"), func.sum(TradeRecord.trade_value_usd).label("total"))
        .filter(
            TradeRecord.year == year,
            TradeRecord.reporter == REPORTER_CODE,
            column.isnot(None),
        )
        .group_by(column)
        .order_by(func.sum(TradeRecord.trade_value_usd).desc())
        .all()
    )
    return [(r.key, float(r.total or 0.0)) for r in rows]


def count_distinct_sections(db: Session, *, year: int, partner: str) -> int:
    """Count distinct HS sections traded with a partner in a year."""
    result = (
        db.query(func.count(func.distinct(TradeRecord.hs_section)))
        .filter(
            TradeRecord.partner == partner,
            TradeRecord.reporter == REPORTER_CODE,
            TradeRecord.year == year,
        )
        .scalar()
    )
    return int(result or 0)


# === Trend queries ===

def fetch_trend_rows(
    db: Session,
    *,
    countries: Optional[Sequence[str]] = None,
    sections: Optional[Sequence[str]] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> List[Tuple[int, int, str, float]]:
    """Fetch aggregated trend rows (year, month, partner, total)."""
    q = db.query(
        TradeRecord.year,
        TradeRecord.month,
        TradeRecord.partner,
        func.sum(TradeRecord.trade_value_usd).label("total"),
    ).filter(TradeRecord.reporter == REPORTER_CODE)

    if countries:
        q = q.filter(TradeRecord.partner.in_(list(countries)))
    if sections:
        q = q.filter(TradeRecord.hs_section.in_(list(sections)))
    if start_year:
        q = q.filter(TradeRecord.year >= start_year)
    if end_year:
        q = q.filter(TradeRecord.year <= end_year)

    rows = (
        q.group_by(TradeRecord.year, TradeRecord.month, TradeRecord.partner)
        .order_by(TradeRecord.year, TradeRecord.month)
        .all()
    )
    return [(r[0], r[1], r[2], float(r[3] or 0.0)) for r in rows]


# === Sankey queries ===

def fetch_sankey_rows(
    db: Session,
    *,
    year: int,
) -> List[Tuple[str, str, float]]:
    """Fetch (partner, section, total) for sankey diagram."""
    rows = (
        db.query(
            TradeRecord.partner,
            TradeRecord.hs_section,
            func.sum(TradeRecord.trade_value_usd).label("total"),
        )
        .filter(
            TradeRecord.year == year,
            TradeRecord.reporter == REPORTER_CODE,
            TradeRecord.hs_section.isnot(None),
        )
        .group_by(TradeRecord.partner, TradeRecord.hs_section)
        .all()
    )
    return [(r[0], r[1], float(r[2] or 0.0)) for r in rows]


# === Country lookups ===

def get_country(db: Session, code: str) -> Optional[Country]:
    return db.query(Country).filter(Country.code == code).first()


def get_countries_by_codes(db: Session, codes: Sequence[str]) -> List[Country]:
    if not codes:
        return []
    return db.query(Country).filter(Country.code.in_(list(codes))).all()


def get_country_name_map(db: Session, codes: Sequence[str]) -> Dict[str, str]:
    """Return {code: name_cn} for the given country codes."""
    countries = get_countries_by_codes(db, codes)
    return {c.code: c.name_cn for c in countries}


# === Bulk operations (used by ETL / init) ===

def bulk_insert_trade_records(db: Session, records: List[dict]) -> None:
    """Bulk insert a list of trade record dicts."""
    db.bulk_insert_mappings(TradeRecord, records)
    db.commit()


def update_source_record_count(db: Session, source: str, count: int) -> None:
    """Update the record_count column for a data source."""
    from app.models.schemas_db import DataSource
    src = db.query(DataSource).filter(DataSource.name == source).first()
    if src:
        src.record_count = count
        src.last_sync = func.now()
        db.commit()
