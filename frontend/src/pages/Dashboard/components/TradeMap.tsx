import React from 'react';
import ReactECharts from 'echarts-for-react';

/**
 * TradeMap -- China + ASEAN trade flow visualization.
 * Uses ECharts graph with layout:'none' so nodes sit at fixed
 * pixel positions that approximate their real-world longitude/latitude.
 * No GeoJSON required.
 *
 * Palette: 8 validated categorical slots (dataviz validator, light --pairs all).
 */

/* ── interfaces ── */
export interface TradeMapPoint {
  country: string;
  lat: number;
  lng: number;
  trade_value: number;        // 亿美元
  growth_rate: number;        // percentage
  top_products: string[];
}

export interface TradeMapArc {
  source: string;
  target: string;
  value: number;              // 亿美元
}

interface TradeMapProps {
  points: TradeMapPoint[];
  arcs: TradeMapArc[];
}

/* ── palette ── */
const PALETTE = ['#2a78d6','#1baf7a','#eda100','#008300','#4a3aa7','#e34948','#e87ba4','#eb6834'];
const CHINA_BLUE = '#2a78d6';

/* ── approximate center positions for China + 10 ASEAN members ── */
const FIXED_POSITIONS: Record<string, [number, number]> = {
  'China':      [420, 120],
  'Vietnam':    [430, 260],
  'Thailand':   [370, 280],
  'Myanmar':    [330, 190],
  'Laos':       [380, 225],
  'Cambodia':   [400, 300],
  'Malaysia':   [380, 370],
  'Singapore':  [395, 395],
  'Indonesia':  [470, 395],
  'Philippines':[520, 260],
  'Brunei':     [490, 360],
};

/**
 * Format a large number in Chinese units.
 */
function fmtValue(v: number): string {
  if (v >= 10000) return (v / 10000).toFixed(2) + ' 万亿美元';
  return v.toFixed(0) + ' 亿美元';
}

const TradeMap: React.FC<TradeMapProps> = ({ points, arcs }) => {
  // Build a color map for countries
  const colorMap: Record<string, string> = { 'China': CHINA_BLUE };
  let idx = 1; // slot 1 = China; ASEAN countries start at slot 2
  for (const p of points) {
    if (p.country !== 'China') {
      colorMap[p.country] = PALETTE[idx % PALETTE.length];
      idx++;
    }
  }

  // Value range for symbol sizing
  const values = points.map(p => p.trade_value);
  const minV = Math.min(...values, 1);
  const maxV = Math.max(...values, 100);

  function symbolSize(v: number): number {
    const minS = 18, maxS = 52;
    if (maxV === minV) return 35;
    return minS + ((v - minV) / (maxV - minV)) * (maxS - minS);
  }

  // Build graph nodes
  const nodes = points.map(p => {
    const pos = FIXED_POSITIONS[p.country];
    const size = symbolSize(p.trade_value);
    return {
      name: p.country,
      x: pos ? pos[0] : 300,
      y: pos ? pos[1] : 300,
      symbolSize: size,
      itemStyle: {
        color: colorMap[p.country] || '#898781',
        borderColor: '#fff',
        borderWidth: 2,
        shadowBlur: 8,
        shadowColor: 'rgba(42,120,214,0.25)',
      },
      label: {
        show: true,
        position: p.country === 'China' ? 'left' as const : 'bottom' as const,
        fontSize: 12,
        fontWeight: 600 as const,
        color: '#0b0b0b',
        distance: 6,
      },
      // store original data for tooltip
      tradeValue: p.trade_value,
      growthRate: p.growth_rate,
      topProducts: p.top_products,
    };
  });

  // Build graph edges (arcs from China to each ASEAN country)
  const maxArc = Math.max(...arcs.map(a => a.value), 1);
  const edges = arcs.map(a => {
    const w = 1 + (a.value / maxArc) * 5; // line width 1-6
    return {
      source: a.source,
      target: a.target,
      value: a.value,
      lineStyle: {
        width: w,
        color: {
          type: 'linear' as const,
          x: 0, y: 0, x2: 1, y2: 0,
          colorStops: [
            { offset: 0, color: CHINA_BLUE },
            { offset: 1, color: colorMap[a.target === 'China' ? a.source : a.target] || '#898781' },
          ],
        },
        curveness: 0.2,
        opacity: 0.55,
        shadowBlur: 6,
        shadowColor: 'rgba(42,120,214,0.18)',
      },
      emphasis: {
        lineStyle: { opacity: 0.85, width: w + 2 },
      },
    };
  });

  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: '#fff',
      borderColor: '#e8e8e8',
      borderWidth: 1,
      textStyle: { color: '#0b0b0b', fontSize: 13 },
      formatter(params: { dataType?: string; data?: Record<string, unknown> }) {
        // Node hover
        if (params.dataType === 'node') {
          const d = params.data as typeof nodes[0];
          const prods = d.topProducts?.slice(0, 3).join('、') || '-';
          return `<div style="font-weight:600;font-size:14px;margin-bottom:6px;color:#0b0b0b">${d.name}</div>
                  <div style="color:#898781;font-size:12px">贸易额</div>
                  <div style="font-size:15px;font-weight:600;color:#2a78d6">${fmtValue(d.tradeValue)}</div>
                  <div style="color:#898781;font-size:12px;margin-top:4px">增长率</div>
                  <div style="font-size:14px;color:${d.growthRate >= 0 ? '#0ca30c' : '#d03b3b'}">
                    ${d.growthRate >= 0 ? '+' : ''}${d.growthRate.toFixed(1)}%
                  </div>
                  <div style="color:#898781;font-size:12px;margin-top:4px">主要商品</div>
                  <div style="font-size:13px;color:#0b0b0b">${prods}</div>`;
        }
        // Edge hover
        if (params.dataType === 'edge') {
          const d = params.data as typeof edges[0];
          return `<div style="font-size:13px;color:#898781">${d.source} → ${d.target}</div>
                  <div style="font-size:15px;font-weight:600;color:#2a78d6;margin-top:4px">${fmtValue(d.value)}</div>`;
        }
        return '';
      },
    },
    // Subtle background — light gradient evoking a map canvas
    backgroundColor: {
      type: 'linear',
      x: 0, y: 0, x2: 0, y2: 1,
      colorStops: [
        { offset: 0, color: '#f0f6ff' },
        { offset: 1, color: '#e8f4f8' },
      ],
    },
    graphic: [
      // Decorative map label
      {
        type: 'text',
        left: 14,
        top: 10,
        style: {
          text: '中国-东盟贸易地图',
          fill: '#898781',
          fontSize: 12,
          fontWeight: 400,
        },
      },
    ],
    series: [
      {
        type: 'graph',
        layout: 'none',
        roam: false,
        data: nodes,
        links: edges,
        emphasis: {
          focus: 'adjacency',
          blurScope: 'coordinateSystem',
        },
        // No default labels on edges
        edgeLabel: { show: false },
      },
    ],
  };

  return (
    <ReactECharts
      option={option}
      style={{ height: 420, width: '100%' }}
      opts={{ renderer: 'canvas' }}
      notMerge
    />
  );
};

export default TradeMap;
