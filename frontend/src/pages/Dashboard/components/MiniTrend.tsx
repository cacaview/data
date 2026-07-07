import React from 'react';
import ReactECharts from 'echarts-for-react';

/** Palette (validated via dataviz validator, light mode, --pairs all) */
const SERIES_BLUE = '#2a78d6';
const GRIDLINE   = '#e1e0d9';
const MUTED      = '#898781';

interface MiniTrendProps {
  data: Array<{ date: string; value: number }>;
}

const MiniTrend: React.FC<MiniTrendProps> = ({ data }) => {
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#e8e8e8',
      borderWidth: 1,
      textStyle: { color: '#0b0b0b', fontSize: 13 },
      formatter(params: echarts.DefaultLabelFormatterCallbackParams[]) {
        const p = params[0];
        const val = typeof p.value === 'number' ? p.value : Number(p.value);
        return `<div style="font-size:12px;color:#898781;margin-bottom:4px">${p.name}</div>
                <div style="font-size:14px;font-weight:600;color:#0b0b0b">
                  ${val >= 10000 ? (val / 10000).toFixed(1) + ' 万亿' : val.toFixed(0) + ' 亿'} USD
                </div>`;
      },
    },
    grid: { top: 20, right: 16, bottom: 32, left: 52 },
    xAxis: {
      type: 'category',
      data: data.map(d => d.date),
      axisLine: { lineStyle: { color: GRIDLINE } },
      axisTick: { show: false },
      axisLabel: { color: MUTED, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: GRIDLINE } },
      axisLabel: {
        color: MUTED,
        fontSize: 11,
        formatter(val: number) {
          return val >= 10000 ? (val / 10000).toFixed(1) + '万亿' : val + '亿';
        },
      },
    },
    series: [
      {
        type: 'line',
        data: data.map(d => d.value),
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { width: 2, color: SERIES_BLUE },
        itemStyle: {
          color: SERIES_BLUE,
          borderColor: '#fff',
          borderWidth: 2,
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(42,120,214,0.18)' },
              { offset: 1, color: 'rgba(42,120,214,0.01)' },
            ],
          },
        },
      },
    ],
  };

  return (
    <ReactECharts
      option={option}
      style={{ height: 280, width: '100%' }}
      opts={{ renderer: 'canvas' }}
      notMerge
    />
  );
};

export default MiniTrend;
