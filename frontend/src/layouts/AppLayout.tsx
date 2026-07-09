import React from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Typography } from 'antd';
import {
  DashboardOutlined,
  LineChartOutlined,
  RobotOutlined,
  CalculatorOutlined,
  MessageOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  FundOutlined,
  BankOutlined,
  GlobalOutlined,
  ApartmentOutlined,
} from '@ant-design/icons';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '总览大屏' },
  { key: '/trade', icon: <LineChartOutlined />, label: '贸易分析' },
  { key: '/ai', icon: <RobotOutlined />, label: 'AI预测' },
  { key: '/tariff', icon: <CalculatorOutlined />, label: '关税计算' },
  { key: '/analytics', icon: <ExperimentOutlined />, label: '智能分析' },
  { key: '/factors', icon: <ApartmentOutlined />, label: '因子分析' },
  { key: '/quant', icon: <FundOutlined />, label: '量化分析' },
  { key: '/enterprise', icon: <BankOutlined />, label: '企业风控' },
  { key: '/socioeconomic', icon: <GlobalOutlined />, label: '社会经济' },
  { key: '/chat', icon: <MessageOutlined />, label: 'AI助手' },
  { key: '/assets', icon: <DatabaseOutlined />, label: '数据资产' },
];

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={220}
        style={{
          background: '#fff',
          borderRight: '1px solid #f0f0f0',
          boxShadow: '2px 0 8px rgba(0,0,0,0.04)',
        }}
      >
        <div style={{ padding: '20px 24px', borderBottom: '1px solid #f0f0f0' }}>
          <Title level={4} style={{ margin: 0, color: '#1677ff', fontWeight: 700 }}>
            ACTAP
          </Title>
          <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
            东盟跨境贸易AI智能分析平台
          </div>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ border: 'none', padding: '8px 0' }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: 56,
          }}
        >
          <Title level={5} style={{ margin: 0, color: '#262626' }}>
            中国-东盟跨境贸易AI智能分析平台
          </Title>
          <div style={{ color: '#8c8c8c', fontSize: 13 }}>
            2026"数据要素×"大赛参赛作品
          </div>
        </Header>
        <Content style={{ padding: 20, background: '#f5f5f5', overflow: 'auto' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
