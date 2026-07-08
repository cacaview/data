// Typed API client for ACTAP backend.
// All methods return Promises of typed responses; no `any` in this file.

import axios, { type AxiosInstance } from 'axios';
import type {
  OverviewSummary,
  TradeMapData,
  SankeyData,
  TrendPoint,
  CountryRadar,
  RankingItem,
  PredictionResult,
  ClusteringResult,
  RiskAlertsResult,
  TariffInput,
  TariffResult,
  ChatResponse,
  DataSourceStatus,
  ExchangeRate,
  CommodityPrice,
  RiskDashboard,
  UpstreamnessResult,
  TariffSavingsResult,
  BurstProduct,
} from '../types';

const api: AxiosInstance = axios.create({ baseURL: '/api' });

// Type helper that unwraps the Axios envelope to just the data.
type Data<T> = T;

// ── Overview ──
export const getOverviewSummary = (): Promise<Data<OverviewSummary>> =>
  api.get<OverviewSummary>('/overview/summary').then(r => r.data);

export const getTradeMap = (): Promise<Data<TradeMapData>> =>
  api.get<TradeMapData>('/overview/trade-map').then(r => r.data);

export const getOverviewSankey = (): Promise<Data<SankeyData>> =>
  api.get<SankeyData>('/overview/sankey').then(r => r.data);

export const getTrendMini = (): Promise<Data<TrendPoint[]>> =>
  api.get<TrendPoint[]>('/overview/trend-mini').then(r => r.data);

// ── Trade Analysis ──
export interface TradeTrendParams {
  countries?: string;
  products?: string;
  start_year?: number;
  end_year?: number;
}

export const getTradeTrend = (params?: TradeTrendParams): Promise<Data<TrendPoint[]>> =>
  api.get<TrendPoint[]>('/trade/trend', { params }).then(r => r.data);

export const getCountryCompare = (): Promise<Data<CountryRadar[]>> =>
  api.get<CountryRadar[]>('/trade/country-compare').then(r => r.data);

export interface TradeRankingParams {
  type?: 'country' | 'product';
  limit?: number;
}

export const getTradeRanking = (params?: TradeRankingParams): Promise<Data<RankingItem[]>> =>
  api.get<RankingItem[]>('/trade/ranking', { params }).then(r => r.data);

export const getTradeSankey = (year?: number): Promise<Data<SankeyData>> =>
  api.get<SankeyData>('/trade/sankey', { params: year ? { year } : {} }).then(r => r.data);

// ── AI Prediction ──
export interface PredictionParams {
  country?: string;
  horizon?: number;
}

export const getPrediction = (params?: PredictionParams): Promise<Data<PredictionResult>> =>
  api.get<PredictionResult>('/ai/prediction', { params }).then(r => r.data);

export const getClustering = (): Promise<Data<ClusteringResult>> =>
  api.get<ClusteringResult>('/ai/clustering').then(r => r.data);

export const getRiskAlerts = (): Promise<Data<RiskAlertsResult>> =>
  api.get<RiskAlertsResult>('/ai/risk-alerts').then(r => r.data);

// ── Tariff ──
export const calculateTariff = (data: TariffInput): Promise<Data<TariffResult>> =>
  api.post<TariffResult>('/tariff/calculate', data).then(r => r.data);

export const getCommonCodes = (): Promise<Data<{ hs_code: string; description: string }[]>> =>
  api.get<{ hs_code: string; description: string }[]>('/tariff/common-codes').then(r => r.data);

// ── Chat ──
export const askChat = (message: string): Promise<Data<ChatResponse>> =>
  api.post<ChatResponse>('/chat/ask', { message }).then(r => r.data);

export const getChatSuggestions = (): Promise<Data<string[]>> =>
  api.get<string[]>('/chat/suggestions').then(r => r.data);

// ── Data Assets ──
export const getLineage = (): Promise<Data<unknown>> =>
  api.get('/assets/lineage').then(r => r.data);

export const getQuality = (): Promise<Data<unknown>> =>
  api.get('/assets/quality').then(r => r.data);

export const getCatalog = (): Promise<Data<unknown>> =>
  api.get('/assets/catalog').then(r => r.data);

// ── Data Sources ──
export const getDatasourceStatus = (): Promise<Data<DataSourceStatus>> =>
  api.get<DataSourceStatus>('/datasources/status').then(r => r.data);

export const getExchangeRates = (): Promise<Data<ExchangeRate[]>> =>
  api.get<ExchangeRate[]>('/datasources/exchange-rates').then(r => r.data);

export const getMacroProfile = (countryCode: string): Promise<Data<unknown>> =>
  api.get(`/datasources/macro/${countryCode}`).then(r => r.data);

export const getCommodityPrices = (): Promise<Data<CommodityPrice[]>> =>
  api.get<CommodityPrice[]>('/datasources/commodity-prices').then(r => r.data);

export const refreshDatasources = (): Promise<Data<{ status: string; message: string }>> =>
  api.post<{ status: string; message: string }>('/datasources/refresh').then(r => r.data);

// ── Analytics (P0 features) ──
export interface BurstRadarParams {
  partner?: string;
  threshold?: number;
}

export const getBurstRadar = (params?: BurstRadarParams): Promise<Data<BurstProduct[]>> =>
  api.get<BurstProduct[]>('/analytics/burst-radar', { params }).then(r => r.data);

export const getRiskDashboard = (country?: string): Promise<Data<RiskDashboard>> =>
  api.get<RiskDashboard>('/analytics/risk-dashboard', { params: { country } }).then(r => r.data);

export const getUpstreamness = (year?: number): Promise<Data<UpstreamnessResult[]>> =>
  api.get<UpstreamnessResult[]>('/analytics/upstreamness', { params: { year } }).then(r => r.data);

export const getTariffSavings = (partner?: string): Promise<Data<TariffSavingsResult>> =>
  api.get<TariffSavingsResult>('/analytics/tariff-savings', { params: { partner } }).then(r => r.data);

export default api;
