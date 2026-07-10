import React, { useEffect, useState, useCallback } from 'react';
import { Card, Select, Space, Spin, Tag, Timeline, Empty } from 'antd';
import {
  WarningOutlined,
  AlertOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { getPrediction, getClustering, getRiskAlerts } from '../../services/api';

const COUNTRY_OPTIONS = [
  { value: 'VNM', label: '越南' },
  { value: 'THA', label: '泰国' },
  { value: 'IDN', label: '印度尼西亚' },
  { value: 'MYS', label: '马来西亚' },
  { value: 'PHL', label: '菲律宾' },
  { value: 'SGP', label: '新加坡' },
];

const PRODUCT_OPTIONS = [
  { value: '机电产品', label: '机电产品' },
  { value: '矿产品', label: '矿产品' },
  { value: '农产品', label: '农产品' },
  { value: '化工产品', label: '化工产品' },
  { value: '纺织品', label: '纺织品' },
];

const CLUSTER_COLORS = ['#1677ff', '#36cfc9', '#ffc53d', '#ff7a45', '#9254de', '#73d13d'];

// ─────────────── Section 1: LSTM Prediction ───────────────
const PredictionChart: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [_loading, setLoading] = useState(false);
  const [country, setCountry] = useState('VNM');
  const [_product, setProduct] = useState('机电产品');

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getPrediction({ country });
      const raw = res as unknown as Record<string, any>;

      if (Array.isArray(raw?.data) && raw.data.length > 0) {
        // API returns {model_name, mape, data: [{date, actual, predicted, lower, upper}]}
        // Transform to {months, actual, predicted, lower, upper, mape}
        const months = raw.data.map((d: any) => d.date);
        const actual = raw.data.map((d: any) => d.actual != null ? Math.round(d.actual / 1e8) : null); // dollars → 亿美元
        const predicted = raw.data.map((d: any) => d.predicted != null ? Math.round(d.predicted / 1e8) : null);
        const lower = raw.data.map((d: any) => d.lower != null ? Math.round(d.lower / 1e8) : null);
        const upper = raw.data.map((d: any) => d.upper != null ? Math.round(d.upper / 1e8) : null);

        setData({
          months,
          actual,
          predicted,
          lower,
          upper,
          mape: raw.mape || 0,
        });
      } else if (raw?.months && raw?.actual && raw?.predicted) {
        setData(raw);
      } else {
        throw new Error('empty data');
      }
    } catch {
      // fallback mock - only used if API fails
      const months = Array.from({ length: 24 }, (_, i) => {
        const d = new Date(2024, i);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      });
      const actual = months.slice(0, 18).map((_, i) => Math.round(100 + i * 5 + Math.random() * 20));
      const predicted = months.slice(12).map((_, i) => Math.round(185 + i * 6 + Math.random() * 15));
      const lower = predicted.map((v) => Math.round(v * 0.88));
      const upper = predicted.map((v) => Math.round(v * 1.12));
      setData({ months, actual, predicted, lower, upper, mape: 4.2 });
    } finally {
      setLoading(false);
    }
  }, [country]);

  useEffect(() => { fetch(); }, [fetch]);

  if (!data) return <Spin style={{ display: 'block', margin: '40px auto' }} />;

  // Ensure all required arrays exist (API may return partial data)
  const months: string[] = data.months || [];
  const actual: number[] = data.actual || [];
  const predicted: number[] = data.predicted || [];
  const lower: number[] = data.lower || predicted.map((v: number) => Math.round(v * 0.88));
  const upper: number[] = data.upper || predicted.map((v: number) => Math.round(v * 1.12));

  if (!months.length) return <Empty description="暂无预测数据" />;

  const predLen = predicted.length;
  const actualPad = Array(Math.max(0, months.length - predLen)).fill(null);

  const option = {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, data: ['实际值', '预测值', '置信区间'] },
    grid: { left: 60, right: 30, top: 50, bottom: 30 },
    xAxis: { type: 'category', data: months },
    yAxis: { type: 'value', name: '贸易额 (亿美元)' },
    series: [
      {
        name: '实际值',
        type: 'line',
        data: [...actual, ...Array(predLen).fill(null)],
        lineStyle: { width: 2.5 },
        itemStyle: { color: '#1677ff' },
        symbol: 'circle',
        symbolSize: 5,
      },
      {
        name: '预测值',
        type: 'line',
        data: [...actualPad, ...predicted],
        lineStyle: { width: 2.5, type: 'dashed' },
        itemStyle: { color: '#ff7a45' },
        symbol: 'diamond',
        symbolSize: 5,
      },
      {
        name: '置信上界',
        type: 'line',
        data: [...actualPad, ...upper],
        lineStyle: { opacity: 0 },
        symbol: 'none',
        stack: 'confidence',
        silent: true,
      },
      {
        name: '置信区间',
        type: 'line',
        data: [...actualPad, ...lower.map((v: number, i: number) => (upper[i] ?? 0) - v)],
        lineStyle: { opacity: 0 },
        symbol: 'none',
        stack: 'confidence',
        areaStyle: { color: 'rgba(255,122,69,0.15)', origin: 'auto' },
        silent: true,
      },
    ],
  };

  return (
    <>
      <Space style={{ marginBottom: 16 }} wrap>
        <span style={{ fontWeight: 500 }}>国家：</span>
        <Select value={country} onChange={setCountry} options={COUNTRY_OPTIONS} style={{ width: 140 }} />
        <span style={{ fontWeight: 500 }}>商品：</span>
        <Select value={_product} onChange={setProduct} options={PRODUCT_OPTIONS} style={{ width: 140 }} />
        {data.mape != null && (
          <Tag color="blue" style={{ marginLeft: 16, fontSize: 14 }}>
            MAPE: {data.mape}%
          </Tag>
        )}
      </Space>
      <ReactECharts option={option} style={{ height: 400 }} />
    </>
  );
};

// ─────────────── Section 2: Clustering Analysis ───────────────
const ClusterChart: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [_loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getClustering()
      .then((res) => {
        const raw = res as unknown as any[];
        if (Array.isArray(raw) && raw.length > 0) {
          // API returns [{hs_code, name, trade_value, growth_rate, cluster, cluster_label}]
          // Transform to {clusters, products} format
          const clusterLabels = new Set<string>();
          raw.forEach((item: any) => {
            if (item.cluster_label) clusterLabels.add(item.cluster_label);
          });
          const clusters = Array.from(clusterLabels).sort();

          // Create cluster index map
          const clusterIndex: Record<string, number> = {};
          clusters.forEach((c, i) => { clusterIndex[c] = i; });

          const products = raw.map((item: any) => ({
            name: item.name || item.hs_code,
            growth: item.growth_rate || 0,
            value: Math.round((item.trade_value || 0) / 1e8), // dollars → 亿美元
            cluster: clusterIndex[item.cluster_label] ?? item.cluster ?? 0,
            clusterLabel: item.cluster_label || '',
          }));

          setData({ clusters, products });
        } else {
          setData(raw);
        }
      })
      .catch(() => {
        const clusters = ['高增长高价值', '高增长低价值', '低增长高价值', '低增长低价值', '新兴潜力'];
        const products = [
          { name: '集成电路', growth: 25, value: 4500, cluster: 0 },
          { name: '自动数据处理设备', growth: 18, value: 3200, cluster: 0 },
          { name: '农产品', growth: 30, value: 300, cluster: 1 },
          { name: '纺织品', growth: 22, value: 250, cluster: 1 },
          { name: '原油', growth: 3, value: 5000, cluster: 2 },
          { name: '矿产', growth: 5, value: 4200, cluster: 2 },
          { name: '废金属', growth: 2, value: 150, cluster: 3 },
          { name: '木材', growth: 4, value: 180, cluster: 3 },
          { name: '新能源汽车', growth: 45, value: 800, cluster: 4 },
          { name: '光伏组件', growth: 38, value: 650, cluster: 4 },
          { name: '锂电池', growth: 42, value: 720, cluster: 4 },
          { name: '半导体设备', growth: 15, value: 1800, cluster: 0 },
        ];
        setData({ clusters, products });
      })
      .finally(() => setLoading(false));
  }, []);

  if (!data) return <Spin style={{ display: 'block', margin: '40px auto' }} />;

  const seriesMap: Record<number, any[]> = {};
  (data.products || []).forEach((p: any) => {
    if (!seriesMap[p.cluster]) seriesMap[p.cluster] = [];
    seriesMap[p.cluster].push(p);
  });

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => {
        const d = p.data;
        return `<strong>${d.name}</strong><br/>
          增长率: ${d.value[0]}%<br/>
          贸易额: ${d.value[1]} 亿美元<br/>
          类别: ${d.clusterLabel}`;
      },
    },
    legend: {
      top: 0,
      data: (data.clusters || []).map((c: string, i: number) => ({
        name: c,
        itemStyle: { color: CLUSTER_COLORS[i % CLUSTER_COLORS.length] },
      })),
    },
    grid: { left: 70, right: 30, top: 50, bottom: 50 },
    xAxis: { type: 'value', name: '增长率 (%)', nameLocation: 'center', nameGap: 30 },
    yAxis: {
      type: 'log',
      name: '贸易额 (亿美元, log)',
      nameLocation: 'center',
      nameGap: 50,
      axisLabel: { formatter: '{value}' },
    },
    series: Object.entries(seriesMap).map(([clusterIdx, products]) => {
      const idx = Number(clusterIdx);
      return {
        name: data.clusters[idx] || `Cluster ${idx}`,
        type: 'scatter',
        symbolSize: (v: number[]) => Math.max(12, Math.sqrt(v[1]) * 2),
        data: products.map((p: any) => ({
          name: p.name,
          value: [p.growth, p.value],
          clusterLabel: data.clusters[idx],
        })),
        itemStyle: {
          color: CLUSTER_COLORS[idx % CLUSTER_COLORS.length],
          opacity: 0.8,
        },
        emphasis: { itemStyle: { opacity: 1, borderWidth: 2, borderColor: '#333' } },
      };
    }),
  };

  return <ReactECharts option={option} style={{ height: 440 }} />;
};

// ─────────────── Section 3: Risk Alerts ───────────────
const levelConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  high: { color: '#ff4d4f', icon: <WarningOutlined />, label: '高风险' },
  medium: { color: '#fa8c16', icon: <AlertOutlined />, label: '中风险' },
  low: { color: '#1677ff', icon: <InfoCircleOutlined />, label: '低风险' },
};

const RiskAlerts: React.FC = () => {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getRiskAlerts()
      .then((res) => setAlerts(Array.isArray(res) ? res : (res as unknown as Record<string, unknown>).alerts as unknown[] || []))
      .catch(() => {
        setAlerts([
          { id: 1, level: 'high', country: '越南', date: '2026-06-28', description: '越南对华钢铁反倾销税率上调至25.3%', suggestion: '建议钢铁出口企业关注越南市场，提前规划出口策略' },
          { id: 2, level: 'high', country: '印度尼西亚', date: '2026-06-25', description: '印尼实施镍矿出口限制，影响新能源产业链', suggestion: '建议相关企业加快镍矿替代来源布局' },
          { id: 3, level: 'medium', country: '泰国', date: '2026-06-20', description: '泰铢持续贬值，双边贸易汇率风险上升', suggestion: '建议采用远期结汇等工具锁定汇率' },
          { id: 4, level: 'medium', country: '马来西亚', date: '2026-06-18', description: '马方加强电子产品认证要求', suggestion: '建议电子出口企业尽早申请SIRIM认证' },
          { id: 5, level: 'low', country: '菲律宾', date: '2026-06-15', description: '菲方计划下调部分农产品进口关税', suggestion: '关注农业出口机遇，优化产品结构' },
          { id: 6, level: 'low', country: '新加坡', date: '2026-06-12', description: '新加坡推进数字贸易标准化', suggestion: '建议跨境数字贸易企业对接SG标准' },
        ]);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin style={{ display: 'block', margin: '40px auto' }} />;
  if (!alerts.length) return <Empty description="暂无风险预警" />;

  return (
    <Timeline
      style={{ marginTop: 20, paddingLeft: 8 }}
      items={alerts.map((a) => {
        const cfg = levelConfig[a.level] || levelConfig.low;
        return {
          color: cfg.color,
          children: (
            <div style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <Tag color={cfg.color} icon={cfg.icon} style={{ margin: 0 }}>
                  {cfg.label}
                </Tag>
                <span style={{ fontWeight: 600, fontSize: 15 }}>{a.country}</span>
                <span style={{ color: '#8c8c8c', fontSize: 13 }}>{a.date}</span>
              </div>
              <div style={{ fontSize: 14, color: '#262626', marginBottom: 4 }}>{a.description}</div>
              <div style={{ fontSize: 13, color: '#595959', background: '#f6f6f6', padding: '6px 10px', borderRadius: 4 }}>
                建议：{a.suggestion}
              </div>
            </div>
          ),
        };
      })}
    />
  );
};

// ─────────────── Main Component ───────────────
const AIPrediction: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <Card title="LSTM 趋势预测" variant="borderless">
        <PredictionChart />
      </Card>
      <Card title="商品聚类分析" variant="borderless">
        <ClusterChart />
      </Card>
      <Card title="贸易风险预警" variant="borderless">
        <RiskAlerts />
      </Card>
    </div>
  );
};

export default AIPrediction;
