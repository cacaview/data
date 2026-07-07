import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Select, Table, Tag, Statistic, Spin, Typography, Space, Progress } from 'antd';
import {
  ThunderboltOutlined,
  SafetyOutlined,
  RiseOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { getBurstRadar, getRiskDashboard, getUpstreamness, getTariffSavings } from '../../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

const COUNTRIES = [
  { code: 'VNM', name: '越南', flag: '🇻🇳' },
  { code: 'THA', name: '泰国', flag: '🇹🇭' },
  { code: 'MYS', name: '马来西亚', flag: '🇲🇾' },
  { code: 'IDN', name: '印尼', flag: '🇮🇩' },
  { code: 'PHL', name: '菲律宾', flag: '🇵🇭' },
  { code: 'SGP', name: '新加坡', flag: '🇸🇬' },
  { code: 'MMR', name: '缅甸', flag: '🇲🇲' },
  { code: 'KHM', name: '柬埔寨', flag: '🇰🇭' },
  { code: 'LAO', name: '老挝', flag: '🇱🇦' },
  { code: 'BRN', name: '文莱', flag: '🇧🇳' },
];

const Analytics: React.FC = () => {
  const [country, setCountry] = useState('VNM');
  const [loading, setLoading] = useState(false);
  const [burstData, setBurstData] = useState<any>(null);
  const [riskData, setRiskData] = useState<any>(null);
  const [upstreamData, setUpstreamData] = useState<any>(null);
  const [savingsData, setSavingsData] = useState<any>(null);

  const fetchData = async (c: string) => {
    setLoading(true);
    try {
      const [burst, risk, upstream, savings] = await Promise.all([
        getBurstRadar(c),
        getRiskDashboard(c),
        getUpstreamness(2023),
        getTariffSavings(c),
      ]);
      setBurstData(burst.data);
      setRiskData(risk.data);
      setUpstreamData(upstream.data);
      setSavingsData(savings.data);
    } catch (e) {
      console.error('Analytics fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(country); }, [country]);

  // Risk gauge chart option
  const riskGaugeOption = riskData ? {
    series: [{
      type: 'gauge',
      startAngle: 180,
      endAngle: 0,
      min: 0,
      max: 100,
      splitNumber: 10,
      axisLine: {
        lineStyle: {
          width: 30,
          color: [
            [0.3, '#67e0e3'],
            [0.7, '#37a2da'],
            [1, '#fd666d'],
          ],
        },
      },
      pointer: { itemStyle: { color: 'auto' } },
      axisTick: { distance: -30, length: 8, lineStyle: { color: '#fff', width: 2 } },
      splitLine: { distance: -30, length: 30, lineStyle: { color: '#fff', width: 4 } },
      axisLabel: { color: 'inherit', distance: 40, fontSize: 12 },
      detail: {
        valueAnimation: true,
        formatter: '{value}',
        color: 'inherit',
        fontSize: 24,
        offsetCenter: [0, '10%'],
      },
      title: { offsetCenter: [0, '35%'], fontSize: 14 },
      data: [{ value: riskData.total_score, name: `${riskData.country_name} 风险评分` }],
    }],
  } : {};

  // Upstreamness bar chart
  const upstreamOption = upstreamData ? {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'value', name: '上游度指数', max: 5 },
    yAxis: { type: 'category', data: upstreamData.upstreamness?.map((u: any) => u.country_name) || [] },
    series: [{
      type: 'bar',
      data: upstreamData.upstreamness?.map((u: any) => ({
        value: u.upstreamness_index,
        itemStyle: { color: u.upstreamness_index > 2.5 ? '#faad14' : u.upstreamness_index > 1.5 ? '#1677ff' : '#52c41a' },
      })) || [],
      label: { show: true, position: 'right', formatter: '{c}' },
    }],
  } : {};

  // Savings pie chart
  const savingsTop5 = savingsData?.items?.slice(0, 5) || [];
  const savingsPieOption = savingsTop5.length > 0 ? {
    tooltip: { trigger: 'item', formatter: '{b}: ${c}' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: savingsTop5.map((s: any) => ({
        name: s.hs_code,
        value: Math.round(s.savings_usd),
      })),
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
    }],
  } : {};

  // Burst radar table columns
  const burstColumns = [
    { title: 'HS编码', dataIndex: 'hs_code', key: 'hs_code' },
    { title: '贸易额', dataIndex: 'latest_value', key: 'value', render: (v: number) => `$${(v / 1e6).toFixed(1)}M` },
    { title: 'CAGR(3月)', dataIndex: 'cagr_3m', key: 'cagr', render: (v: number) => `${v.toFixed(1)}%` },
    { title: '趋势', dataIndex: 'trend', key: 'trend', render: (v: string) => <Tag color={v === 'rising' ? 'green' : v === 'declining' ? 'red' : 'blue'}>{v}</Tag> },
    { title: '异常分数', dataIndex: 'anomaly_z_score', key: 'z', render: (v: number) => <Tag color={v > 2 ? 'red' : v > 1 ? 'orange' : 'green'}>{v.toFixed(2)}</Tag> },
    { title: '状态', dataIndex: 'is_burst', key: 'burst', render: (v: boolean) => v ? <Tag color="red" icon={<ThunderboltOutlined />}>爆发</Tag> : <Tag>正常</Tag> },
  ];

  return (
    <Spin spinning={loading}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>🧠 智能分析中心</Title>
        <Select value={country} onChange={setCountry} style={{ width: 160 }}>
          {COUNTRIES.map(c => <Option key={c.code} value={c.code}>{c.flag} {c.name}</Option>)}
        </Select>
      </div>

      <Row gutter={[16, 16]}>
        {/* Risk Dashboard */}
        <Col xs={24} lg={8}>
          <Card title={<Space><SafetyOutlined /> 综合风险仪表盘</Space>} size="small">
            {riskData && (
              <>
                <ReactECharts option={riskGaugeOption} style={{ height: 200 }} />
                <div style={{ marginTop: 8 }}>
                  {riskData.recommendations?.map((r: string, i: number) => (
                    <Tag key={i} color="blue" style={{ marginBottom: 4 }}>{r}</Tag>
                  ))}
                </div>
              </>
            )}
          </Card>
        </Col>

        {/* Upstreamness */}
        <Col xs={24} lg={8}>
          <Card title={<Space><RiseOutlined /> RCEP价值链位势</Space>} size="small">
            {upstreamData && (
              <ReactECharts option={upstreamOption} style={{ height: 300 }} />
            )}
          </Card>
        </Col>

        {/* Tariff Savings */}
        <Col xs={24} lg={8}>
          <Card title={<Space><DollarOutlined /> RCEP关税节省</Space>} size="small">
            {savingsData && (
              <>
                <Statistic
                  title="潜在节省总额"
                  value={savingsData.total_potential_savings_usd}
                  precision={0}
                  prefix="$"
                  valueStyle={{ color: '#52c41a', fontSize: 24 }}
                />
                <ReactECharts option={savingsPieOption} style={{ height: 200 }} />
              </>
            )}
          </Card>
        </Col>

        {/* Burst Radar */}
        <Col span={24}>
          <Card title={<Space><ThunderboltOutlined /> 爆品挖掘雷达</Space>} size="small">
            <Table
              dataSource={burstData?.top_growing || []}
              columns={burstColumns}
              rowKey="hs_code"
              size="small"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </Col>
      </Row>
    </Spin>
  );
};

export default Analytics;
