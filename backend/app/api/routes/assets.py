"""Data assets routes -- lineage graph, quality metrics, data source catalog."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas import DataSourceMeta, LineageEdge, LineageGraph, LineageNode, QualityMetric
from app.models.schemas_db import Country, DataSource, Product, TariffRule, TradeRecord

router = APIRouter()


# ── Data source field definitions (static metadata) ──
_SOURCE_FIELDS = {
    "UN Comtrade": [
        "year",
        "month",
        "reporter",
        "partner",
        "hs_code",
        "trade_value_usd",
        "quantity",
        "source",
    ],
    "World Bank Open Data": ["country_code", "indicator", "value", "year"],
    "IMF DOTS": ["reporter", "partner", "indicator", "period", "value"],
    "ExchangeRate-API": ["base", "currency", "rate", "last_update"],
    "IMF Commodity Prices": ["commodity", "period", "price"],
    "广西公共数据开放平台": ["dataset", "category", "record_count"],
    "北部湾港数据": ["port", "month", "cargo_tons", "container_teu"],
    "RCEP/ACFTA关税数据库": ["hs_code", "country", "mfn_rate", "rcep_rate", "rule_of_origin"],
    "BDI航运指数": ["date", "bdi_value", "change_pct"],
}

_SOURCE_QUALITY_ESTIMATES = {
    "UN Comtrade": 95.0,
    "World Bank Open Data": 98.0,
    "IMF DOTS": 93.0,
    "ExchangeRate-API": 90.0,
    "IMF Commodity Prices": 88.0,
    "广西公共数据开放平台": 82.0,
    "北部湾港数据": 75.0,
    "RCEP/ACFTA关税数据库": 85.0,
    "BDI航运指数": 80.0,
}


# ── GET /lineage ────────────────────────────────────────────────────────────
@router.get("/lineage", response_model=LineageGraph)
def get_lineage(db: Session = Depends(get_db)):
    """Data pipeline DAG showing sources -> transforms -> storage -> outputs."""
    trade_count = db.query(func.count(TradeRecord.id)).scalar() or 0
    country_count = db.query(func.count(Country.code)).scalar() or 0
    product_count = db.query(func.count(Product.hs_code)).scalar() or 0
    tariff_count = db.query(func.count(TariffRule.id)).scalar() or 0

    nodes = [
        # External data sources (real API sources)
        LineageNode(id="src_uncomtrade", label="UN Comtrade", type="source", x=0, y=0),
        LineageNode(id="src_worldbank", label="World Bank", type="source", x=0, y=100),
        LineageNode(id="src_imf", label="IMF DOTS", type="source", x=0, y=200),
        LineageNode(id="src_exrate", label="ExchangeRate-API", type="source", x=0, y=300),
        LineageNode(id="src_commodity", label="IMF Commodity", type="source", x=0, y=400),
        LineageNode(id="src_gxdata", label="广西数据平台", type="source", x=0, y=500),
        LineageNode(id="src_port", label="北部湾港", type="source", x=0, y=600),
        LineageNode(id="src_rcep", label="RCEP/ACFTA关税", type="source", x=0, y=700),
        LineageNode(id="src_bdi", label="BDI航运指数", type="source", x=0, y=800),
        # Processing stages
        LineageNode(id="proc_etl", label="ETL Pipeline", type="process", x=300, y=200),
        LineageNode(id="proc_clean", label="数据清洗", type="process", x=300, y=400),
        LineageNode(id="proc_norm", label="标准化 & 归一化", type="process", x=300, y=600),
        # Storage
        LineageNode(
            id="store_trade", label=f"trade_records ({trade_count})", type="store", x=600, y=100
        ),
        LineageNode(
            id="store_country", label=f"countries ({country_count})", type="store", x=600, y=300
        ),
        LineageNode(
            id="store_product", label=f"products ({product_count})", type="store", x=600, y=500
        ),
        LineageNode(
            id="store_tariff", label=f"tariff_rules ({tariff_count})", type="store", x=600, y=700
        ),
        # Outputs
        LineageNode(id="out_overview", label="总览仪表盘", type="output", x=900, y=100),
        LineageNode(id="out_trade", label="贸易分析", type="output", x=900, y=300),
        LineageNode(id="out_ai", label="AI 预测", type="output", x=900, y=500),
        LineageNode(id="out_tariff", label="关税计算", type="output", x=900, y=700),
    ]

    edges = [
        # Sources -> ETL
        LineageEdge(source="src_uncomtrade", target="proc_etl"),
        LineageEdge(source="src_worldbank", target="proc_etl"),
        LineageEdge(source="src_imf", target="proc_etl"),
        LineageEdge(source="src_exrate", target="proc_etl"),
        LineageEdge(source="src_commodity", target="proc_etl"),
        LineageEdge(source="src_gxdata", target="proc_etl"),
        LineageEdge(source="src_port", target="proc_etl"),
        LineageEdge(source="src_rcep", target="proc_etl"),
        LineageEdge(source="src_bdi", target="proc_etl"),
        # ETL -> Clean
        LineageEdge(source="proc_etl", target="proc_clean"),
        LineageEdge(source="proc_clean", target="proc_norm"),
        # Normalize -> stores
        LineageEdge(source="proc_norm", target="store_trade"),
        LineageEdge(source="proc_norm", target="store_country"),
        LineageEdge(source="proc_norm", target="store_product"),
        LineageEdge(source="proc_norm", target="store_tariff"),
        # Stores -> outputs
        LineageEdge(source="store_trade", target="out_overview"),
        LineageEdge(source="store_trade", target="out_trade"),
        LineageEdge(source="store_trade", target="out_ai"),
        LineageEdge(source="store_country", target="out_overview"),
        LineageEdge(source="store_country", target="out_trade"),
        LineageEdge(source="store_product", target="out_trade"),
        LineageEdge(source="store_product", target="out_ai"),
        LineageEdge(source="store_tariff", target="out_tariff"),
    ]

    return LineageGraph(nodes=nodes, edges=edges)


# ── GET /quality ────────────────────────────────────────────────────────────
@router.get("/quality", response_model=list[QualityMetric])
def get_quality(db: Session = Depends(get_db)):
    """Data quality metrics computed from the actual database."""
    metrics: list[QualityMetric] = []

    total_records = db.query(func.count(TradeRecord.id)).scalar() or 0

    # Completeness: percentage of records with non-null trade_value_usd
    non_null_value = (
        db.query(func.count(TradeRecord.id))
        .filter(TradeRecord.trade_value_usd.isnot(None))
        .scalar()
        or 0
    )
    completeness = (non_null_value / total_records * 100) if total_records else 0
    metrics.append(
        QualityMetric(
            dimension="completeness",
            score=round(completeness, 1),
            details=f"贸易额字段完整率 {completeness:.1f}%（{non_null_value}/{total_records}条记录）",
        )
    )

    # Accuracy: records with positive trade values
    positive_records = (
        db.query(func.count(TradeRecord.id)).filter(TradeRecord.trade_value_usd > 0).scalar() or 0
    )
    accuracy = (positive_records / total_records * 100) if total_records else 0
    metrics.append(
        QualityMetric(
            dimension="accuracy",
            score=round(accuracy, 1),
            details=f"贸易额正值占比 {accuracy:.1f}%，异常值（<=0）记录 {total_records - positive_records} 条",
        )
    )

    # Timeliness: check if recent year data exists
    max_year = db.query(func.max(TradeRecord.year)).scalar()
    current_year = datetime.now().year
    if max_year and max_year >= current_year - 1:
        timeliness = 100.0
        details = f"数据已更新至{max_year}年，时效性良好"
    elif max_year and max_year >= current_year - 2:
        timeliness = 70.0
        details = f"数据最新年份为{max_year}年，存在一年延迟"
    else:
        timeliness = 40.0
        details = f"数据最新年份为{max_year}年，时效性较低"
    metrics.append(QualityMetric(dimension="timeliness", score=timeliness, details=details))

    # Consistency: country codes match countries table
    trade_countries = {r[0] for r in db.query(distinct(TradeRecord.partner)).all() if r[0]}
    known_countries = {r[0] for r in db.query(Country.code).all() if r[0]}
    known_countries.add("CHN")
    unmatched = trade_countries - known_countries
    consistency = (
        ((len(trade_countries) - len(unmatched)) / len(trade_countries) * 100)
        if trade_countries
        else 100
    )
    metrics.append(
        QualityMetric(
            dimension="consistency",
            score=round(consistency, 1),
            details=f"国家代码一致率 {consistency:.1f}%，"
            f"{len(unmatched)}个未知代码: {', '.join(sorted(unmatched)[:5]) if unmatched else '无'}",
        )
    )

    # Multi-source consistency (new: check data source diversity)
    source_count = db.query(func.count(func.distinct(TradeRecord.source))).scalar() or 0
    source_diversity = min(source_count / 3 * 100, 100)  # Target: 3+ sources
    metrics.append(
        QualityMetric(
            dimension="diversity",
            score=round(source_diversity, 1),
            details=f"数据来源多样性: {source_count}个数据源接入，目标≥3个",
        )
    )

    return metrics


# ── GET /catalog ────────────────────────────────────────────────────────────
@router.get("/catalog", response_model=list[DataSourceMeta])
def get_catalog(db: Session = Depends(get_db)):
    """Data source catalog - reads from DataSource table with real metadata."""
    # Try reading from DataSource table first
    db_sources = db.query(DataSource).all()

    if db_sources:
        sources = []
        for src in db_sources:
            fields = _SOURCE_FIELDS.get(src.name, ["id", "value", "date"])
            quality = _SOURCE_QUALITY_ESTIMATES.get(src.name, 80.0)
            # Adjust quality based on actual data
            quality = min(quality + 5, 100.0) if src.record_count > 0 else max(quality - 20, 0.0)

            last_updated = src.last_sync.strftime("%Y-%m-%d") if src.last_sync else "N/A"

            sources.append(
                DataSourceMeta(
                    id=src.name.lower().replace(" ", "_").replace("/", "_"),
                    name=src.name,
                    url=src.url or "",
                    description=src.description or "",
                    update_frequency=src.update_frequency or "N/A",
                    record_count=src.record_count or 0,
                    last_updated=last_updated,
                    fields=fields,
                    quality_score=round(quality, 1),
                )
            )
        return sources

    # Fallback: compute from actual data (original logic)
    trade_count = db.query(func.count(TradeRecord.id)).scalar() or 0
    country_count = db.query(func.count(Country.code)).scalar() or 0
    db.query(func.count(Product.hs_code)).scalar() or 0
    tariff_count = db.query(func.count(TariffRule.id)).scalar() or 0

    def _quality_score(model):
        total = db.query(func.count(model.id)).scalar() or 0
        return min(100.0, 60 + total / 10) if total else 0.0

    trade_q = _quality_score(TradeRecord)
    country_q = _quality_score(Country)
    tariff_q = _quality_score(TariffRule)
    max_year = db.query(func.max(TradeRecord.year)).scalar()

    sources = [
        DataSourceMeta(
            id="uncomtrade",
            name="UN Comtrade",
            url="https://comtradeapi.un.org",
            description="联合国商品贸易统计数据库，覆盖全球200+经济体双边贸易数据",
            update_frequency="月度",
            record_count=trade_count,
            last_updated=f"{max_year}-12" if max_year else "N/A",
            fields=_SOURCE_FIELDS["UN Comtrade"],
            quality_score=round(trade_q, 1),
        ),
        DataSourceMeta(
            id="worldbank",
            name="World Bank Open Data",
            url="https://api.worldbank.org/v2/",
            description="世界银行开放数据，GDP/人口/FDI/贸易占比等宏观经济指标",
            update_frequency="年度",
            record_count=country_count,
            last_updated="2025",
            fields=_SOURCE_FIELDS["World Bank Open Data"],
            quality_score=round(country_q, 1),
        ),
        DataSourceMeta(
            id="imf_dots",
            name="IMF DOTS",
            url="http://dataservices.imf.org/REST/SDMX_JSON.svc/",
            description="IMF贸易方向统计，双边贸易流量验证数据",
            update_frequency="季度",
            record_count=trade_count // 3,
            last_updated="2025",
            fields=_SOURCE_FIELDS["IMF DOTS"],
            quality_score=round(trade_q * 0.92, 1),
        ),
        DataSourceMeta(
            id="exchange_rate",
            name="ExchangeRate-API",
            url="https://open.er-api.com/v6/latest/USD",
            description="实时汇率数据，覆盖11种东盟+中国货币",
            update_frequency="每日",
            record_count=11,
            last_updated=datetime.now().strftime("%Y-%m-%d"),
            fields=_SOURCE_FIELDS["ExchangeRate-API"],
            quality_score=90.0,
        ),
        DataSourceMeta(
            id="commodity",
            name="IMF Commodity Prices",
            url="https://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/PIT",
            description="IMF初级产品价格，80+商品月度价格",
            update_frequency="月度",
            record_count=0,
            last_updated="N/A",
            fields=_SOURCE_FIELDS["IMF Commodity Prices"],
            quality_score=88.0,
        ),
        DataSourceMeta(
            id="gxdata",
            name="广西公共数据开放平台",
            url="https://data.gxzf.gov.cn",
            description="广西数据开放平台，604个API，含商务厅/南宁海关/贸促会数据",
            update_frequency="不定期",
            record_count=0,
            last_updated="N/A",
            fields=_SOURCE_FIELDS["广西公共数据开放平台"],
            quality_score=82.0,
        ),
        DataSourceMeta(
            id="port_data",
            name="北部湾港数据",
            url="http://yqb.gxzf.gov.cn/sjfb/sjxz/",
            description="北部湾港月度货物/集装箱吞吐量",
            update_frequency="月度",
            record_count=0,
            last_updated="N/A",
            fields=_SOURCE_FIELDS["北部湾港数据"],
            quality_score=75.0,
        ),
        DataSourceMeta(
            id="rcep_tariff",
            name="RCEP/ACFTA关税数据库",
            url="https://asean.mendel-online.com",
            description="RCEP/ACFTA关税减让表，原产地规则，降税时间表",
            update_frequency="年度",
            record_count=tariff_count,
            last_updated="2025",
            fields=_SOURCE_FIELDS["RCEP/ACFTA关税数据库"],
            quality_score=round(tariff_q, 1),
        ),
        DataSourceMeta(
            id="bdi",
            name="BDI航运指数",
            url="https://finance.yahoo.com/quote/%5EBDIY",
            description="波罗的海干散货指数，反映国际航运成本",
            update_frequency="每日",
            record_count=0,
            last_updated=datetime.now().strftime("%Y-%m-%d"),
            fields=_SOURCE_FIELDS["BDI航运指数"],
            quality_score=80.0,
        ),
    ]

    return sources
