import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Spin, Typography, Space, Statistic } from 'antd';
import {
  GlobalOutlined,
  BankOutlined,
  RiseOutlined,
  EnvironmentOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { getSocioMacroOverview, getSocioTradeImpact, getSocioSustainability } from '../../services/api';

const { Title } = Typography;

const ASEAN_COUNTRIES = ['越南', '泰国', '马来西亚', '印尼', '菲律宾', '新加坡', '缅甸', '柬埔寨', '老挝', '文莱'];

const Socioeconomic: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [macroData, setMacroData] = useState<any>(null);
  const [tradeImpactData, setTradeImpactData] = useState<any>(null);
  const [sustainabilityData, setSustainabilityData] = useState<any>(null);

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      try {
        const [macro, trade, sustainability] = await Promise.all([
          getSocioMacroOverview(),
          getSocioTradeImpact(),
          getSocioSustainability(),
        ]);
        setMacroData(macro);
        setTradeImpactData(trade);
        setSustainabilityData(sustainability);
      } catch (e) {
        console.error('Socioeconomic fetch error:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  // Country comparison radar chart
  const radarOption = macroData?.country_profiles ? (() => {
    const profiles = macroData.country_profiles as any[];
    const dimensions = macroData.dimensions || ['GDP', '贸易额', '人口', '人均GDP', '贸易增长率', '城镇化率'];
    const indicators = dimensions.map((d: string) => ({ name: d, max: 100 }));
    const colors = ['#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2', '#eb2f96', '#f5222d', '#a0d911', '#2f54eb'];
    return {
      tooltip: {},
      legend: {
        data: profiles.slice(0, 5).map((p: any) => p.country || p.name),
        bottom: 0,
        type: 'scroll',
      },
      radar: { indicator: indicators, radius: '60%' },
      series: [{
        type: 'radar',
        data: profiles.slice(0, 5).map((p: any, i: number) => ({
          value: p.values || p.radar_values || [],
          name: p.country || p.name,
          lineStyle: { color: colors[i % colors.length] },
          areaStyle: { color: colors[i % colors.length], opacity: 0.1 },
        })),
      }],
    };
  })() : {};

  // Trade impact bar chart (trade-to-GDP ratios)
  const tradeImpactOption = tradeImpactData?.countries ? (() => {
    const countries = tradeImpactData.countries as any[];
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: countries.map((c: any) => c.country || c.name),
        axisLabel: { rotate: 30 },
      },
      yAxis: { type: 'value', name: '贸易/GDP (%)' },
      series: [{
        type: 'bar',
        data: countries.map((c: any) => ({
          value: c.trade_to_gdp ?? c.ratio ?? 0,
          itemStyle: {
            color: (c.trade_to_gdp ?? c.ratio ?? 0) > 100
              ? '#1677ff'
              : (c.trade_to_gdp ?? c.ratio ?? 0) > 50
                ? '#52c41a'
                : '#faad14',
            borderRadius: [4, 4, 0, 0],
          },
        })),
        label: { show: true, position: 'top', formatter: '{c}%' },
      }],
    };
  })() : {};

  // Sustainability gauge charts option (multiple gauges)
  const sustainabilityGaugeOption = sustainabilityData?.metrics ? (() => {
    const metrics = sustainabilityData.metrics as any[];
    const gauges = metrics.slice(0, 6).map((m: any, i: number) => ({
      title: { offsetCenter: [0, '75%'], fontSize: 12 },
      value: m.score ?? m.value ?? 0,
      name: m.name || m.metric || `指标${i + 1}`,
    }));
    return {
      series: [{
        type: 'gauge',
        center: ['50%', '60%'],
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 100,
        splitNumber: 10,
        axisLine: {
          lineStyle: {
            width: 20,
            color: [
              [0.3, '#ff4d4f'],
              [0.6, '#faad14'],
              [1, '#52c41a'],
            ],
          },
        },
        pointer: { itemStyle: { color: 'auto' } },
        axisTick: { distance: -20, length: 6, lineStyle: { color: '#fff', width: 2 } },
        splitLine: { distance: -20, length: 20, lineStyle: { color: '#fff', width: 3 } },
        axisLabel: { color: 'inherit', distance: 30, fontSize: 10 },
        detail: { valueAnimation: true, formatter: '{value}', fontSize: 18, offsetCenter: [0, '35%'], color: 'inherit' },
        data: gauges,
      }],
    };
  })() : {};

  // ESG individual gauge charts
  const esgCategories = sustainabilityData?.esg || sustainabilityData?.categories || [];

  return (
    <Spin spinning={loading}>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}><GlobalOutlined style={{ marginRight: 8 }} />社会经济分析</Title>
      </div>

      <Row gutter={[16, 16]}>
        {/* Macro Overview Statistic Cards */}
        <Col span={24}>
          <Card title={<Space><BankOutlined /> ASEAN宏观经济概览</Space>} size="small">
            <Row gutter={[16, 16]}>
              {(macroData?.aggregate || macroData?.summary) ? (
                Object.entries(macroData.aggregate || macroData.summary || {}).map(([key, val]) => (
                  <Col xs={12} sm={8} md={6} key={key}>
                    <Statistic
                      title={key}
                      value={val as number}
                      precision={typeof val === 'number' && val > 10000 ? 0 : 2}
                      prefix={typeof val === 'number' && val > 10000 ? '$' : undefined}
                    />
                  </Col>
                ))
              ) : (
                <Col span={24}>
                  <div style={{ textAlign: 'center', color: '#999', padding: 20 }}>暂无宏观数据</div>
                </Col>
              )}
            </Row>
          </Card>
        </Col>

        {/* Country Comparison Radar */}
        <Col xs={24} lg={12}>
          <Card title={<Space><RiseOutlined /> 国家综合对比</Space>} size="small">
            {macroData?.country_profiles ? (
              <ReactECharts option={radarOption} style={{ height: 400 }} />
            ) : (
              <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>暂无数据</div>
            )}
          </Card>
        </Col>

        {/* Trade Impact Bar Chart */}
        <Col xs={24} lg={12}>
          <Card title={<Space><EnvironmentOutlined /> 贸易对GDP贡献</Space>} size="small">
            {tradeImpactData?.countries ? (
              <ReactECharts option={tradeImpactOption} style={{ height: 400 }} />
            ) : (
              <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>暂无数据</div>
            )}
          </Card>
        </Col>

        {/* Sustainability Gauges */}
        <Col span={24}>
          <Card title={<Space><GlobalOutlined /> 可持续发展指标 (ESG)</Space>} size="small">
            {esgCategories.length > 0 ? (
              <Row gutter={[16, 16]}>
                {esgCategories.map((cat: any, i: number) => (
                  <Col xs={24} sm={12} md={8} lg={4} key={i}>
                    <Card size="small" style={{ textAlign: 'center' }}>
                      <Statistic
                        title={cat.name || cat.metric || `ESG-${i + 1}`}
                        value={cat.score ?? cat.value ?? 0}
                        suffix="/ 100"
                        valueStyle={{
                          color: (cat.score ?? cat.value ?? 0) > 70
                            ? '#52c41a'
                            : (cat.score ?? cat.value ?? 0) > 40
                              ? '#faad14'
                              : '#ff4d4f',
                          fontSize: 28,
                        }}
                      />
                      <div style={{ marginTop: 8, fontSize: 11, color: '#8c8c8c' }}>{cat.description || ''}</div>
                    </Card>
                  </Col>
                ))}
              </Row>
            ) : sustainabilityData?.metrics ? (
              <ReactECharts option={sustainabilityGaugeOption} style={{ height: 350 }} />
            ) : (
              <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>暂无可持续发展数据</div>
            )}
          </Card>
        </Col>
      </Row>
    </Spin>
  );
};

export default Socioeconomic;
