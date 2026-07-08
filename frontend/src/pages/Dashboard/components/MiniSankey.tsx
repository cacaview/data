import React from 'react';
import ReactECharts from 'echarts-for-react';

/** 8 validated categorical slots */
const PALETTE = ['#2a78d6','#1baf7a','#eda100','#008300','#4a3aa7','#e34948','#e87ba4','#eb6834'];

interface MiniSankeyProps {
  nodes: Array<{ name: string }>;
  links: Array<{ source: string; target: string; value: number }>;
}

const MiniSankey: React.FC<MiniSankeyProps> = ({ nodes, links }) => {
  // Build a color map: country nodes get categorical slots, product nodes get muted tones
  const countryNames = new Set(links.map(l => l.source));
  let colorIdx = 0;
  const nodeColorMap: Record<string, string> = {};
  for (const n of nodes) {
    if (countryNames.has(n.name)) {
      nodeColorMap[n.name] = PALETTE[colorIdx % PALETTE.length];
      colorIdx++;
    } else {
      nodeColorMap[n.name] = '#6da7ec'; // light sequential step for product nodes
    }
  }

  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: '#fff',
      borderColor: '#e8e8e8',
      borderWidth: 1,
      textStyle: { color: '#0b0b0b', fontSize: 13 },
      formatter(params: { data?: { source?: string; target?: string; value?: number } }) {
        const d = params.data as { source: string; target: string; value: number } | undefined;
        if (d && d.source && d.target) {
          return `<div style="font-size:12px;color:#898781;margin-bottom:4px">${d.source} → ${d.target}</div>
                  <div style="font-size:14px;font-weight:600;color:#0b0b0b">
                    ${d.value >= 10000 ? (d.value / 10000).toFixed(1) + ' 万亿' : d.value.toFixed(0) + ' 亿'} USD
                  </div>`;
        }
        return '';
      },
    },
    series: [
      {
        type: 'sankey',
        layout: 'none',
        left: 20,
        right: 20,
        top: 10,
        bottom: 10,
        nodeWidth: 18,
        nodeGap: 12,
        orient: 'horizontal',
        label: {
          fontSize: 12,
          color: '#0b0b0b',
        },
        lineStyle: {
          color: 'gradient',
          opacity: 0.35,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { opacity: 0.6 },
        },
        data: nodes.map(n => ({
          name: n.name,
          itemStyle: {
            color: nodeColorMap[n.name],
            borderColor: '#fff',
            borderWidth: 1,
          },
        })),
        links: links.map(l => ({
          source: l.source,
          target: l.target,
          value: l.value,
        })),
      },
    ],
  };

  return (
    <ReactECharts
      option={option}
      style={{ height: 260, width: '100%' }}
      opts={{ renderer: 'canvas' }}
      notMerge
    />
  );
};

export default MiniSankey;
