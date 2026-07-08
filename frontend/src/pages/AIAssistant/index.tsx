import React, { useEffect, useState, useRef } from 'react';
import { Card, Input, Button, Space, Spin, Tag, Typography } from 'antd';
import { SendOutlined, RobotOutlined, UserOutlined, BulbOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { askChat, getChatSuggestions } from '../../services/api';

const { Text } = Typography;

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  chart?: {
    chart_type: string;
    chart_data: any;
  };
}

const CHART_PALETTE = ['#1677ff', '#36cfc9', '#ffc53d', '#ff7a45', '#9254de', '#73d13d', '#f759ab', '#597ef7'];

function buildChartOption(chartType: string, chartData: any): any {
  if (!chartData) return null;
  switch (chartType) {
    case 'bar':
      return {
        tooltip: { trigger: 'axis' },
        grid: { left: 60, right: 20, top: 30, bottom: 30 },
        xAxis: { type: 'category', data: chartData.categories || [] },
        yAxis: { type: 'value' },
        series: (chartData.series || [{ name: '', data: chartData.values || [] }]).map((s: any, i: number) => ({
          ...s,
          type: 'bar',
          itemStyle: { color: CHART_PALETTE[i % CHART_PALETTE.length], borderRadius: [4, 4, 0, 0] },
        })),
        color: CHART_PALETTE,
      };
    case 'line':
      return {
        tooltip: { trigger: 'axis' },
        grid: { left: 60, right: 20, top: 30, bottom: 30 },
        xAxis: { type: 'category', data: chartData.categories || [] },
        yAxis: { type: 'value' },
        series: (chartData.series || [{ name: '', data: chartData.values || [] }]).map((s: any, i: number) => ({
          ...s,
          type: 'line',
          smooth: true,
          itemStyle: { color: CHART_PALETTE[i % CHART_PALETTE.length] },
        })),
        color: CHART_PALETTE,
      };
    case 'pie':
      return {
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        legend: { bottom: 0, type: 'scroll' },
        series: [{
          type: 'pie',
          radius: ['35%', '60%'],
          center: ['50%', '44%'],
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: { formatter: '{b}: {d}%' },
          data: (chartData.values || []).map((v: any, i: number) => ({
            name: chartData.categories?.[i] || `Item${i}`,
            value: v,
            itemStyle: { color: CHART_PALETTE[i % CHART_PALETTE.length] },
          })),
        }],
      };
    default:
      return null;
  }
}

const MessageBubble: React.FC<{ msg: ChatMessage }> = ({ msg }) => {
  const isUser = msg.role === 'user';
  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: 16,
      padding: '0 8px',
    }}>
      {!isUser && (
        <div style={{
          width: 36, height: 36, borderRadius: '50%', background: '#e6f4ff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginRight: 10, flexShrink: 0, marginTop: 2,
        }}>
          <RobotOutlined style={{ color: '#1677ff', fontSize: 18 }} />
        </div>
      )}
      <div style={{ maxWidth: '75%' }}>
        <div style={{
          background: isUser ? '#1677ff' : '#f5f5f5',
          color: isUser ? '#fff' : '#262626',
          padding: '10px 14px',
          borderRadius: isUser ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
          fontSize: 14,
          lineHeight: 1.7,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}>
          {msg.content}
        </div>
        {msg.chart?.chart_type && msg.chart.chart_data && (() => {
          const opt = buildChartOption(msg.chart.chart_type, msg.chart.chart_data);
          return opt ? (
            <div style={{
              background: '#fff', border: '1px solid #f0f0f0', borderRadius: 8,
              padding: 8, marginTop: 8,
            }}>
              <ReactECharts option={opt} style={{ height: 260 }} />
            </div>
          ) : null;
        })()}
        <div style={{
          fontSize: 11, color: '#bfbfbf', marginTop: 4,
          textAlign: isUser ? 'right' : 'left',
        }}>
          {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
      {isUser && (
        <div style={{
          width: 36, height: 36, borderRadius: '50%', background: '#1677ff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginLeft: 10, flexShrink: 0, marginTop: 2,
        }}>
          <UserOutlined style={{ color: '#fff', fontSize: 18 }} />
        </div>
      )}
    </div>
  );
};

const AIAssistant: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getChatSuggestions()
      .then((res) => setSuggestions(Array.isArray(res) ? res : []))
      .catch(() => {
        setSuggestions([
          '中国与东盟2024年贸易总额是多少？',
          '越南对中国出口增长最快的商品是什么？',
          'RCEP生效后关税有哪些变化？',
          '哪些商品存在贸易风险预警？',
          '预测下季度贸易趋势',
        ]);
      });
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const send = async (text: string) => {
    const msg = text.trim();
    if (!msg || loading) return;

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: msg,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await askChat(msg);
      const data = res as unknown as Record<string, unknown>;
      const assistantMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: (data.answer || data.content || data.message || '抱歉，暂时无法回答该问题。') as string,
        timestamp: Date.now(),
        chart: data.chart_type ? { chart_type: data.chart_type as string, chart_data: data.chart_data } : undefined,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const assistantMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: `收到您的问题："${msg}"。\n\n该问题涉及中国-东盟贸易领域，以下是一些要点：\n\n1. 中国与东盟互为最大贸易伙伴，2024年双边贸易额超6.6万亿元人民币\n2. RCEP 协定的全面实施显著降低了关税壁垒\n3. 主要贸易商品包括机电产品、矿产品、农产品等\n\n如需更详细的分析，请提供具体的国家或商品范围。`,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 136px)', minHeight: 500 }}>
      <Card
        title={
          <Space>
            <RobotOutlined style={{ color: '#1677ff' }} />
            <span>AI 智能助手</span>
          </Space>
        }
        variant="borderless"
        styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column', height: '100%' } }}
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
      >
        {/* Messages area */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 16px',
          background: '#fafafa',
          minHeight: 0,
        }}>
          {messages.length === 0 && (
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', height: '100%', color: '#bfbfbf',
            }}>
              <RobotOutlined style={{ fontSize: 48, marginBottom: 16, color: '#d9d9d9' }} />
              <Text type="secondary" style={{ fontSize: 16 }}>
                你好！我是 ACTAP 智能助手，可以回答关于中国-东盟贸易的各类问题。
              </Text>
            </div>
          )}
          {messages.map((msg) => <MessageBubble key={msg.id} msg={msg} />)}
          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', padding: '0 8px', marginBottom: 16 }}>
              <div style={{
                width: 36, height: 36, borderRadius: '50%', background: '#e6f4ff',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginRight: 10,
              }}>
                <RobotOutlined style={{ color: '#1677ff', fontSize: 18 }} />
              </div>
              <div style={{
                background: '#f5f5f5', padding: '10px 14px',
                borderRadius: '12px 12px 12px 2px',
              }}>
                <Spin size="small" />
                <Text type="secondary" style={{ marginLeft: 8, fontSize: 13 }}>正在思考...</Text>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Suggestion chips */}
        <div style={{
          padding: '10px 16px 0',
          borderTop: '1px solid #f0f0f0',
          background: '#fff',
        }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            <BulbOutlined style={{ color: '#faad14', marginTop: 3, marginRight: 2 }} />
            {suggestions.map((s, i) => (
              <Tag
                key={i}
                color="blue"
                style={{
                  cursor: 'pointer',
                  borderRadius: 12,
                  padding: '3px 12px',
                  fontSize: 13,
                  background: '#f0f5ff',
                  borderColor: '#adc6ff',
                  color: '#1677ff',
                }}
                onClick={() => send(s)}
              >
                {s}
              </Tag>
            ))}
          </div>
        </div>

        {/* Input area */}
        <div style={{
          padding: '12px 16px 16px',
          background: '#fff',
          borderTop: '1px solid #f0f0f0',
        }}>
          <Space.Compact style={{ width: '100%' }}>
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPressEnter={() => send(input)}
              placeholder="输入您关于中国-东盟贸易的问题..."
              size="large"
              disabled={loading}
              style={{ borderRadius: '8px 0 0 8px' }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              size="large"
              onClick={() => send(input)}
              loading={loading}
              style={{ borderRadius: '0 8px 8px 0', paddingInline: 20 }}
            >
              发送
            </Button>
          </Space.Compact>
        </div>
      </Card>
    </div>
  );
};

export default AIAssistant;
