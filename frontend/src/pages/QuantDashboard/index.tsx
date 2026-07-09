import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Select, Table, Tag, Spin, Typography, Space, Statistic, Alert } from 'antd';
import {
  FundOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { getQuantSignals, getQuantVar, getQuantPortfolio, getQuantForecast } from '../../services/api';

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

const QuantDashboard: React.FC = () => {
  const [partner, setPartner] = useState('VNM');
  const [loading, setLoading] = useState(false);
  const [signalData, setSignalData] = useState<any>(null);
  const [varData, setVarData] = useState<any>(null);
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [forecastData, setForecastData] = useState<any>(null);

  const fetchData = async (p: string) => {
    setLoading(true);
    try {
      const [signals, varResult, portfolio, forecast] = await Promise.all([
        getQuantSignals({ partner: p }),
        getQuantVar({ partner: p, confidence: 0.95 }),
        getQuantPortfolio(),
        getQuantForecast({ partner: p, horizon: 12 }),
      ]);
      setSignalData(signals);
      setVarData(varResult);
      setPortfolioData(portfolio);
      setForecastData(forecast);
    } catch (e) {
      console.error('Quant dashboard fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(partner); }, [partner]);

  // Trading signals table columns
  const signalColumns = [
    { title: '商品/指标', dataIndex: 'name', key: 'name' },
    {
      title: '信号',
      dataIndex: 'signal',
      key: 'signal',
      render: (v: string) => {
        const colorMap: Record<string, string> = { BUY: 'green', SELL: 'red', HOLD: 'blue', STRONG_BUY: '#389e0d', STRONG_SELL: '#cf1322' };
        return <Tag color={colorMap[v?.toUpperCase()] || 'default'} style={{ fontWeight: 600 }}>{v?.toUpperCase()}</Tag>;
      },
    },
    {
      title: '评分',
      dataIndex: 'score',
      key: 'score',
      render: (v: number) => v != null ? <span style={{ fontWeight: 600, color: v > 0 ? '#52c41a' : v < 0 ? '#ff4d4f' : '#1677ff' }}>{v > 0 ? '+' : ''}{v.toFixed(2)}</span> : '-',
    },
    { title: '置信度', dataIndex: 'confidence', key: 'confidence', render: (v: number) => v != null ? `${(v * 100).toFixed(0)}%` : '-' },
    { title: '说明', dataIndex: 'reason', key: 'reason', ellipsis: true },
  ];

  // VaR gauge chart
  const varGaugeOption = varData ? (() => {
    const value = varData.var_pct ?? varData.var ?? 0;
    return {
      series: [{
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 50,
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            width: 20,
            color: [
              [0.2, '#52c41a'],
              [0.5, '#faad14'],
              [1, '#ff4d4f'],
            ],
          },
        },
        pointer: { itemStyle: { color: 'auto' } },
        axisTick: { distance: -20, length: 6, lineStyle: { color: '#fff', width: 2 } },
        splitLine: { distance: -20, length: 20, lineStyle: { color: '#fff', width: 3 } },
        axisLabel: { color: 'inherit', distance: 30, fontSize: 10 },
        detail: { valueAnimation: true, formatter: '{value}%', fontSize: 22, offsetCenter: [0, '35%'], color: 'inherit' },
        title: { offsetCenter: [0, '60%'], fontSize: 14 },
        data: [{ value: Math.abs(value), name: 'VaR (95%)' }],
      }],
    };
  })() : {};

  // Stress test table
  const stressColumns = [
    { title: '情景', dataIndex: 'scenario', key: 'scenario' },
    { title: '冲击幅度', dataIndex: 'shock', key: 'shock', render: (v: number) => v != null ? `${v.toFixed(1)}%` : '-' },
    { title: '预计损失', dataIndex: 'loss', key: 'loss', render: (v: number) => v != null ? <Tag color="red">$ {v.toLocaleString()}</Tag> : '-' },
    { title: '概率', dataIndex: 'probability', key: 'probability', render: (v: number) => v != null ? `${(v * 100).toFixed(1)}%` : '-' },
  ];

  // Efficient frontier scatter plot
  const frontierOption = portfolioData ? (() => {
    const portfolios = portfolioData.portfolios || portfolioData.points || [];
    const efficient = portfolioData.efficient_frontier || [];
    const optimal = portfolioData.optimal || null;
    return {
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (params.seriesType === 'scatter') {
            return `风险: ${params.value[0].toFixed(2)}%<br/>收益: ${params.value[1].toFixed(2)}%`;
          }
          return '';
        },
      },
      legend: { data: ['投资组合', '有效前沿', '最优点'], bottom: 0 },
      grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
      xAxis: { type: 'value', name: '风险 (%)', nameLocation: 'center', nameGap: 30 },
      yAxis: { type: 'value', name: '收益 (%)', nameLocation: 'center', nameGap: 40 },
      series: [
        {
          name: '投资组合',
          type: 'scatter',
          data: portfolios.map((p: any) => [p.risk ?? p.volatility ?? 0, p.return ?? p.expected_return ?? 0]),
          symbolSize: 8,
          itemStyle: { color: '#1677ff', opacity: 0.5 },
        },
        {
          name: '有效前沿',
          type: 'line',
          data: efficient.map((p: any) => [p.risk ?? p.volatility ?? 0, p.return ?? p.expected_return ?? 0]),
          smooth: true,
          lineStyle: { color: '#52c41a', width: 3 },
          symbol: 'none',
        },
        ...(optimal ? [{
          name: '最优点',
          type: 'scatter',
          data: [[optimal.risk ?? optimal.volatility ?? 0, optimal.return ?? optimal.expected_return ?? 0]],
          symbolSize: 16,
          symbol: 'diamond',
          itemStyle: { color: '#ff4d4f', borderColor: '#fff', borderWidth: 2 },
          label: { show: true, formatter: '最优', position: 'top' },
        }] : []),
      ],
    };
  })() : {};

  // Forecast chart with confidence bands
  const forecastOption = forecastData ? (() => {
    const history = forecastData.history || [];
    const forecast = forecastData.forecast || [];
    const allDates = [...history.map((h: any) => h.date), ...forecast.map((f: any) => f.date)];
    const historyValues = history.map((h: any) => h.value);
    const forecastValues = new Array(history.length - 1).fill(null).concat(
      history.length > 0 ? [history[history.length - 1].value] : [],
      forecast.map((f: any) => f.predicted ?? f.value ?? 0)
    );
    const upperBand = new Array(history.length - 1).fill(null).concat(
      history.length > 0 ? [history[history.length - 1].value] : [],
      forecast.map((f: any) => f.upper ?? (f.predicted ?? f.value ?? 0) * 1.1)
    );
    const lowerBand = new Array(history.length - 1).fill(null).concat(
      history.length > 0 ? [history[history.length - 1].value] : [],
      forecast.map((f: any) => f.lower ?? (f.predicted ?? f.value ?? 0) * 0.9)
    );
    // Mark area for confidence band
    const confidenceArea = forecast.map((f: any, i: number) => ({
      xAxis: history.length + i - 1,
      itemStyle: { color: 'rgba(22, 119, 255, 0.08)' },
    }));

    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['历史数据', '预测值', '上界', '下界'], top: 0 },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: allDates, boundaryGap: false },
      yAxis: { type: 'value', name: '贸易额 (亿美元)' },
      series: [
        {
          name: '历史数据',
          type: 'line',
          data: [...historyValues, ...new Array(forecast.length).fill(null)],
          smooth: true,
          lineStyle: { width: 2 },
        },
        {
          name: '预测值',
          type: 'line',
          data: forecastValues,
          smooth: true,
          lineStyle: { type: 'dashed', color: '#1677ff' },
        },
        {
          name: '上界',
          type: 'line',
          data: upperBand,
          lineStyle: { opacity: 0 },
          areaStyle: { color: 'rgba(22, 119, 255, 0.1)' },
          stack: 'confidence',
          symbol: 'none',
        },
        {
          name: '下界',
          type: 'line',
          data: lowerBand,
          lineStyle: { opacity: 0 },
          areaStyle: { color: 'rgba(255, 255, 255, 1)' },
          stack: 'confidence',
          symbol: 'none',
        },
      ],
    };
  })() : {};

  // Aggregate stats from signals
  const signals = signalData?.signals || signalData?.items || [];
  const buyCount = signals.filter((s: any) => ['BUY', 'STRONG_BUY'].includes(s.signal?.toUpperCase())).length;
  const sellCount = signals.filter((s: any) => ['SELL', 'STRONG_SELL'].includes(s.signal?.toUpperCase())).length;
  const holdCount = signals.filter((s: any) => s.signal?.toUpperCase() === 'HOLD').length;

  return (
    <Spin spinning={loading}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}><FundOutlined style={{ marginRight: 8 }} />量化分析中心</Title>
        <Select value={partner} onChange={setPartner} style={{ width: 160 }}>
          {COUNTRIES.map(c => <Option key={c.code} value={c.code}>{c.flag} {c.name}</Option>)}
        </Select>
      </div>

      {/* Summary stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="买入信号" value={buyCount} valueStyle={{ color: '#52c41a' }} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="卖出信号" value={sellCount} valueStyle={{ color: '#ff4d4f' }} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="持有信号" value={holdCount} valueStyle={{ color: '#1677ff' }} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="VaR (95%)" value={Math.abs(varData?.var_pct ?? varData?.var ?? 0)} precision={2} suffix="%" valueStyle={{ color: '#faad14' }} /></Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Trading Signals */}
        <Col xs={24} lg={12}>
          <Card title={<Space><ThunderboltOutlined /> 交易信号</Space>} size="small">
            <Table
              dataSource={signals}
              columns={signalColumns}
              rowKey={(r: any) => r.name || r.id || Math.random().toString()}
              size="small"
              pagination={{ pageSize: 8 }}
            />
          </Card>
        </Col>

        {/* VaR Gauge + Stress Test */}
        <Col xs={24} lg={12}>
          <Card title={<Space><SafetyOutlined /> 风险度量 (VaR)</Space>} size="small">
            {varData ? (
              <>
                <ReactECharts option={varGaugeOption} style={{ height: 220 }} />
                {varData?.stress_tests?.length > 0 && (
                  <Table
                    dataSource={varData.stress_tests}
                    columns={stressColumns}
                    rowKey={(r: any) => r.scenario || Math.random().toString()}
                    size="small"
                    pagination={false}
                    style={{ marginTop: 8 }}
                  />
                )}
              </>
            ) : (
              <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>暂无VaR数据</div>
            )}
          </Card>
        </Col>

        {/* Efficient Frontier */}
        <Col xs={24} lg={12}>
          <Card title={<Space><FundOutlined /> 投资组合优化</Space>} size="small">
            {portfolioData ? (
              <ReactECharts option={frontierOption} style={{ height: 380 }} />
            ) : (
              <div style={{ height: 380, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>暂无投资组合数据</div>
            )}
          </Card>
        </Col>

        {/* Forecast with Confidence Bands */}
        <Col xs={24} lg={12}>
          <Card title={<Space><LineChartOutlined /> 时间序列预测</Space>} size="small">
            {forecastData ? (
              <>
                {forecastData.model && (
                  <Alert
                    message={`模型: ${forecastData.model} | 预测窗口: ${forecastData.horizon ?? forecastData.horizon_months ?? 12} 个月`}
                    type="info"
                    showIcon
                    style={{ marginBottom: 8 }}
                  />
                )}
                <ReactECharts option={forecastOption} style={{ height: 350 }} />
              </>
            ) : (
              <div style={{ height: 380, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>暂无预测数据</div>
            )}
          </Card>
        </Col>
      </Row>
    </Spin>
  );
};

export default QuantDashboard;
