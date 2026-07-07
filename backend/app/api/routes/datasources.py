"""Data source API routes.

Exposes real-time data fetching capabilities:
- GET /datasources/status — All data source status
- GET /datasources/exchange-rates — Latest exchange rates
- GET /datasources/macro/{country} — Country macro profile
- GET /datasources/comtrade/summary — Comtrade trade summary
- GET /datasources/commodity-prices — Commodity price summary
- POST /datasources/refresh — Trigger data refresh
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.models.database import get_db
from app.models.schemas_db import DataSource

router = APIRouter()


@router.get("/status")
def get_datasource_status(db: Session = Depends(get_db)):
    """Get status of all registered data sources."""
    sources = db.query(DataSource).all()
    return {
        "total_sources": len(sources),
        "active": sum(1 for s in sources if s.status == "active"),
        "sources": [
            {
                "name": s.name,
                "type": s.source_type,
                "url": s.url,
                "status": s.status,
                "record_count": s.record_count or 0,
                "last_sync": s.last_sync.isoformat() if s.last_sync else None,
                "update_frequency": s.update_frequency,
                "requires_key": bool(s.requires_key),
                "is_free": bool(s.is_free),
            }
            for s in sources
        ],
    }


@router.get("/exchange-rates")
def get_exchange_rates():
    """Get latest exchange rates for ASEAN + China currencies."""
    try:
        from app.data.exchange_rate_client import get_rates_summary
        return get_rates_summary()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Exchange rate service unavailable: {e}")


@router.get("/macro/{country_code}")
def get_macro_profile(country_code: str):
    """Get macroeconomic profile for a specific country.

    Args:
        country_code: ISO alpha-3 code (e.g. CHN, VNM, THA)
    """
    try:
        from app.data.worldbank_client import get_country_profile
        profile = get_country_profile(country_code)
        return {"country": country_code, "indicators": profile}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"World Bank API unavailable: {e}")


@router.get("/comtrade/summary")
def get_comtrade_summary(partner: str = "VNM", year: str = "2023"):
    """Get trade summary from UN Comtrade.

    Args:
        partner: Partner country ISO code (default: Vietnam)
        year: Year (default: 2023)
    """
    try:
        from app.data.comtrade_client import get_trade_summary
        from app.data.etl import COUNTRY_MAP
        m49 = COUNTRY_MAP.get(partner, {}).get("m49")
        if not m49:
            raise HTTPException(status_code=400, detail=f"Unknown country code: {partner}")
        summary = get_trade_summary("156", m49, year)
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Comtrade API unavailable: {e}")


@router.get("/commodity-prices")
def get_commodity_prices():
    """Get latest commodity price summary from IMF."""
    try:
        from app.data.commodity_client import get_commodity_summary
        summary = get_commodity_summary()
        return {"commodities": summary, "source": "IMF Primary Commodity Prices"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Commodity price service unavailable: {e}")


@router.get("/imf-validation")
def validate_trade_data(partner: str = "VNM", year: str = "2023"):
    """Cross-validate Comtrade vs IMF DOTS data.

    Args:
        partner: Partner country ISO code
        year: Year
    """
    try:
        from app.data.imf_client import validate_comtrade_data
        from app.data.comtrade_client import get_trade_summary
        from app.data.etl import COUNTRY_MAP

        m49 = COUNTRY_MAP.get(partner, {}).get("m49")
        if not m49:
            raise HTTPException(status_code=400, detail=f"Unknown country code: {partner}")

        comtrade = get_trade_summary("156", m49, year)
        validation = validate_comtrade_data(
            comtrade.get("total_export_usd", 0), "CHN", partner, year
        )
        return {
            "partner": partner,
            "year": year,
            "comtrade_exports": comtrade.get("total_export_usd", 0),
            "validation": validation,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Validation failed: {e}")


@router.post("/refresh")
def refresh_data(db: Session = Depends(get_db)):
    """Trigger a data refresh from all API sources."""
    try:
        from app.data.cache import clear_all
        clear_all()
        return {"status": "success", "message": "Cache cleared. New data will be fetched on next request."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {e}")
