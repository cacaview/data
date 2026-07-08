// Domain type definitions for ACTAP frontend.
// Mirror the Pydantic response models from the backend.

export interface OverviewSummary {
  total_trade_usd: number;
  year_over_year_growth: number;
  top_partners: { code: string; name: string; value: number; share: number }[];
  monthly_trend: { month: string; value: number }[];
  top_growth_products: { hs_section: string; growth_pct: number }[];
  rcep_utilization: number;
}

export interface TradeMapNode {
  code: string;
  name: string;
  lat: number;
  lng: number;
  value: number;
}

export interface TradeMapLink {
  source: string;
  target: string;
  value: number;
}

export interface TradeMapData {
  nodes: TradeMapNode[];
  links: TradeMapLink[];
}

export interface SankeyNode {
  name: string;
  category: 'country' | 'product';
}

export interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

export interface SankeyData {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

export interface TrendPoint {
  date: string;
  value: number;
  country: string;
}

export interface CountryRadar {
  country: string;
  trade_volume: number;
  growth_rate: number;
  interdependence: number;
  diversity: number;
  rcep_utilization: number;
}

export interface RankingItem {
  name: string;
  value: number;
  growth: number | null;
  share: number | null;
}

export interface PredictionPoint {
  date: string;
  predicted: number;
  lower: number;
  upper: number;
}

export interface PredictionResult {
  model_name: string;
  country: string;
  horizon_months: number;
  history: TrendPoint[];
  forecast: PredictionPoint[];
  metrics: {
    rmse: number;
    mape: number;
  };
}

export interface ClusterItem {
  cluster_id: number;
  cluster_label: string;
  products: { hs_code: string; name: string; trade_value: number }[];
  total_value: number;
}

export interface ClusteringResult {
  clusters: ClusterItem[];
  total_products: number;
}

export interface RiskAlert {
  type: 'yoy_drop' | 'volatility' | 'concentration' | 'partner_risk';
  severity: 'high' | 'medium' | 'low';
  country?: string;
  product?: string;
  description: string;
  metric_value: number;
  reference_value: number;
}

export interface RiskAlertsResult {
  alerts: RiskAlert[];
  total: number;
  by_severity: { high: number; medium: number; low: number };
}

export interface TariffInput {
  hs_code: string;
  origin_country: string;
  target_country: string;
  value_usd: number;
}

export interface TariffResult {
  hs_code: string;
  origin_country: string;
  target_country: string;
  declared_value_usd: number;
  mfn_rate: number;
  applicable_rate: number;
  applicable_basis: 'rcep' | 'fta' | 'mfn' | 'zero';
  duty_usd: number;
  savings_vs_mfn_usd: number;
  rule_of_origin: string | null;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface ChatResponse {
  reply: string;
  sources: { title: string; snippet: string }[];
  model: string;
}

export interface DataSourceInfo {
  name: string;
  type: 'api' | 'file' | 'scrape';
  url: string | null;
  status: 'active' | 'inactive' | 'error';
  record_count: number;
  last_sync: string | null;
  update_frequency: string | null;
  requires_key: boolean;
  is_free: boolean;
}

export interface DataSourceStatus {
  total_sources: number;
  active: number;
  sources: DataSourceInfo[];
}

export interface ExchangeRate {
  code: string;
  name: string;
  rate_to_usd: number;
  change_24h: number;
  updated_at: string;
}

export interface CommodityPrice {
  commodity: string;
  unit: string;
  price_usd: number;
  month_over_month: number;
  year_over_year: number;
}

export interface BurstProduct {
  hs_section: string;
  hs_name: string;
  current_value: number;
  zscore: number;
  yoy_growth: number;
  rank: number;
}

export interface RiskDashboard {
  country: string;
  overall_score: number;
  components: {
    fx_volatility: number;
    logistics_disruption: number;
    tariff_exposure: number;
    political_stability: number;
    disaster_risk: number;
  };
  recommendation: string;
}

export interface UpstreamnessResult {
  hs_section: string;
  upstreamness_index: number;
  position: 'upstream' | 'midstream' | 'downstream';
  year: number;
}

export interface TariffSavingsResult {
  partner: string;
  year: number;
  mfn_total_usd: number;
  rcep_total_usd: number;
  savings_usd: number;
  savings_pct: number;
  top_products: { hs_section: string; savings_usd: number }[];
}

export interface ApiError {
  error_code: string;
  message: string;
  details?: Record<string, unknown>;
  request_id?: string;
}
