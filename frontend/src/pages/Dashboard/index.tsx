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

    // Country name mapping: Chinese → English (for TradeMap component)
    const COUNTRY_NAME_MAP: Record<string, string> = {
      '中国': 'China',
      '越南': 'Vietnam',
      '泰国': 'Thailand',
      '马来西亚': 'Malaysia',
      '印度尼西亚': 'Indonesia',
      '印尼': 'Indonesia',
      '新加坡': 'Singapore',
      '菲律宾': 'Philippines',
      '缅甸': 'Myanmar',
      '柬埔寨': 'Cambodia',
      '老挝': 'Laos',
      '文莱': 'Brunei',
    };

    async function fetchAll() {
      try {
        const [summaryRes, mapRes, sankeyRes, trendRes] = await Promise.allSettled([
          getOverviewSummary(),
          getTradeMap(),
          getOverviewSankey(),
          getTrendMini(),
        ]);

        if (cancelled) return;

        // Summary KPIs - convert total_trade_value from dollars to 亿美元
        if (summaryRes.status === 'fulfilled' && summaryRes.value) {
          const raw = summaryRes.value as any;
          setKpi({
            total_trade_value: Math.round((raw.total_trade_value || 0) / 1e8), // dollars → 亿美元
            yoy_growth: raw.yoy_growth || 0,
            partner_count: raw.partner_count || 10,
            product_categories: raw.product_categories || 0,
          });
        }

        // Trade map - transform API field names to component expected names
        if (mapRes.status === 'fulfilled' && mapRes.value) {
          const md = mapRes.value as any;
          if (md.points && Array.isArray(md.points)) {
            const transformedPoints: TradeMapPoint[] = md.points.map((p: any) => {
              const chineseName = p.country_name || p.country || '';
              return {
                country: COUNTRY_NAME_MAP[chineseName] || chineseName, // Convert Chinese → English
                lat: p.latitude || p.lat || 0,
                lng: p.longitude || p.lng || 0,
                trade_value: Math.round((p.trade_value || 0) / 1e8), // dollars → 亿美元
                growth_rate: p.growth_rate || 0,
                top_products: p.top_products || [],
              };
            });
            // Add China node if not present
            const hasChina = transformedPoints.some(p => p.country === 'China');
            if (!hasChina) {
              transformedPoints.unshift({
                country: 'China',
                lat: 35.86,
                lng: 104.19,
                trade_value: Math.round((summaryRes.status === 'fulfilled' ? (summaryRes.value as any)?.total_trade_value || 0 : 0) / 1e8),
                growth_rate: 0,
                top_products: ['机电产品', '高新技术', '农产品'],
              });
            }
            setMapPoints(transformedPoints);
          }
          if (md.arcs && Array.isArray(md.arcs)) {
            const transformedArcs: TradeMapArc[] = md.arcs.map((a: any) => {
              const sourceName = a.from_name || a.source || '中国';
              const targetName = a.to_name || a.target || '';
              return {
                source: COUNTRY_NAME_MAP[sourceName] || sourceName, // Convert Chinese → English
                target: COUNTRY_NAME_MAP[targetName] || targetName, // Convert Chinese → English
                value: Math.round((a.trade_value || a.value || 0) / 1e8), // dollars → 亿美元
              };
            });
            setMapArcs(transformedArcs);
          }
        }

        // Sankey
        if (sankeyRes.status === 'fulfilled' && sankeyRes.value) {
          setSankey(sankeyRes.value as unknown as typeof FALLBACK_SANKEY);
        }

        // Trend - transform array to expected format
        if (trendRes.status === 'fulfilled' && trendRes.value) {
          const trendData = trendRes.value as any;
          if (Array.isArray(trendData)) {
            // API returns [{date, value}] - value in dollars, convert to 亿美元
            const transformed = trendData.map((t: any) => ({
              date: t.date || t.month,
              value: Math.round((t.value || 0) / 1e8), // dollars → 亿美元
            }));
            setTrend(transformed);
          } else {
            setTrend(trendData);
          }
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
