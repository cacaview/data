import React, { useEffect, useState } from 'react';
import { Card, Tabs, Progress, Row, Col, Tag, Spin, Empty, Typography } from 'antd';
import {
  DatabaseOutlined, CheckCircleOutlined, ClockCircleOutlined,
  SafetyCertificateOutlined, ApiOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { getLineage, getQuality, getCatalog } from '../../services/api';

const { Text, Paragraph } = Typography;

const QUALITY_COLOR = '#1677ff';

// ─────────────── Tab 1: Data Lineage DAG ───────────────
const LineageTab: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [_loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getLineage()
      .then((res) => {
        const raw = res as any;
        if (raw?.nodes && raw?.edges) {
          // API returns {nodes: [{id, label, type, x, y}], edges: [{source, target}]}
          // Transform to {layers: [{name, x, nodes: [label1, label2, ...]}]} format
          const typeGroups: Record<string, {label: string, x: number, y: number}[]> = {};

          raw.nodes.forEach((node: any) => {
            const type = node.type || 'unknown';
            if (!typeGroups[type]) typeGroups[type] = [];
            typeGroups[type].push({
              label: node.label || node.id,
              x: node.x || 0,
              y: node.y || 0,
            });
          });

          // Create layers from type groups
          const typeOrder = ['source', 'process', 'storage', 'output', 'sink'];
          const layers = typeOrder
            .filter(type => typeGroups[type])
            .map(type => ({
              name: type === 'source' ? '源数据层' :
                    type === 'process' ? '处理层' :
                    type === 'storage' ? '存储层' :
                    type === 'output' ? '输出层' :
                    type === 'sink' ? '应用层' : type,
              x: typeGroups[type][0]?.x || 0,
              nodes: typeGroups[type].map(n => n.label),
            }));

          // If no layers created, use all nodes as single layer
          if (layers.length === 0) {
            layers.push({
              name: '数据节点',
              x: 0,
              nodes: raw.nodes.map((n: any) => n.label || n.id),
            });
          }

          setData({ layers, edges: raw.edges });
        } else {
          setData(raw);
        }
      })
      .catch(() => {
        const layers = [
          { name: '源数据层', x: 80, nodes: ['海关总署数据', 'UN Comtrade', '东盟秘书处', '企业报关系统'] },
          { name: '处理层', x: 380, nodes: ['ETL清洗', '标准化转换', '质量校验'] },
          { name: '存储层', x: 680, nodes: ['贸易主库', 'AI特征库', '关税规则库'] },
          { name: '输出层', x: 980, nodes: ['BI报表', 'AI模型', 'API服务'] },
        ];
        setData({ layers });
      })
      .finally(() => setLoading(false));
  }, []);

  if (!data) return <Spin style={{ display: 'block', margin: '40px auto' }} />;

  const layers = data.layers || [];
  const nodes: any[] = [];
  const links: any[] = [];
  const layerColors = ['#1677ff', '#36cfc9', '#ffc53d', '#ff7a45'];

  layers.forEach((layer: any, layerIdx: number) => {
    const layerNodes = layer.nodes || [];
    layerNodes.forEach((nodeName: string, nodeIdx: number) => {
      const yPos = 60 + nodeIdx * 90 + Math.max(0, (4 - layerNodes.length)) * 45;
      nodes.push({
        name: nodeName,
        x: layer.x,
        y: yPos,
        symbolSize: 50,
        symbol: 'roundRect',
        category: layerIdx,
        itemStyle: {
          color: '#fff',
          borderColor: layerColors[layerIdx],
          borderWidth: 2,
        },
        label: {
          show: true,
          position: 'inside',
          fontSize: 11,
          color: '#262626',
          formatter: (p: any) => {
            const n = p.name;
            if (n.length > 6) return n.slice(0, 6) + '\n' + n.slice(6);
            return n;
          },
        },
      });
    });
  });

  // Link each layer to the next
  for (let l = 0; l < layers.length - 1; l++) {
    const srcNodes = layers[l].nodes || [];
    const tgtNodes = layers[l + 1].nodes || [];
    srcNodes.forEach((src: string) => {
      tgtNodes.forEach((tgt: string) => {
        links.push({
          source: src,
          target: tgt,
          lineStyle: {
            color: layerColors[l],
            curveness: 0.2,
            width: 1.5,
            opacity: 0.5,
          },
        });
      });
    });
  }

  const option = {
    tooltip: { show: false },
    animationDuration: 1500,
    animationEasingUpdate: 'quinticInOut' as const,
    series: [{
      type: 'graph',
      layout: 'none',
      roam: false,
      data: nodes,
      links: links,
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: [0, 10],
      lineStyle: { opacity: 0.5 },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 3 },
      },
      categories: layers.map((l: any, i: number) => ({
        name: l.name,
        itemStyle: { color: layerColors[i] },
      })),
    }],
    graphic: layers.map((l: any, i: number) => ({
      type: 'text',
      left: l.x + 12,
      top: 16,
      style: {
        text: l.name,
        fill: layerColors[i],
        fontSize: 14,
        fontWeight: 'bold',
      },
    })),
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">
          数据从源系统流入，经过清洗和转换处理，存储到各数据库，最终输出到应用层。拖拽图表可交互查看。
        </Text>
      </div>
      <ReactECharts option={option} style={{ height: 460 }} />
    </div>
  );
};

// ─────────────── Tab 2: Quality Monitor ───────────────
interface QualityDim {
  name: string;
  key: string;
  score: number;
  icon: React.ReactNode;
  color: string;
  desc: string;
}

const QualityTab: React.FC = () => {
  const [dims, setDims] = useState<QualityDim[]>([]);
  const [loading, setLoading] = useState(false);
  const [overall, setOverall] = useState(0);

  useEffect(() => {
    setLoading(true);
    getQuality()
      .then((res) => {
        const raw = res as unknown as any[];
        if (Array.isArray(raw) && raw.length > 0) {
          // API returns [{dimension, score, details}]
          // Transform to {dimensions, overall} format
          const dimMap: Record<string, { name: string; icon: React.ReactNode; color: string; desc: string }> = {
            completeness: { name: '完整性', icon: <CheckCircleOutlined />, color: '#52c41a', desc: '数据字段非空率及记录完整程度' },
            accuracy: { name: '准确性', icon: <SafetyCertificateOutlined />, color: '#1677ff', desc: '数据值的准确性和合规性' },
            timeliness: { name: '时效性', icon: <ClockCircleOutlined />, color: '#faad14', desc: '数据更新及时性及延迟情况' },
            consistency: { name: '一致性', icon: <ApiOutlined />, color: '#722ed1', desc: '跨源数据的一致与规则符合度' },
            diversity: { name: '多样性', icon: <DatabaseOutlined />, color: '#13c2c2', desc: '数据来源的多样性和覆盖范围' },
          };

          const dimensions: QualityDim[] = raw
            .filter((d: any) => dimMap[d.dimension])
            .map((d: any) => ({
              key: d.dimension,
              score: d.score || 0,
              ...dimMap[d.dimension],
            }));

          const overall = dimensions.length > 0
            ? dimensions.reduce((sum: number, d: QualityDim) => sum + d.score, 0) / dimensions.length
            : 0;

          setDims(dimensions);
          setOverall(overall);
        } else {
          throw new Error('Invalid format');
        }
      })
      .catch(() => {
        const fallback: QualityDim[] = [
          { name: '完整性', key: 'completeness', score: 96.5, icon: <CheckCircleOutlined />, color: '#52c41a', desc: '数据字段非空率及记录完整程度' },
          { name: '准确性', key: 'accuracy', score: 94.2, icon: <SafetyCertificateOutlined />, color: '#1677ff', desc: '数据值的准确性和合规性' },
          { name: '时效性', key: 'timeliness', score: 91.8, icon: <ClockCircleOutlined />, color: '#faad14', desc: '数据更新及时性及延迟情况' },
          { name: '一致性', key: 'consistency', score: 93.1, icon: <ApiOutlined />, color: '#722ed1', desc: '跨源数据的一致与规则符合度' },
        ];
        setDims(fallback);
        setOverall(93.9);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin style={{ display: 'block', margin: '60px auto' }} />;

  return (
    <div>
      <div style={{ textAlign: 'center', marginBottom: 40 }}>
        <Progress
          type="circle"
          percent={Number(overall.toFixed(1))}
          size={140}
          strokeColor={QUALITY_COLOR}
          format={(p) => (
            <div>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#262626' }}>{p}%</div>
              <div style={{ fontSize: 13, color: '#8c8c8c' }}>综合质量</div>
            </div>
          )}
        />
      </div>
      <Row gutter={[24, 24]} justify="center">
        {dims.map((dim) => (
          <Col key={dim.key} xs={12} sm={12} md={6}>
            <Card
              variant="borderless"
              styles={{ body: { textAlign: 'center', padding: '28px 16px' } }}
              hoverable
            >
              <Progress
                type="circle"
                percent={Number(dim.score.toFixed(1))}
                size={110}
                strokeColor={dim.color}
                format={(p) => (
                  <div>
                    <div style={{ fontSize: 22, fontWeight: 700, color: '#262626' }}>{p}%</div>
                  </div>
                )}
              />
              <div style={{ marginTop: 16, fontWeight: 600, fontSize: 16, color: '#262626' }}>
                {dim.name}
              </div>
              <div style={{ marginTop: 4, fontSize: 12, color: '#8c8c8c' }}>
                {dim.desc}
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
};

// ─────────────── Tab 3: Data Catalog ───────────────
interface CatalogItem {
  name: string;
  url: string;
  description: string;
  update_freq: string;
  record_count: number;
  quality_score: number;
}

const freqColor: Record<string, string> = {
  '实时': 'green', '每日': 'blue', '每周': 'orange', '每月': 'purple', '每年': 'default',
};

const CatalogTab: React.FC = () => {
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getCatalog()
      .then((res) => {
        const raw = res as unknown as any[];
        if (Array.isArray(raw) && raw.length > 0) {
          // API returns [{id, name, url, description, update_frequency, record_count, last_updated, fields}]
          // Transform to CatalogItem format
          const freqMap: Record<string, string> = {
            daily: '每日',
            weekly: '每周',
            monthly: '每月',
            quarterly: '每季度',
            yearly: '每年',
            annual: '每年',
            real_time: '实时',
          };

          const transformed: CatalogItem[] = raw.map((item: any) => ({
            name: item.name || '',
            url: item.url || '',
            description: item.description || '',
            update_freq: freqMap[item.update_frequency] || item.update_frequency || '未知',
            record_count: item.record_count || 0,
            quality_score: item.quality_score || 95, // default score
          }));

          setCatalog(transformed);
        } else {
          throw new Error('Invalid format');
        }
      })
      .catch(() => {
        setCatalog([
          { name: '中国海关总署', url: 'http://www.customs.gov.cn', description: '中国进出口贸易统计数据，含HS编码商品明细', update_freq: '每月', record_count: 2580000, quality_score: 97.2 },
          { name: 'UN Comtrade', url: 'https://comtrade.un.org', description: '联合国商品贸易统计数据，覆盖全球200+经济体', update_freq: '每年', record_count: 12500000, quality_score: 95.8 },
          { name: '东盟秘书处统计', url: 'https://aseanstats.org', description: '东盟10国经济贸易综合统计数据', update_freq: '每季度', record_count: 856000, quality_score: 93.5 },
          { name: 'RCEP协定数据库', url: 'https://rcep.org', description: 'RCEP成员国关税减让表和原产地规则', update_freq: '每年', record_count: 156000, quality_score: 98.1 },
          { name: '世界银行WITS', url: 'https://wits.worldbank.org', description: '世界银行贸易综合解决方案，关税与非关税壁垒', update_freq: '每年', record_count: 3420000, quality_score: 94.6 },
          { name: '企业报关数据', url: 'internal://customs-clearance', description: '合作企业报关单、装箱单等贸易单证数据', update_freq: '实时', record_count: 8900000, quality_score: 91.3 },
          { name: '汇率数据源', url: 'https://exchangerate-api.com', description: '人民币与东盟各国货币逐日汇率', update_freq: '每日', record_count: 48200, quality_score: 99.1 },
          { name: '物流追踪数据', url: 'internal://logistics-tracking', description: '跨境物流运单状态、航线及港口吞吐量', update_freq: '每日', record_count: 1560000, quality_score: 92.7 },
          { name: '商品知识图谱', url: 'internal://knowledge-graph', description: 'HS编码映射、商品分类标准、贸易政策规则', update_freq: '每月', record_count: 420000, quality_score: 96.4 },
        ]);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin style={{ display: 'block', margin: '60px auto' }} />;
  if (!catalog.length) return <Empty description="暂无数据目录" />;

  return (
    <Row gutter={[16, 16]}>
      {catalog.map((item, idx) => (
        <Col key={idx} xs={24} sm={12} md={8}>
          <Card
            variant="borderless"
            hoverable
            styles={{ body: { padding: 20 } }}
            style={{ height: '100%' }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 12 }}>
              <div style={{
                width: 40, height: 40, borderRadius: 8, background: '#e6f4ff',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <DatabaseOutlined style={{ color: '#1677ff', fontSize: 20 }} />
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 15, color: '#262626', marginBottom: 2 }}>
                  {item.name}
                </div>
                <Text
                  type="secondary"
                  style={{ fontSize: 12 }}
                  ellipsis={{ tooltip: item.url }}
                >
                  {item.url}
                </Text>
              </div>
            </div>

            <Paragraph
              type="secondary"
              ellipsis={{ rows: 2 }}
              style={{ fontSize: 13, marginBottom: 14, minHeight: 40 }}
            >
              {item.description}
            </Paragraph>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
              <Tag color={freqColor[item.update_freq] || 'default'}>
                {item.update_freq}
              </Tag>
              <Tag>{(item.record_count / 10000).toFixed(1)}万条</Tag>
            </div>

            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              background: '#fafafa', borderRadius: 6, padding: '8px 12px',
            }}>
              <span style={{ fontSize: 13, color: '#8c8c8c' }}>质量评分</span>
              <span style={{
                fontSize: 18, fontWeight: 700,
                color: item.quality_score >= 95 ? '#52c41a' : item.quality_score >= 90 ? '#1677ff' : '#faad14',
              }}>
                {item.quality_score}
              </span>
            </div>
          </Card>
        </Col>
      ))}
    </Row>
  );
};

// ─────────────── Main Component ───────────────
const DataAssets: React.FC = () => {
  const tabItems = [
    { key: 'lineage', label: '数据血缘', children: <LineageTab /> },
    { key: 'quality', label: '质量监控', children: <QualityTab /> },
    { key: 'catalog', label: '数据目录', children: <CatalogTab /> },
  ];

  return (
    <Card
      title="数据资产管理"
      variant="borderless"
      styles={{ body: { padding: '12px 20px 20px' } }}
    >
      <Tabs defaultActiveKey="lineage" items={tabItems} />
    </Card>
  );
};

export default DataAssets;
