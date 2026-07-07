"""Initialize database with real data sources, falling back to mock data.

Startup flow:
1. Create tables if not exist
2. Initialize country data (fast)
3. Try fetching real data from APIs:
   - Exchange rates (fast, ~1s)
   - World Bank macro data (fast, ~5s)
   - UN Comtrade trade data (rate limited, may fail)
4. If real data unavailable, use mock data as fallback
5. Register data source metadata
"""
import os
import sys
import logging
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models.database import engine, SessionLocal, Base
from app.models.schemas_db import TradeRecord, Country, Product, TariffRule, DataSource
from app.mock_data.trade_generator import generate_all

logger = logging.getLogger(__name__)

# Data source registry
DATA_SOURCES = [
    {
        "name": "UN Comtrade",
        "source_type": "api",
        "url": "https://comtradeapi.un.org",
        "description": "联合国商品贸易统计数据库，200+国家HS6级双边贸易数据",
        "update_frequency": "monthly",
        "requires_key": 0,
        "is_free": 1,
    },
    {
        "name": "World Bank Open Data",
        "source_type": "api",
        "url": "https://api.worldbank.org/v2/",
        "description": "世界银行开放数据，GDP/人口/FDI/贸易占比等宏观经济指标",
        "update_frequency": "annual",
        "requires_key": 0,
        "is_free": 1,
    },
    {
        "name": "IMF DOTS",
        "source_type": "api",
        "url": "http://dataservices.imf.org/REST/SDMX_JSON.svc/",
        "description": "IMF贸易方向统计，双边贸易流量验证数据",
        "update_frequency": "monthly",
        "requires_key": 0,
        "is_free": 1,
    },
    {
        "name": "ExchangeRate-API",
        "source_type": "api",
        "url": "https://open.er-api.com/v6/latest/USD",
        "description": "实时汇率数据，覆盖11种东盟+中国货币",
        "update_frequency": "daily",
        "requires_key": 0,
        "is_free": 1,
    },
    {
        "name": "IMF Commodity Prices",
        "source_type": "api",
        "url": "https://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/PIT",
        "description": "IMF初级产品价格，80+商品月度价格（棕榈油/橡胶/原油等）",
        "update_frequency": "monthly",
        "requires_key": 0,
        "is_free": 1,
    },
    {
        "name": "广西公共数据开放平台",
        "source_type": "api",
        "url": "https://data.gxzf.gov.cn",
        "description": "广西数据开放平台，604个API，含商务厅/南宁海关/贸促会数据",
        "update_frequency": "varies",
        "requires_key": 1,
        "is_free": 1,
    },
    {
        "name": "北部湾港数据",
        "source_type": "api",
        "url": "http://yqb.gxzf.gov.cn/sjfb/sjxz/",
        "description": "北部湾港月度货物/集装箱吞吐量",
        "update_frequency": "monthly",
        "requires_key": 0,
        "is_free": 1,
    },
    {
        "name": "RCEP/ACFTA关税数据库",
        "source_type": "file",
        "url": "https://asean.mendel-online.com",
        "description": "RCEP/ACFTA关税减让表，原产地规则，降税时间表",
        "update_frequency": "annual",
        "requires_key": 0,
        "is_free": 1,
    },
    {
        "name": "BDI航运指数",
        "source_type": "api",
        "url": "https://finance.yahoo.com/quote/%5EBDIY",
        "description": "波罗的海干散货指数，反映国际航运成本",
        "update_frequency": "daily",
        "requires_key": 0,
        "is_free": 1,
    },
]


def _register_data_sources(db):
    """Register all data sources in the metadata table."""
    for src in DATA_SOURCES:
        existing = db.query(DataSource).filter(DataSource.name == src["name"]).first()
        if not existing:
            db.add(DataSource(**src))
    db.commit()
    logger.info("Registered %d data sources", len(DATA_SOURCES))


def _init_with_mock_data(db, data):
    """Load mock data into database as fallback."""
    # Insert countries
    for c in data["countries"]:
        existing = db.query(Country).filter(Country.code == c.get("code")).first()
        if not existing:
            db.add(Country(**c))
    db.commit()
    print(f"  [MOCK] {len(data['countries'])} countries")

    # Insert products
    for p in data["products"]:
        existing = db.query(Product).filter(Product.hs_code == p.get("hs_code")).first()
        if not existing:
            db.add(Product(**p))
    db.commit()
    print(f"  [MOCK] {len(data['products'])} products")

    # Insert trade records (mark as mock source)
    batch_size = 5000
    records = data["trade_records"]
    for r in records:
        r["source"] = "mock"
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        db.bulk_insert_mappings(TradeRecord, batch)
        db.commit()
        print(f"  [MOCK] Trade records: {min(i + batch_size, len(records))}/{len(records)}")

    # Insert tariff rules
    for t in data["tariff_rules"]:
        db.add(TariffRule(**t))
    db.commit()
    print(f"  [MOCK] {len(data['tariff_rules'])} tariff rules")


def _try_fetch_real_data(db):
    """Attempt to fetch real data from APIs. Returns True if successful."""
    try:
        from app.data.etl import init_country_data
        from app.data import exchange_rate_client

        # Step 1: Country data (always works, instant)
        print("[REAL] Initializing country data...")
        init_country_data(db)

        # Step 2: Exchange rates (fast, ~1s, reliable)
        print("[REAL] Fetching exchange rates...")
        try:
            rates = exchange_rate_client.get_latest_rates()
            if rates:
                print(f"  [OK] {len(rates) - 3} exchange rates fetched")
            else:
                print("  [WARN] Exchange rates unavailable, continuing...")
        except Exception as e:
            print(f"  [WARN] Exchange rates failed: {e}")

        # Skip slow APIs on startup (World Bank, Comtrade)
        # These will be fetched on-demand via /api/datasources endpoints
        print("[REAL] Fast init complete. Slow APIs available via /api/datasources/*")

        # Load tariff data from RCEP/ACFTA rules
        try:
            from app.data.tariff_loader import load_tariff_data
            print("[REAL] Loading RCEP/ACFTA tariff data...")
            load_tariff_data(db)
            print("  [OK] Tariff data loaded")
        except Exception as e:
            print(f"  [WARN] Tariff loader failed: {e}")

        return False  # Use mock data for trade records on startup

    except Exception as e:
        logger.error("Real data fetch failed: %s", e)
        print(f"[ERROR] Real data fetch failed: {e}")
        return False


def init_database():
    """Create tables and populate with real or mock data."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Register data source metadata (always)
        _register_data_sources(db)

        # Skip if trade data already exists
        if db.query(TradeRecord).count() > 0:
            print("[INIT] Database already populated, skipping data generation.")
            return

        print("[INIT] Database empty, attempting real data sources...")

        # Try real data first
        real_success = _try_fetch_real_data(db)

        # Fall back to mock if real data incomplete
        if not real_success:
            print("\n[FALLBACK] Using mock data for remaining tables...")
            data = generate_all()
            _init_with_mock_data(db, data)

        # Update data source record counts
        trade_count = db.query(TradeRecord).count()
        for src in db.query(DataSource).all():
            count = db.query(TradeRecord).filter(TradeRecord.source == src.name).count()
            src.record_count = count
            src.last_sync = datetime.utcnow()
            src.status = "active" if count > 0 else "inactive"
        db.commit()

        print(f"\n[INIT] Database initialization complete! Total records: {trade_count}")

    finally:
        db.close()


if __name__ == "__main__":
    init_database()
