import React, { useEffect, useState, useCallback } from 'react';
import { Tabs, Card, Select, Space, Spin, DatePicker } from 'antd';
import ReactECharts from 'echarts-for-react';
import { getTradeTrend, getCountryCompare, getTradeRanking, getTradeSankey } from '../../services/api';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

const COUNTRY_COLORS: Record<string, string> = {
  '越南': '#1677ff', '泰国': '#36cfc9', '印度尼西亚': '#ffc53d',
  '马来西亚': '#ff7a45', '菲律宾': '#9254de', '新加坡': '#f759ab',
  '缅甸': '#597ef7', '柬埔寨': '#73d13d', '老挝': '#ffa940',
  '文莱': '#4096ff',
};

const ASEAN_COUNTRIES = Object.keys(COUNTRY_COLORS);

const CHART_PALETTE = [
  '#1677ff', '#36cfc9', '#ffc53d', '#ff7a45', '#9254de',
  '#f759ab', '#597ef7', '#73d13d', '#ffa940', '#4096ff',
];

// ─────────────── Tab 1: Trend Analysis ───────────────
const TrendTab: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [_loading, setLoading] = useState(false);
  const [yearRange, setYearRange] = useState<[string, string]>(['2018', '2024']);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getTradeTrend({ start_year: Number(yearRange[0]), end_year: Number(yearRange[1]) });
      const raw = res as unknown as any[];

      if (Array.isArray(raw) && raw.length > 0) {
        // API returns [{date, value, country, product}]
        // Transform to {years, series} format
        const yearsSet = new Set<string>();
        const seriesMap: Record<string, Record<string, number>> = {};

        raw.forEach((item: any) => {
          const year = item.date?.substring(0, 4) || item.date;
          const country = item.country || '未知';
          const value = Math.round((item.value || 0) / 1e8); // dollars → 亿美元

          yearsSet.add(year);
          if (!seriesMap[country]) seriesMap[country] = {};
          seriesMap[country][year] = value;
        });

        const years = Array.from(yearsSet).sort();
        const series: Record<string, number[]> = {};
        Object.entries(seriesMap).forEach(([country, yearValues]) => {
          series[country] = years.map(y => yearValues[y] || 0);
        });

        setData({ years, series });
      } else {
        setData(raw);
      }
    } catch {
      // fallback mock - only used if API fails
      const years = Array.from({ length: 7 }, (_, i) => String(2018 + i));
      const mock: Record<string, number[]> = {};
      ASEAN_COUNTRIES.slice(0, 6).forEach((c) => {
        mock[c] = years.map(() => Math.round(50 + Math.random() * 200));
      });
      setData({ years, series: mock });
    } finally {
      setLoading(false);
    }
  }, [yearRange]);

  useEffect(() => { fetch(); }, [fetch]);

  if (!data) return <Spin style={{ display: 'block', margin: '80px auto' }} />;

  const option = {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, type: 'scroll' },
    grid: { left: 60, right: 30, top: 50, bottom: 30 },
    xAxis: { type: 'category', data: data.years },
    yAxis: { type: 'value', name: '贸易额 (亿美元)', axisLabel: { formatter: '{value}' } },
    series: Object.entries(data.series || {}).map(([name, vals]) => ({
      name,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      data: vals as number[],
      itemStyle: { color: COUNTRY_COLORS[name] || '#1677ff' },
    })),
    color: CHART_PALETTE,
  };

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <span style={{ fontWeight: 500 }}>年份范围：</span>
        <RangePicker
          picker="year"
          defaultValue={[dayjs('2018'), dayjs('2024')]}
          onChange={(vals) => {
            if (vals && vals[0] && vals[1]) {
              setYearRange([String(vals[0].year()), String(vals[1].year())]);
            }
          }}
        />
      </Space>
      <ReactECharts option={option} style={{ height: 460 }} />
    </>
  );
};

// ─────────────── Tab 2: Country Compare ───────────────
const CompareTab: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [_loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getCountryCompare()
      .then((res) => {
        const raw = res as unknown as any[];
        if (Array.isArray(raw) && raw.length > 0) {
          // API returns [{country, trade_volume, growth_rate, interdependence, diversity, rcep_utilization}]
          // Transform to {indicators, series} format for radar chart
          const indicators = [
            { name: '贸易规模', max: 100 },
            { name: '增长率', max: 100 },
            { name: '相互依存度', max: 100 },
            { name: '多元化程度', max: 100 },
            { name: 'RCEP利用率', max: 100 },
          ];

          // Find max values for normalization
          const maxTrade = Math.max(...raw.map((r: any) => r.trade_volume || 0));
          const maxGrowth = Math.max(...raw.map((r: any) => Math.abs(r.growth_rate || 0)));

          const series = raw.map((r: any) => ({
            name: r.country,
            value: [
              Math.round((r.trade_volume || 0) / maxTrade * 100), // normalize to 0-100
              Math.round(Math.abs(r.growth_rate || 0) / maxGrowth * 100),
              Math.round(r.interdependence || 0),
              Math.round(r.diversity || 0),
              Math.round(r.rcep_utilization || 0),
            ],
          }));

          setData({ indicators, series });
        } else {
          setData(raw);
        }
      })
      .catch(() => {
        const indicators = [
          { name: '贸易规模', max: 100 },
          { name: '增长率', max: 100 },
          { name: '相互依存度', max: 100 },
          { name: '多元化程度', max: 100 },
          { name: 'RCEP利用率', max: 100 },
        ];
        const series = ASEAN_COUNTRIES.map((c) => ({
          name: c,
          value: indicators.map(() => Math.round(20 + Math.random() * 70)),
        }));
        setData({ indicators, series });
      })
      .finally(() => setLoading(false));
  }, []);

  if (!data) return <Spin style={{ display: 'block', margin: '80px auto' }} />;

  const option = {
    tooltip: {},
    legend: {
      type: 'scroll',
      bottom: 0,
      data: (data.series || []).map((s: any) => s.name),
    },
    radar: {
      indicator: data.indicators || [],
      shape: 'polygon',
      splitArea: { areaStyle: { color: ['#fff', '#fafafa', '#fff', '#fafafa'] } },
    },
    series: [
      {
        type: 'radar',
        data: (data.series || []).map((s: any, i: number) => ({
          name: s.name,
          value: s.value,
          areaStyle: { opacity: 0.08 },
          lineStyle: { width: 2 },
          itemStyle: { color: CHART_PALETTE[i % CHART_PALETTE.length] },
        })),
      },
    ],
    color: CHART_PALETTE,
  };

  return (
    <Card variant="borderless" styles={{ body: { padding: 16 } }}>
      <ReactECharts option={option} style={{ height: 500 }} />
    </Card>
  );
};

// ─────────────── Tab 3: Ranking Analysis ───────────────
const RankingTab: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [_loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getTradeRanking()
      .then((res) => {
        const raw = res as unknown as any[];
        if (Array.isArray(raw) && raw.length > 0) {
          // API returns [{name, value, growth, share}]
          // Transform to {country_ranking, product_ranking} format
          // Note: API returns countries, we need to split into countries and products
          // For now, treat all as country ranking since API doesn't distinguish
          const country_ranking = raw.map((r: any) => ({
            name: r.name,
            value: Math.round((r.value || 0) / 1e8), // dollars → 亿美元
          }));

          // Use top_growth_products from overview API for product ranking
          // For now, create empty product ranking
          const product_ranking: { name: string; value: number }[] = [];

          setData({ country_ranking, product_ranking });
        } else {
          setData(raw);
        }
      })
      .catch(() => {
        setData({
          country_ranking: ASEAN_COUNTRIES.map((c, i) => ({ name: c, value: Math.round(500 - i * 40 + Math.random() * 30) })),
          product_ranking: [
            '机电产品', '矿产品', '贱金属', '化工产品', '塑料橡胶',
            '纺织品', '农产品', '运输设备', '光学仪器', '木材制品',
            '食品饮料', '陶瓷玻璃', '宝石贵金属', '动植物油脂', '鞋帽伞',
            '皮革制品', '杂项制品', '艺术品', '武器弹药', '特殊交易品',
          ].map((p, i) => ({ name: p, value: Math.round(300 - i * 12 + Math.random() * 40) })),
        });
      })
      .finally(() => setLoading(false));
  }, []);

  if (!data) return <Spin style={{ display: 'block', margin: '80px auto' }} />;

  const countryOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 110, right: 30, top: 10, bottom: 20 },
    xAxis: { type: 'value', name: '亿美元' },
    yAxis: {
      type: 'category',
      data: (data.country_ranking || []).map((r: any) => r.name).reverse(),
      axisLabel: { width: 90, overflow: 'truncate' },
    },
    series: [{
      type: 'bar',
      data: (data.country_ranking || []).map((r: any) => r.value).reverse(),
      itemStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
          colorStops: [
            { offset: 0, color: '#1677ff' },
            { offset: 1, color: '#4096ff' },
          ],
        },
        borderRadius: [0, 4, 4, 0],
      },
      barWidth: 18,
    }],
  };

  const productOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 110, right: 30, top: 10, bottom: 20 },
    xAxis: { type: 'value', name: '亿美元' },
    yAxis: {
      type: 'category',
      data: (data.product_ranking || []).map((r: any) => r.name).reverse(),
      axisLabel: { width: 90, overflow: 'truncate' },
    },
    series: [{
      type: 'bar',
      data: (data.product_ranking || []).map((r: any) => r.value).reverse(),
      itemStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
          colorStops: [
            { offset: 0, color: '#36cfc9' },
            { offset: 1, color: '#87e8de' },
          ],
        },
        borderRadius: [0, 4, 4, 0],
      },
      barWidth: 14,
    }],
  };

  return (
    <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
      <Card title="国家 TOP10" variant="borderless" style={{ flex: '1 1 45%', minWidth: 380 }}>
        <ReactECharts option={countryOption} style={{ height: 420 }} />
      </Card>
      <Card title="商品 TOP20" variant="borderless" style={{ flex: '1 1 45%', minWidth: 380 }}>
        <ReactECharts option={productOption} style={{ height: 520 }} />
      </Card>
    </div>
  );
};

// ─────────────── Tab 4: Sankey Flow ───────────────
const SankeyTab: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [_loading, setLoading] = useState(false);
  const [year, setYear] = useState<number>(2024);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getTradeSankey(year);
      setData(res as unknown as Record<string, unknown>);
    } catch {
      const countries = ['越南', '泰国', '印度尼西亚', '马来西亚', '菲律宾'];
      const sections = ['机电产品', '矿产品', '农产品', '化工产品', '纺织品'];
      const nodes = [
        { name: '中国' },
        ...countries.map((c) => ({ name: c })),
        ...sections.map((s) => ({ name: s })),
      ];
      const links = [
        ...countries.map((c) => ({ source: '中国', target: c, value: Math.round(80 + Math.random() * 200) })),
        ...countries.flatMap((c) =>
          sections.map((s) => ({ source: c, target: s, value: Math.round(10 + Math.random() * 60) }))
        ),
      ];
      setData({ nodes, links });
    } finally {
      setLoading(false);
    }
  }, [year]);

  useEffect(() => { fetch(); }, [fetch]);

  if (!data) return <Spin style={{ display: 'block', margin: '80px auto' }} />;

  const nodeColors: Record<string, string> = {
    '中国': '#1677ff', '越南': '#1677ff', '泰国': '#36cfc9',
    '印度尼西亚': '#ffc53d', '马来西亚': '#ff7a45', '菲律宾': '#9254de',
    '机电产品': '#73d13d', '矿产品': '#ffa940', '农产品': '#f759ab',
    '化工产品': '#597ef7', '纺织品': '#ff4d4f',
  };

  const option = {
    tooltip: { trigger: 'item', triggerOn: 'mousemove' },
    series: [{
      type: 'sankey',
      layout: 'none',
      emphasis: { focus: 'adjacency' },
      nodeAlign: 'left',
      nodeGap: 14,
      nodeWidth: 24,
      lineStyle: { color: 'gradient', curveness: 0.5, opacity: 0.35 },
      itemStyle: { borderWidth: 0 },
      label: { fontSize: 13, color: '#262626' },
      data: (data.nodes || []).map((n: any) => ({
        name: n.name,
        itemStyle: { color: nodeColors[n.name] || '#1677ff' },
      })),
      links: data.links || [],
    }],
  };

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <span style={{ fontWeight: 500 }}>年份：</span>
        <Select
          value={year}
          onChange={setYear}
          style={{ width: 100 }}
          options={Array.from({ length: 7 }, (_, i) => ({ value: 2018 + i, label: String(2018 + i) }))}
        />
      </Space>
      <ReactECharts option={option} style={{ height: 520 }} />
    </>
  );
};

// ─────────────── Main Component ───────────────
const TradeAnalysis: React.FC = () => {
  const tabItems = [
    { key: 'trend', label: '趋势分析', children: <TrendTab /> },
    { key: 'compare', label: '国家对比', children: <CompareTab /> },
    { key: 'ranking', label: '排行分析', children: <RankingTab /> },
    { key: 'sankey', label: '商品流向', children: <SankeyTab /> },
  ];

  return (
    <Card
      title="贸易分析"
      variant="borderless"
      styles={{ body: { padding: '12px 20px 20px' } }}
    >
      <Tabs defaultActiveKey="trend" items={tabItems} />
    </Card>
  );
};

export default TradeAnalysis;
