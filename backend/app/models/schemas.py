"""Pydantic response schemas."""
from pydantic import BaseModel
from typing import Optional


# ── Overview ──
class KPISummary(BaseModel):
    total_trade_value: float
    yoy_growth: float
    partner_count: int
    product_categories: int
    top_partner: str
    top_product: str
    # Frontend-aligned fields (kept in sync with the singular ones above):
    top_partners: list[dict] = []
    monthly_trend: list[dict] = []
    top_growth_products: list[dict] = []
    rcep_utilization: float = 0.0


class TradeMapPoint(BaseModel):
    country_code: str
    country_name: str
    latitude: float
    longitude: float
    trade_value: float
    growth_rate: float
    top_products: list[str]


class TradeMapArc(BaseModel):
    from_code: str
    to_code: str
    from_name: str
    to_name: str
    trade_value: float
    coords: list[list[float]]


class SankeyNode(BaseModel):
    name: str
    category: Optional[str] = None


class SankeyLink(BaseModel):
    source: str
    target: str
    value: float


class SankeyData(BaseModel):
    nodes: list[SankeyNode]
    links: list[SankeyLink]


# ── Trade Analysis ──
class TrendPoint(BaseModel):
    date: str
    value: float
    country: Optional[str] = None
    product: Optional[str] = None


class CountryRadar(BaseModel):
    country: str
    trade_volume: float
    growth_rate: float
    interdependence: float
    diversity: float
    rcep_utilization: float


class RankingItem(BaseModel):
    name: str
    value: float
    growth: Optional[float] = None
    share: Optional[float] = None


# ── AI Prediction ──
class PredictionPoint(BaseModel):
    date: str
    actual: Optional[float] = None
    predicted: Optional[float] = None
    lower: Optional[float] = None
    upper: Optional[float] = None


class PredictionResult(BaseModel):
    model_config = {"protected_namespaces": ()}  # allow model_ prefix
    model_name: str
    mape: float
    data: list[PredictionPoint]


class ClusterItem(BaseModel):
    hs_code: str
    name: str
    trade_value: float
    growth_rate: float
    cluster: int
    cluster_label: str


class RiskAlert(BaseModel):
    date: str
    level: str          # high / medium / low
    country: str
    description: str
    suggestion: str
    metric_value: float


# ── Tariff ──
class TariffRequest(BaseModel):
    hs_code: str
    origin_country: str
    target_country: str
    value_usd: float


class TariffResult(BaseModel):
    # Backend-native fields
    hs_code: str
    product_name: str
    origin_country: str
    target_country: str
    mfn_rate: float
    rcep_rate: float
    fta_rate: Optional[float]
    best_rate: float
    best_scheme: str
    value_usd: float
    duty_mfn: float
    duty_best: float
    savings: float
    savings_pct: float
    rule_of_origin: str
    cumulation_rule: str
    # Frontend-aligned aliases (kept in sync with the backend-native fields)
    declared_value_usd: Optional[float] = None
    applicable_rate: Optional[float] = None
    applicable_basis: Optional[str] = None
    duty_usd: Optional[float] = None
    savings_vs_mfn_usd: Optional[float] = None


# ── Chat ──
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    # Frontend-aligned alias — page code reads `data.answer || data.content || data.message`.
    answer: Optional[str] = None
    chart_type: Optional[str] = None
    chart_data: Optional[dict] = None

    def model_post_init(self, __context):
        # Auto-mirror `reply` into `answer` when not explicitly set,
        # so frontend pages that read `data.answer` keep working.
        if self.answer is None:
            self.answer = self.reply


# ── Data Assets ──
class LineageNode(BaseModel):
    id: str
    label: str
    type: str    # source / process / store / output
    x: float
    y: float


class LineageEdge(BaseModel):
    source: str
    target: str


class LineageGraph(BaseModel):
    nodes: list[LineageNode]
    edges: list[LineageEdge]


class QualityMetric(BaseModel):
    dimension: str   # completeness / accuracy / timeliness / consistency
    score: float
    details: str


class DataSourceMeta(BaseModel):
    id: str
    name: str
    url: str
    description: str
    update_frequency: str
    record_count: int
    last_updated: str
    fields: list[str]
    quality_score: float
