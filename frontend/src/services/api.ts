import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

// ── Overview ──
export const getOverviewSummary = () => api.get('/overview/summary');
export const getTradeMap = () => api.get('/overview/trade-map');
export const getOverviewSankey = () => api.get('/overview/sankey');
export const getTrendMini = () => api.get('/overview/trend-mini');

// ── Trade Analysis ──
export const getTradeTrend = (params?: Record<string, string>) =>
  api.get('/trade/trend', { params });
export const getCountryCompare = () => api.get('/trade/country-compare');
export const getTradeRanking = (params?: Record<string, string | number>) =>
  api.get('/trade/ranking', { params });
export const getTradeSankey = (year?: number) =>
  api.get('/trade/sankey', { params: year ? { year } : {} });

// ── AI Prediction ──
export const getPrediction = (params?: Record<string, string>) =>
  api.get('/ai/prediction', { params });
export const getClustering = () => api.get('/ai/clustering');
export const getRiskAlerts = () => api.get('/ai/risk-alerts');

// ── Tariff ──
export const calculateTariff = (data: {
  hs_code: string;
  origin_country: string;
  target_country: string;
  value_usd: number;
}) => api.post('/tariff/calculate', data);
export const getCommonCodes = () => api.get('/tariff/common-codes');

// ── Chat ──
export const askChat = (message: string) =>
  api.post('/chat/ask', { message });
export const getChatSuggestions = () => api.get('/chat/suggestions');

// ── Data Assets ──
export const getLineage = () => api.get('/assets/lineage');
export const getQuality = () => api.get('/assets/quality');
export const getCatalog = () => api.get('/assets/catalog');

// ── Data Sources (new) ──
export const getDatasourceStatus = () => api.get('/datasources/status');
export const getExchangeRates = () => api.get('/datasources/exchange-rates');
export const getMacroProfile = (countryCode: string) =>
  api.get(`/datasources/macro/${countryCode}`);
export const getCommodityPrices = () => api.get('/datasources/commodity-prices');

// ── Analytics (new P0 features) ──
export const getBurstRadar = (partner?: string, threshold?: number) =>
  api.get('/analytics/burst-radar', { params: { partner, threshold } });
export const getRiskDashboard = (country?: string) =>
  api.get('/analytics/risk-dashboard', { params: { country } });
export const getUpstreamness = (year?: number) =>
  api.get('/analytics/upstreamness', { params: { year } });
export const getTariffSavings = (partner?: string) =>
  api.get('/analytics/tariff-savings', { params: { partner } });

export default api;
