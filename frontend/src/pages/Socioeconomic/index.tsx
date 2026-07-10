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

        // Transform macro data: API returns {countries: [...]} → frontend expects {country_profiles, aggregate}
        const rawMacro = macro as any;
        const rawTrade = trade as any;

        // Use trade-impact data for radar chart (has more real fields)
        if (rawTrade?.countries && Array.isArray(rawTrade.countries)) {
          const countries = rawTrade.countries;

          // Find max values for normalization
          const maxTrade = Math.max(...countries.map((c: any) => c.trade_value_usd || 0));
          const maxGrowth = Math.max(...countries.map((c: any) => Math.abs(c.trade_growth_pct || 0)));
          const maxShare = Math.max(...countries.map((c: any) => c.market_share_pct || 0));
          const maxEmployment = Math.max(...countries.map((c: any) => c.employment_proxy || 0));
          const maxIntensity = Math.max(...countries.map((c: any) => c.trade_intensity_index || 0));

          // Build dimensions list based on available data
          const dimensions: string[] = ['贸易额', '增长率', '市场份额'];
          if (maxEmployment > 0) dimensions.push('就业带动');
          if (maxIntensity > 0) dimensions.push('贸易强度');

          // Normalize function
          const normalize = (value: number, max: number) => {
            if (max > 0) return Math.round((value / max) * 100);
            return 50; // Default to middle if no variation
          };

          const country_profiles = countries.map((c: any) => {
            const values: number[] = [
              normalize(c.trade_value_usd || 0, maxTrade),
              normalize(Math.abs(c.trade_growth_pct || 0), maxGrowth),
              normalize(c.market_share_pct || 0, maxShare),
            ];
            if (maxEmployment > 0) values.push(normalize(c.employment_proxy || 0, maxEmployment));
            if (maxIntensity > 0) values.push(normalize(c.trade_intensity_index || 0, maxIntensity));

            return {
              country: c.country_name || c.country,
              values,
            };
          });

          // Calculate aggregate statistics
          const totalTrade = countries.reduce((sum: number, c: any) => sum + (c.trade_value_usd || 0), 0);
          const avgGrowth = countries.reduce((sum: number, c: any) => sum + (c.trade_growth_pct || 0), 0) / countries.length;

          setMacroData({
            ...rawMacro,
            country_profiles,
            aggregate: {
              'ASEAN贸易总额': Math.round(totalTrade / 1e8), // dollars → 亿美元
              '平均增长率': Math.round(avgGrowth * 100) / 100,
              '成员国数量': rawMacro.total_countries || countries.length,
              '数据年份': rawMacro.year || 2023,
            },
            dimensions,
          });
        } else if (rawMacro?.countries && Array.isArray(rawMacro.countries)) {
          // Fallback to macro data if trade-impact not available
          const countries = rawMacro.countries;
          const maxTrade = Math.max(...countries.map((c: any) => c.trade_volume_usd || 0));
          const maxGrowth = Math.max(...countries.map((c: any) => Math.abs(c.trade_growth_pct || 0)));

          const country_profiles = countries.map((c: any) => ({
            country: c.country_name || c.country,
            values: [
              maxTrade > 0 ? Math.round((c.trade_volume_usd || 0) / maxTrade * 100) : 50,
              maxGrowth > 0 ? Math.round(Math.abs(c.trade_growth_pct || 0) / maxGrowth * 100) : 50,
            ],
          }));

          const totalTrade = countries.reduce((sum: number, c: any) => sum + (c.trade_volume_usd || 0), 0);
          const avgGrowth = countries.reduce((sum: number, c: any) => sum + (c.trade_growth_pct || 0), 0) / countries.length;

          setMacroData({
            ...rawMacro,
            country_profiles,
            aggregate: {
              'ASEAN贸易总额': Math.round(totalTrade / 1e8),
              '平均增长率': Math.round(avgGrowth * 100) / 100,
              '成员国数量': rawMacro.total_countries || countries.length,
              '数据年份': rawMacro.year || 2023,
            },
            dimensions: ['贸易额', '增长率'],
          });
        } else {
          setMacroData(macro);
        }

        // Transform trade impact data for bar chart
        if (rawTrade?.countries && Array.isArray(rawTrade.countries)) {
          const transformedCountries = rawTrade.countries.map((c: any) => ({
            country: c.country_name || c.country,
            trade_to_gdp: c.trade_to_gdp_pct || c.trade_to_gdp || 0,
            ...c,
          }));
          setTradeImpactData({ ...rawTrade, countries: transformedCountries });
        } else {
          setTradeImpactData(trade);
        }

        // Transform sustainability: API returns {countries: [...]} → frontend expects {metrics, esg}
        const rawSustainability = sustainability as any;
        if (rawSustainability?.countries && Array.isArray(rawSustainability.countries)) {
          // Extract ESG-like metrics from country data
          const firstCountry = rawSustainability.countries[0] || {};
          const metrics = Object.entries(firstCountry)
            .filter(([key]) => !['country', 'country_name', 'country_name_en'].includes(key))
            .map(([key, val]) => ({
              name: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
              score: typeof val === 'number' ? val : 0,
              value: typeof val === 'number' ? val : 0,
            }));

          setSustainabilityData({
            ...rawSustainability,
            metrics,
            esg: metrics.slice(0, 6),
          });
        } else {
          setSustainabilityData(sustainability);
        }
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
