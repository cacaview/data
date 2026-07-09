"""Pydantic response schemas."""

from pydantic import BaseModel


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
    category: str | None = None


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
    country: str | None = None
    product: str | None = None


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
    growth: float | None = None
    share: float | None = None


# ── AI Prediction ──
class PredictionPoint(BaseModel):
    date: str
    actual: float | None = None
    predicted: float | None = None
    lower: float | None = None
    upper: float | None = None


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
    level: str  # high / medium / low
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
    fta_rate: float | None
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
    declared_value_usd: float | None = None
    applicable_rate: float | None = None
    applicable_basis: str | None = None
    duty_usd: float | None = None
    savings_vs_mfn_usd: float | None = None


# ── Chat ──
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    # Frontend-aligned alias — page code reads `data.answer || data.content || data.message`.
    answer: str | None = None
    chart_type: str | None = None
    chart_data: dict | None = None

    def model_post_init(self, __context):
        # Auto-mirror `reply` into `answer` when not explicitly set,
        # so frontend pages that read `data.answer` keep working.
        if self.answer is None:
            self.answer = self.reply


# ── Data Assets ──
class LineageNode(BaseModel):
    id: str
    label: str
    type: str  # source / process / store / output
    x: float
    y: float


class LineageEdge(BaseModel):
    source: str
    target: str


class LineageGraph(BaseModel):
    nodes: list[LineageNode]
    edges: list[LineageEdge]


class QualityMetric(BaseModel):
    dimension: str  # completeness / accuracy / timeliness / consistency
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


# ── Advanced Time Series Forecasting ──
class ForecastPoint(BaseModel):
    date: str
    actual: float | None = None
    predicted: float | None = None
    lower: float | None = None
    upper: float | None = None


class ForecastResult(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_name: str
    model_params: dict = {}
    mape: float
    rmse: float
    aic: float | None = None
    data: list[ForecastPoint]


class DecompositionResult(BaseModel):
    trend: list[float]
    seasonal: list[float]
    residual: list[float]
    dates: list[str]
    period: int
    strength_of_trend: float


# ── Correlation & Cointegration ──
class CorrelationMatrix(BaseModel):
    entities: list[str]
    matrix: list[list[float]]
    method: str = "pearson"


class CointegrationResult(BaseModel):
    series_a_name: str
    series_b_name: str
    cointegrated: bool
    test_statistic: float
    p_value: float
    critical_values: dict = {}


class ClusterResult(BaseModel):
    id: int
    members: list[str]
    centroid: list[float]
    label: str


class ClusteringResult(BaseModel):
    clusters: list[ClusterResult]
    explained_variance: float
    n_clusters: int


# ── Multi-Factor Analysis ──
class FactorContribution(BaseModel):
    name: str
    value: float
    percentage: float
    direction: str  # "positive" / "negative"


class AttributionResult(BaseModel):
    factors: list[FactorContribution]
    total_change: float
    unexplained: float
    r_squared: float
    period: str


class SeasonalIndex(BaseModel):
    month: int
    index: float
    label: str


class FactorReport(BaseModel):
    partner: str | None = None
    seasonal_indices: list[SeasonalIndex]
    elasticity: float | None = None
    exchange_rate_impact: float = 0.0
    description: str = ""


# ── Trading Signals ──
class SignalDetail(BaseModel):
    value: float = 0.0
    trend: str = "neutral"
    strength: float = 0.0
    zone: str = "neutral"
    regime: str = "medium"
    signal: str = "hold"
    description: str = ""


class SignalHistory(BaseModel):
    month: str
    composite_score: float
    action: str


class SignalReport(BaseModel):
    composite_score: float
    action: str  # BUY / HOLD / SELL
    confidence: float
    signals: dict[str, SignalDetail] = {}
    history: list[SignalHistory] = []
    description: str = ""


# ── Portfolio Optimization ──
class PortfolioWeight(BaseModel):
    name: str
    current_weight: float
    optimal_weight: float
    risk_contribution: float


class EfficientFrontierPoint(BaseModel):
    risk: float
    return_rate: float
    sharpe_ratio: float
    weights: dict[str, float]


class PortfolioResult(BaseModel):
    hhi_current: float
    hhi_optimal: float
    weights: list[PortfolioWeight]
    efficient_frontier: list[EfficientFrontierPoint]
    optimal_sharpe: float
    diversification_benefit: float


# ── Value at Risk ──
class VaRResult(BaseModel):
    confidence_level: float
    var_historical: float
    var_parametric: float
    cvar: float
    max_drawdown: float
    volatility: float
    risk_contributions: list[dict] = []
    stress_tests: list[dict] = []


# ── Backtesting ──
class ScenarioConfig(BaseModel):
    name: str
    description: str = ""
    tariff_change_pct: float | None = None
    fx_change_pct: float | None = None
    demand_change_pct: float | None = None


class BacktestResult(BaseModel):
    scenario: ScenarioConfig
    baseline_total: float
    simulated_total: float
    impact_pct: float
    impact_usd: float
    winners: list[dict] = []
    losers: list[dict] = []
    sensitivity: list[dict] = []


# ── Enterprise Risk ──
class SupplyChainRisk(BaseModel):
    country: str
    risk_score: float
    risk_level: str  # high / medium / low
    factors: dict = {}
    recommendation: str = ""


class ComplianceCheck(BaseModel):
    entity: str
    status: str  # clear / flagged / unknown
    lists_checked: list[str] = []
    details: str = ""
