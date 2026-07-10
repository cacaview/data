import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Tabs, Table, Tag, Spin, Typography, Space, Input, Progress, Statistic } from 'antd';
import {
  BankOutlined,
  SafetyOutlined,
  SearchOutlined,
  DollarOutlined,
  ClusterOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import {
  getEnterpriseRiskMonitor,
  getEnterpriseCompliance,
  getEnterpriseCostOptimizer,
  getSupplyChainMap,
} from '../../services/api';

const { Title } = Typography;

const Enterprise: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [riskData, setRiskData] = useState<any>(null);
  const [complianceData, setComplianceData] = useState<any>(null);
  const [costData, setCostData] = useState<any>(null);
  const [supplyData, setSupplyData] = useState<any>(null);
  const [complianceSearch, setComplianceSearch] = useState('');
  const [activeTab, setActiveTab] = useState('risk');

  const fetchRiskData = async () => {
    setLoading(true);
    try {
      const data = await getEnterpriseRiskMonitor();
      setRiskData(data);
    } catch (e) {
      console.error('Risk monitor fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchCompliance = async (entity?: string) => {
    setLoading(true);
    try {
      const data = await getEnterpriseCompliance(entity || undefined);
      setComplianceData(data);
    } catch (e) {
      console.error('Compliance fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchCostData = async () => {
    setLoading(true);
    try {
      const data = await getEnterpriseCostOptimizer();
      setCostData(data);
    } catch (e) {
      console.error('Cost optimizer fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchSupplyData = async () => {
    setLoading(true);
    try {
      const data = await getSupplyChainMap();
      const raw = data as any;

      // Transform: API returns {nodes, edges} → frontend expects {nodes, links}
      if (raw?.nodes && raw?.edges) {
        const transformedNodes = raw.nodes.map((n: any) => ({
          id: n.id || n.name,
          name: n.name || n.id,
          value: n.gdp_billion_usd || n.value || 1,
          category: n.role === 'hub' ? 0 : n.role === 'partner' ? 1 : 2,
          is_center: n.role === 'hub',
        }));

        const transformedLinks = raw.edges.map((e: any) => ({
          source: e.source,
          target: e.target,
          value: e.trade_value_usd ? e.trade_value_usd / 1e8 : e.value || 0, // dollars → 亿美元
        }));

        setSupplyData({
          ...raw,
          nodes: transformedNodes,
          links: transformedLinks,
          categories: [
            { name: '中心国' },
            { name: '贸易伙伴' },
            { name: '其他' },
          ],
        });
      } else {
        setSupplyData(data);
      }
    } catch (e) {
      console.error('Supply chain fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRiskData();
    // Don't fetch compliance on initial load - requires entity_name parameter
    fetchCostData();
    fetchSupplyData();
  }, []);

  const handleComplianceSearch = () => {
    fetchCompliance(complianceSearch || undefined);
  };

  // Supply chain graph chart option
  const supplyChainGraphOption = supplyData ? (() => {
    const nodes = (supplyData.nodes || []).map((n: any) => ({
      id: n.id || n.name,
      name: n.name || n.id,
      symbolSize: Math.max(20, Math.min(60, (n.value || 1) / 10)),
      category: n.category || 0,
      itemStyle: n.is_center ? { color: '#1677ff' } : undefined,
    }));
    const links = (supplyData.links || []).map((l: any) => ({
      source: l.source,
      target: l.target,
      value: l.value,
      lineStyle: { width: Math.max(1, Math.min(6, (l.value || 1) / 50)) },
    }));
    const categories = supplyData.categories || [
      { name: '国家' },
      { name: '供应商' },
      { name: '产品' },
    ];
    return {
      tooltip: {
        formatter: (params: any) => {
          if (params.dataType === 'node') return `${params.name}`;
          return `${params.data.source} → ${params.data.target}`;
        },
      },
      legend: { data: categories.map((c: any) => c.name), bottom: 0 },
      series: [{
        type: 'graph',
        layout: 'force',
        roam: true,
        label: { show: true, fontSize: 11 },
        categories,
        data: nodes,
        links,
        force: { repulsion: 200, edgeLength: [80, 200], gravity: 0.1 },
        emphasis: { focus: 'adjacency', lineStyle: { width: 4 } },
      }],
    };
  })() : {};

  // Risk monitoring table columns
  const riskColumns = [
    { title: '国家/地区', dataIndex: 'country', key: 'country' },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      render: (v: string) => {
        const colorMap: Record<string, string> = { high: 'red', medium: 'orange', low: 'green', critical: 'volcano' };
        return <Tag color={colorMap[v] || 'default'}>{v?.toUpperCase()}</Tag>;
      },
    },
    { title: '风险评分', dataIndex: 'risk_score', key: 'risk_score', render: (v: number) => v?.toFixed(1) ?? '-' },
    { title: '外汇风险', dataIndex: 'fx_risk', key: 'fx_risk', render: (v: number) => v?.toFixed(1) ?? '-' },
    { title: '物流风险', dataIndex: 'logistics_risk', key: 'logistics_risk', render: (v: number) => v?.toFixed(1) ?? '-' },
    { title: '政治风险', dataIndex: 'political_risk', key: 'political_risk', render: (v: number) => v?.toFixed(1) ?? '-' },
    { title: '建议', dataIndex: 'recommendation', key: 'recommendation', ellipsis: true },
  ];

  // Compliance table columns
  const complianceColumns = [
    { title: '企业名称', dataIndex: 'entity_name', key: 'entity_name' },
    { title: '合规状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'compliant' ? 'green' : v === 'non_compliant' ? 'red' : 'orange'}>{v}</Tag> },
    { title: '已检查清单', dataIndex: 'lists_checked', key: 'lists_checked', render: (v: string[]) => v?.map((l: string) => <Tag key={l} style={{ marginBottom: 2 }}>{l}</Tag>) },
    { title: '风险评级', dataIndex: 'risk_rating', key: 'risk_rating' },
    { title: '更新时间', dataIndex: 'last_checked', key: 'last_checked' },
  ];

  // Cost optimizer table columns
  const costColumns = [
    { title: 'HS编码', dataIndex: 'hs_code', key: 'hs_code' },
    { title: '产品描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: 'MFN税率', dataIndex: 'mfn_rate', key: 'mfn_rate', render: (v: number) => v != null ? `${v.toFixed(1)}%` : '-' },
    { title: 'RCEP税率', dataIndex: 'rcep_rate', key: 'rcep_rate', render: (v: number) => v != null ? `${v.toFixed(1)}%` : '-' },
    { title: '最优FTA', dataIndex: 'best_fta', key: 'best_fta' },
    { title: '最优税率', dataIndex: 'best_rate', key: 'best_rate', render: (v: number) => v != null ? `${v.toFixed(1)}%` : '-' },
    {
      title: '潜在节省',
      dataIndex: 'savings',
      key: 'savings',
      render: (v: number) => v != null
        ? <Tag color={v > 0 ? 'green' : 'default'}>{v > 0 ? `$${v.toLocaleString()}` : '-'}</Tag>
        : '-',
    },
  ];

  const tabItems = [
    {
      key: 'risk',
      label: <Space><SafetyOutlined /> 风险监控</Space>,
      children: (
        <>
          {riskData?.countries && (
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              {riskData.countries.slice(0, 4).map((c: any, i: number) => (
                <Col xs={24} sm={12} lg={6} key={i}>
                  <Card size="small">
                    <Statistic
                      title={c.country || c.name}
                      value={c.risk_score ?? 0}
                      suffix="/ 100"
                      valueStyle={{ color: (c.risk_score ?? 0) > 70 ? '#ff4d4f' : (c.risk_score ?? 0) > 40 ? '#faad14' : '#52c41a' }}
                    />
                    <Progress
                      percent={c.risk_score ?? 0}
                      showInfo={false}
                      strokeColor={(c.risk_score ?? 0) > 70 ? '#ff4d4f' : (c.risk_score ?? 0) > 40 ? '#faad14' : '#52c41a'}
                      size="small"
                      style={{ marginTop: 8 }}
                    />
                    <div style={{ marginTop: 4, fontSize: 12, color: '#8c8c8c' }}>
                      风险等级: <Tag color={c.risk_level === 'high' ? 'red' : c.risk_level === 'medium' ? 'orange' : 'green'} style={{ fontSize: 11 }}>{c.risk_level ?? '-'}</Tag>
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
          <Card size="small" title="风险详情表">
            <Table
              dataSource={riskData?.countries || riskData?.risks || []}
              columns={riskColumns}
              rowKey={(r: any) => r.country || r.id || Math.random().toString()}
              size="small"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </>
      ),
    },
    {
      key: 'compliance',
      label: <Space><SearchOutlined /> 合规检查</Space>,
      children: (
        <Card size="small" title="企业合规筛查">
          <Input.Search
            placeholder="输入企业名称搜索"
            value={complianceSearch}
            onChange={e => setComplianceSearch(e.target.value)}
            onSearch={handleComplianceSearch}
            enterButton="查询"
            style={{ marginBottom: 16, maxWidth: 500 }}
          />
          <Table
            dataSource={complianceData?.results || complianceData?.entities || []}
            columns={complianceColumns}
            rowKey={(r: any) => r.entity_name || r.id || Math.random().toString()}
            size="small"
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
    {
      key: 'cost',
      label: <Space><DollarOutlined /> 成本优化</Space>,
      children: (
        <Card size="small" title="关税方案对比">
          {costData?.summary && (
            <Row gutter={16} style={{ marginBottom: 16 }}>
              {Object.entries(costData.summary).map(([key, val]) => (
                <Col xs={12} sm={6} key={key}>
                  <Statistic title={key} value={val as number} precision={0} prefix="$" />
                </Col>
              ))}
            </Row>
          )}
          <Table
            dataSource={costData?.products || costData?.comparisons || []}
            columns={costColumns}
            rowKey={(r: any) => r.hs_code || r.id || Math.random().toString()}
            size="small"
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
    {
      key: 'supply',
      label: <Space><ClusterOutlined /> 供应网络</Space>,
      children: (
        <Card size="small" title="供应链关系图谱">
          {supplyData ? (
            <ReactECharts option={supplyChainGraphOption} style={{ height: 500 }} />
          ) : (
            <div style={{ height: 500, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>暂无数据</div>
          )}
        </Card>
      ),
    },
  ];

  return (
    <Spin spinning={loading}>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}><BankOutlined style={{ marginRight: 8 }} />企业风控中心</Title>
      </div>
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </Card>
    </Spin>
  );
};

export default Enterprise;
