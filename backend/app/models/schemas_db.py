"""SQLAlchemy ORM models for trade data."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime
from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TradeRecord(Base):
    __tablename__ = "trade_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False)
    reporter = Column(String(10), nullable=False, default="CHN")
    partner = Column(String(10), nullable=False, index=True)
    hs_code = Column(String(10), nullable=False, index=True)
    hs_chapter = Column(Integer)
    hs_section = Column(String(50))
    trade_value_usd = Column(Float, nullable=False)
    quantity = Column(Float)
    unit = Column(String(20))
    trade_flow = Column(String(10), default="export")
    source = Column(String(50), default="mock", index=True)  # Data source: mock, UN Comtrade, IMF, etc.
    created_at = Column(DateTime, default=_utcnow)


class Country(Base):
    __tablename__ = "countries"

    code = Column(String(10), primary_key=True)
    name_cn = Column(String(50), nullable=False)
    name_en = Column(String(80), nullable=False)
    asean_member = Column(Integer, default=0)
    rcep_member = Column(Integer, default=0)
    gdp_billion_usd = Column(Float)
    population_million = Column(Float)
    latitude = Column(Float)
    longitude = Column(Float)


class Product(Base):
    __tablename__ = "products"

    hs_code = Column(String(10), primary_key=True)
    hs_name_cn = Column(String(100))
    hs_name_en = Column(String(150))
    hs_chapter = Column(Integer)
    hs_section = Column(String(50))
    is_agricultural = Column(Integer, default=0)
    is_industrial = Column(Integer, default=0)
    is_consumer_goods = Column(Integer, default=0)


class TariffRule(Base):
    __tablename__ = "tariff_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hs_code = Column(String(10), nullable=False, index=True)
    partner_country = Column(String(10), nullable=False)
    mfn_rate = Column(Float)
    rcep_rate = Column(Float)
    fta_rate = Column(Float)
    rule_of_origin = Column(String(500))
    valid_from = Column(String(10))
    valid_to = Column(String(10))


class DataSource(Base):
    """Metadata table tracking available data sources and their status."""
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    source_type = Column(String(50), nullable=False)  # api, file, scrape
    url = Column(String(500))
    description = Column(String(500))
    status = Column(String(20), default="active")  # active, inactive, error
    last_sync = Column(DateTime)
    record_count = Column(Integer, default=0)
    update_frequency = Column(String(50))  # daily, monthly, annual
    requires_key = Column(Integer, default=0)
    is_free = Column(Integer, default=1)
    created_at = Column(DateTime, default=_utcnow)