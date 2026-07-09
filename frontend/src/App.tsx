import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from './layouts/AppLayout';
import Dashboard from './pages/Dashboard';
import TradeAnalysis from './pages/TradeAnalysis';
import AIPrediction from './pages/AIPrediction';
import TariffCalc from './pages/TariffCalc';
import AIAssistant from './pages/AIAssistant';
import DataAssets from './pages/DataAssets';
import Analytics from './pages/Analytics';
import FactorAnalysis from './pages/FactorAnalysis';
import Enterprise from './pages/Enterprise';
import Socioeconomic from './pages/Socioeconomic';
import QuantDashboard from './pages/QuantDashboard';

const App = () => (
  <ConfigProvider
    locale={zhCN}
    theme={{
      token: {
        colorPrimary: '#1677ff',
        borderRadius: 8,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif',
      },
    }}
  >
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/trade" element={<TradeAnalysis />} />
          <Route path="/ai" element={<AIPrediction />} />
          <Route path="/tariff" element={<TariffCalc />} />
          <Route path="/chat" element={<AIAssistant />} />
          <Route path="/assets" element={<DataAssets />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/factors" element={<FactorAnalysis />} />
          <Route path="/enterprise" element={<Enterprise />} />
          <Route path="/socioeconomic" element={<Socioeconomic />} />
          <Route path="/quant" element={<QuantDashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </ConfigProvider>
);

export default App;
