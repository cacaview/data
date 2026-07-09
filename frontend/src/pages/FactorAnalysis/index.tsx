import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Select, Table, Spin, Typography, Space, Alert, Tag } from 'antd';
import {
  ApartmentOutlined,
  ExperimentOutlined,
  FundOutlined,
  RiseOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { getQuantFactors } from '../../services/api';

const { Title } = Typography;
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

const FactorAnalysis: React.FC = () => {
  const [partner, setPartner] = useState('VNM');
  const [loading, setLoading] = useState(false);
  const [factorData, setFactorData] = useState<any>(null);

  const fetchData = async (p: string) => {
    setLoading(true);
    try {
      const data = await getQuantFactors({ partner: p });
      setFactorData(data);
    } catch (e) {
      console.error('Factor analysis fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(partner); }, [partner]);

  // Waterfall chart - factor contributions
  const waterfallOption = factorData?.factors ? (() => {
    const factors = factorData.factors as { name: string; contribution: number }[];
    const categories = factors.map(f => f.name);
    const transparent: number[] = [];
    const positive: number[] = [];
    const negative: number[] = [];
    let cumulative = 0;
    for (const f of factors) {
      if (f.contribution >= 0) {
        transparent.push(cumulative);
        positive.push(f.contribution);
        negative.push(0);
      } else {
        transparent.push(cumulative + f.contribution);
        positive.push(0);
        negative.push(Math.abs(f.contribution));
      }
      cumulative += f.contribution;
    }
    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any[]) => {
          const idx = params[0]?.dataIndex;
          const f = factors[idx];
          return `${f.name}<br/>贡献度: ${f.contribution > 0 ? '+' : ''}${f.contribution.toFixed(2)}%`;
        },
      },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: categories, axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', name: '贡献度 (%)' },
      series: [
        { name: '透明基底', type: 'bar', stack: 'waterfall', itemStyle: { borderColor: 'transparent', color: 'transparent' }, emphasis: { itemStyle: { borderColor: 'transparent', color: 'transparent' } }, data: transparent },
        { name: '正向因子', type: 'bar', stack: 'waterfall', itemStyle: { color: '#52c41a', borderRadius: [4, 4, 0, 0] }, label: { show: true, position: 'top', formatter: (p: any) => `+${factors[p.dataIndex].contribution.toFixed(1)}` }, data: positive },
        { name: '负向因子', type: 'bar', stack: 'waterfall', itemStyle: { color: '#ff4d4f', borderRadius: [0, 0, 4, 4] }, label: { show: true, position: 'bottom', formatter: (p: any) => factors[p.dataIndex].contribution.toFixed(1) }, data: negative },
      ],
    };
  })() : {};

  // Seasonal radar chart
  const radarOption = factorData?.seasonality ? (() => {
    const s = factorData.seasonality;
    const indicators = (s.dimensions || []).map((d: string) => ({ name: d, max: 100 }));
    return {
      tooltip: {},
      radar: { indicator: indicators, radius: '65%' },
      series: [{
        type: 'radar',
        data: [{
          value: s.values || [],
          name: `${partner} 季节性特征`,
          areaStyle: { color: 'rgba(22, 119, 255, 0.2)' },
          lineStyle: { color: '#1677ff' },
        }],
      }],
    };
  })() : {};

  // Trend line chart with factor decomposition
  const trendOption = factorData?.trend_data ? (() => {
    const td = factorData.trend_data;
    const timeLabels = td.dates || [];
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['实际值', '趋势', '季节性', '残差'], top: 0 },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: timeLabels, boundaryGap: false },
      yAxis: { type: 'value', name: '贸易额 (亿美元)' },
      series: [
        { name: '实际值', type: 'line', data: td.actual || [], smooth: true, lineStyle: { width: 2 } },
        { name: '趋势', type: 'line', data: td.trend || [], smooth: true, lineStyle: { type: 'dashed', color: '#faad14' } },
        { name: '季节性', type: 'line', data: td.seasonal || [], smooth: true, lineStyle: { type: 'dotted', color: '#52c41a' } },
        { name: '残差', type: 'line', data: td.residual || [], smooth: true, lineStyle: { type: 'dotted', color: '#ff4d4f' } },
      ],
    };
  })() : {};

  // Insights table
  const insightColumns = [
    { title: '因子', dataIndex: 'name', key: 'name' },
    {
      title: '贡献方向',
      dataIndex: 'contribution',
      key: 'direction',
      render: (v: number) => v >= 0
        ? <Tag color="green">正向 +{v.toFixed(1)}%</Tag>
        : <Tag color="red">负向 {v.toFixed(1)}%</Tag>,
    },
    { title: '显著性', dataIndex: 'significance', key: 'significance', render: (v: number) => v ? `${(v * 100).toFixed(0)}%` : '-' },
    { title: '说明', dataIndex: 'description', key: 'description' },
  ];

  return (
    <Spin spinning={loading}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}><ApartmentOutlined style={{ marginRight: 8 }} />多因子贸易分析</Title>
        <Select value={partner} onChange={setPartner} style={{ width: 160 }}>
          {COUNTRIES.map(c => <Option key={c.code} value={c.code}>{c.flag} {c.name}</Option>)}
        </Select>
      </div>

      <Row gutter={[16, 16]}>
        {/* Waterfall: Factor Contributions */}
        <Col xs={24} lg={12}>
          <Card title={<Space><FundOutlined /> 因子贡献瀑布图</Space>} size="small">
            {factorData?.factors ? (
              <ReactECharts option={waterfallOption} style={{ height: 350 }} />
            ) : (
              <div style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>暂无数据</div>
            )}
          </Card>
        </Col>

        {/* Seasonal Radar */}
        <Col xs={24} lg={12}>
          <Card title={<Space><ExperimentOutlined /> 季节性特征雷达图</Space>} size="small">
            {factorData?.seasonality ? (
              <ReactECharts option={radarOption} style={{ height: 350 }} />
            ) : (
              <div style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>暂无数据</div>
            )}
          </Card>
        </Col>

        {/* Trend Decomposition */}
        <Col span={24}>
          <Card title={<Space><RiseOutlined /> 趋势分解图</Space>} size="small">
            {factorData?.trend_data ? (
              <ReactECharts option={trendOption} style={{ height: 380 }} />
            ) : (
              <div style={{ height: 380, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>暂无数据</div>
            )}
          </Card>
        </Col>

        {/* Insights Panel */}
        <Col span={24}>
          <Card title={<Space><ExperimentOutlined /> 分析洞察</Space>} size="small">
            {factorData?.insights?.length > 0 ? (
              <Space direction="vertical" style={{ width: '100%' }}>
                {factorData.insights.map((insight: any, i: number) => (
                  <Alert
                    key={i}
                    message={insight.title || insight.message || '洞察'}
                    description={insight.detail || insight.description || ''}
                    type={insight.type || (insight.severity === 'high' ? 'warning' : insight.severity === 'low' ? 'info' : 'success')}
                    showIcon
                  />
                ))}
              </Space>
            ) : null}
            {factorData?.factors?.length > 0 && (
              <Table
                dataSource={factorData.factors}
                columns={insightColumns}
                rowKey="name"
                size="small"
                pagination={false}
                style={{ marginTop: 12 }}
              />
            )}
          </Card>
        </Col>
      </Row>
    </Spin>
  );
};

export default FactorAnalysis;
