import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, GlobalOutlined, AppstoreOutlined } from '@ant-design/icons';

interface KPIData {
  total_trade_value: number;   // in 亿美元
  yoy_growth: number;          // percentage
  partner_count: number;
  product_categories: number;
}

interface KPICardsProps {
  data: KPIData;
}

/**
 * Format a number (in 亿) using Chinese units: 万亿 / 亿.
 * Keeps 2 decimal places for 万亿, 0 for plain 亿.
 */
function formatBillion(value: number): { value: string; unit: string } {
  if (value >= 10000) {
    return { value: (value / 10000).toFixed(2), unit: '万亿美元' };
  }
  return { value: value.toFixed(0), unit: '亿美元' };
}

const cardStyle: React.CSSProperties = {
  borderRadius: 10,
  boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  height: '100%',
};

const KPICards: React.FC<KPICardsProps> = ({ data }) => {
  const formatted = formatBillion(data.total_trade_value);
  const isPositive = data.yoy_growth >= 0;

  return (
    <Row gutter={[16, 16]}>
      {/* Total Trade Value */}
      <Col xs={24} sm={12} lg={6}>
        <Card style={cardStyle} styles={{ body: { padding: '20px 24px' } }}>
          <Statistic
            title={<span style={{ color: '#898781', fontSize: 13 }}>中国-东盟贸易总额</span>}
            value={formatted.value}
            suffix={formatted.unit}
            valueStyle={{ color: '#2a78d6', fontWeight: 700, fontSize: 26 }}
          />
        </Card>
      </Col>

      {/* YoY Growth */}
      <Col xs={24} sm={12} lg={6}>
        <Card style={cardStyle} styles={{ body: { padding: '20px 24px' } }}>
          <Statistic
            title={<span style={{ color: '#898781', fontSize: 13 }}>同比增长率</span>}
            value={data.yoy_growth}
            precision={2}
            suffix="%"
            prefix={isPositive ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            valueStyle={{
              color: isPositive ? '#0ca30c' : '#d03b3b',
              fontWeight: 700,
              fontSize: 26,
            }}
          />
        </Card>
      </Col>

      {/* Partner Countries */}
      <Col xs={24} sm={12} lg={6}>
        <Card style={cardStyle} styles={{ body: { padding: '20px 24px' } }}>
          <Statistic
            title={<span style={{ color: '#898781', fontSize: 13 }}>东盟合作伙伴国</span>}
            value={data.partner_count}
            suffix="个"
            prefix={<GlobalOutlined style={{ color: '#1baf7a' }} />}
            valueStyle={{ color: '#0b0b0b', fontWeight: 700, fontSize: 26 }}
          />
        </Card>
      </Col>

      {/* Product Categories */}
      <Col xs={24} sm={12} lg={6}>
        <Card style={cardStyle} styles={{ body: { padding: '20px 24px' } }}>
          <Statistic
            title={<span style={{ color: '#898781', fontSize: 13 }}>商品类目数</span>}
            value={data.product_categories}
            suffix="类"
            prefix={<AppstoreOutlined style={{ color: '#eda100' }} />}
            valueStyle={{ color: '#0b0b0b', fontWeight: 700, fontSize: 26 }}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default KPICards;
