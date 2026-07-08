import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Spin, Alert } from 'antd';
import {
  getOverviewSummary,
  getTradeMap,
  getOverviewSankey,
  getTrendMini,
} from '../../services/api';
import KPICards from './components/KPICards';
import TradeMap from './components/TradeMap';
import type { TradeMapPoint, TradeMapArc } from './components/TradeMap';
import MiniTrend from './components/MiniTrend';
import MiniSankey from './components/MiniSankey';

/* ── fallback data so the page renders even when the API is not running ── */

const FALLBACK_KPI = {
  total_trade_value: 64280,     // 亿美元
  yoy_growth: 7.32,
  partner_count: 10,
  product_categories: 97,
};

const FALLBACK_MAP_POINTS: TradeMapPoint[] = [
  { country: 'China',       lat: 35.8, lng: 104.2, trade_value: 64280, growth_rate: 7.32, top_products: ['机电产品', '高新技术', '农产品'] },
  { country: 'Vietnam',     lat: 14.1, lng: 108.3, trade_value: 17600, growth_rate: 12.5,  top_products: ['电子产品', '纺织品', '农产品'] },
  { country: 'Thailand',    lat: 15.9, lng: 100.5, trade_value: 11200, growth_rate: 5.8,   top_products: ['橡胶', '机电产品', '食品'] },
  { country: 'Malaysia',    lat: 4.2,  lng: 101.9, trade_value: 9800,  growth_rate: 8.1,   top_products: ['棕榈油', '电子元件', '石油'] },
  { country: 'Indonesia',   lat: -0.8, lng: 113.9, trade_value: 8600,  growth_rate: 6.4,   top_products: ['矿产', '棕榈油', '橡胶'] },
  { country: 'Singapore',   lat: 1.4,  lng: 103.8, trade_value: 6900,  growth_rate: 4.2,   top_products: ['电子元件', '石化产品', '机械设备'] },
  { country: 'Philippines', lat: 12.9, lng: 122.0, trade_value: 4200,  growth_rate: 9.7,   top_products: ['电子产品', '矿产', '农产品'] },
  { country: 'Myanmar',     lat: 21.9, lng: 96.0,  trade_value: 1800,  growth_rate: 3.5,   top_products: ['天然气', '农产品', '矿产'] },
  { country: 'Cambodia',    lat: 12.6, lng: 104.9, trade_value: 1400,  growth_rate: 15.2,  top_products: ['纺织品', '农产品', '橡胶'] },
  { country: 'Laos',        lat: 19.9, lng: 102.5, trade_value: 620,   growth_rate: 11.3,  top_products: ['矿产', '农产品', '木材'] },
  { country: 'Brunei',      lat: 4.5,  lng: 114.7, trade_value: 210,   growth_rate: 2.8,   top_products: ['石油', '天然气', '化工'] },
];

const FALLBACK_MAP_ARCS: TradeMapArc[] = [
  { source: 'China', target: 'Vietnam',     value: 17600 },
  { source: 'China', target: 'Thailand',    value: 11200 },
  { source: 'China', target: 'Malaysia',    value: 9800 },
  { source: 'China', target: 'Indonesia',   value: 8600 },
  { source: 'China', target: 'Singapore',   value: 6900 },
  { source: 'China', target: 'Philippines', value: 4200 },
  { source: 'China', target: 'Myanmar',     value: 1800 },
  { source: 'China', target: 'Cambodia',    value: 1400 },
  { source: 'China', target: 'Laos',        value: 620 },
  { source: 'China', target: 'Brunei',      value: 210 },
];

const FALLBACK_TREND = [
  { date: '2025-08', value: 4820 }, { date: '2025-09', value: 4950 },
  { date: '2025-10', value: 5120 }, { date: '2025-11', value: 5080 },
  { date: '2025-12', value: 5300 }, { date: '2026-01', value: 4980 },
  { date: '2026-02', value: 4650 }, { date: '2026-03', value: 5400 },
  { date: '2026-04', value: 5550 }, { date: '2026-05', value: 5700 },
  { date: '2026-06', value: 5820 }, { date: '2026-07', value: 5950 },
];

const FALLBACK_SANKEY = {
  nodes: [
    { name: '越南' }, { name: '泰国' }, { name: '马来西亚' },
    { name: '印度尼西亚' }, { name: '新加坡' }, { name: '菲律宾' },
    { name: '机电产品' }, { name: '农产品' }, { name: '矿产资源' },
    { name: '纺织品' }, { name: '化工产品' },
  ],
  links: [
    { source: '越南',     target: '机电产品', value: 6800 },
    { source: '越南',     target: '纺织品',   value: 3500 },
    { source: '越南',     target: '农产品',   value: 2400 },
    { source: '泰国',     target: '农产品',   value: 3200 },
    { source: '泰国',     target: '机电产品', value: 2800 },
    { source: '马来西亚', target: '矿产资源', value: 3100 },
    { source: '马来西亚', target: '化工产品', value: 2600 },
    { source: '印度尼西亚', target: '矿产资源', value: 3400 },
    { source: '印度尼西亚', target: '农产品', value: 2200 },
    { source: '新加坡',   target: '机电产品', value: 2500 },
    { source: '新加坡',   target: '化工产品', value: 1900 },
    { source: '菲律宾',   target: '机电产品', value: 2100 },
    { source: '菲律宾',   target: '矿产资源', value: 1200 },
  ],
};

/* ── card chrome ── */
const sectionCard: React.CSSProperties = {
  borderRadius: 10,
  boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
};

/* ── component ── */

const Dashboard: React.FC = () => {
  const [kpi, setKpi] = useState(FALLBACK_KPI);
  const [mapPoints, setMapPoints] = useState<TradeMapPoint[]>(FALLBACK_MAP_POINTS);
  const [mapArcs, setMapArcs] = useState<TradeMapArc[]>(FALLBACK_MAP_ARCS);
  const [trend, setTrend] = useState(FALLBACK_TREND);
  const [sankey, setSankey] = useState(FALLBACK_SANKEY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      try {
        const [summaryRes, mapRes, sankeyRes, trendRes] = await Promise.allSettled([
          getOverviewSummary(),
          getTradeMap(),
          getOverviewSankey(),
          getTrendMini(),
        ]);

        if (cancelled) return;

        // Summary KPIs
        if (summaryRes.status === 'fulfilled' && summaryRes.value) {
          setKpi(summaryRes.value as unknown as typeof FALLBACK_KPI);
        }

        // Trade map
        if (mapRes.status === 'fulfilled' && mapRes.value) {
          const md = mapRes.value as unknown as { points?: TradeMapPoint[]; arcs?: TradeMapArc[] };
          if (md.points) setMapPoints(md.points);
          if (md.arcs) setMapArcs(md.arcs);
        }

        // Sankey
        if (sankeyRes.status === 'fulfilled' && sankeyRes.value) {
          setSankey(sankeyRes.value as unknown as typeof FALLBACK_SANKEY);
        }

        // Trend
        if (trendRes.status === 'fulfilled' && trendRes.value) {
          setTrend(trendRes.value as unknown as typeof FALLBACK_TREND);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '加载数据失败');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div>
      {error && (
        <Alert
          message="数据加载提示"
          description={error}
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* ── KPI cards row ── */}
      <KPICards data={kpi} />

      {/* ── Middle row: Trade Map (60%) + Trend chart (40%) ── */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={14}>
          <Card
            title="中国-东盟贸易地图"
            style={sectionCard}
            styles={{ body: { padding: 0 } }}
          >
            <TradeMap points={mapPoints} arcs={mapArcs} />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card
            title="贸易额月度趋势"
            style={sectionCard}
            styles={{ body: { padding: '8px 12px' } }}
          >
            <MiniTrend data={trend} />
          </Card>
        </Col>
      </Row>

      {/* ── Bottom row: Sankey (full width) ── */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            title="主要贸易流向 (国家 → 商品类目)"
            style={sectionCard}
            styles={{ body: { padding: '8px 12px' } }}
          >
            <MiniSankey nodes={sankey.nodes} links={sankey.links} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
