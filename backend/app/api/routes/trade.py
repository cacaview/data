"""Trade analysis routes -- thin HTTP layer.

These routes delegate all business logic to trade_service.
They only handle request validation and response serialization.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import RANKING_DEFAULT_LIMIT, RANKING_MAX_LIMIT
from app.models.database import get_db
from app.models.schemas import (
    CountryRadar,
    RankingItem,
    SankeyData,
    TrendPoint,
)
from app.services import trade_service

router = APIRouter()


@router.get("/trend", response_model=List[TrendPoint])
def get_trend(
    countries: Optional[str] = Query(None, description="Comma-separated ISO codes"),
    products: Optional[str] = Query(None, description="Comma-separated HS sections"),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Monthly trade trend, optionally filtered by countries and products."""
    country_list = _split_csv(countries)
    product_list = _split_csv(products)
    return trade_service.get_trend(
        db,
        countries=country_list or None,
        sections=product_list or None,
        start_year=start_year,
        end_year=end_year,
    )


@router.get("/country-compare", response_model=List[CountryRadar])
def get_country_compare(db: Session = Depends(get_db)):
    """Radar chart data for the 10 ASEAN member countries."""
    return trade_service.get_country_compare(db)


@router.get("/ranking", response_model=List[RankingItem])
def get_ranking(
    type: str = Query("country", pattern="^(country|product)$"),
    limit: int = Query(RANKING_DEFAULT_LIMIT, ge=1, le=RANKING_MAX_LIMIT),
    db: Session = Depends(get_db),
):
    """Top-N ranking by country or product section."""
    return trade_service.get_ranking(db, rank_type=type, limit=limit)


@router.get("/sankey", response_model=SankeyData)
def get_trade_sankey(
    year: int = Query(...),
    db: Session = Depends(get_db),
):
    """Full sankey diagram: all countries -> product sections for a given year."""
    return trade_service.get_sankey(db, year=year)


def _split_csv(value: Optional[str]) -> List[str]:
    """Parse a comma-separated string into a list of trimmed non-empty tokens."""
    if not value:
        return []
    return [token.strip() for token in value.split(",") if token.strip()]
