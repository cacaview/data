// Number / currency / percent formatters shared across pages.

export function formatUsd(value: number | null | undefined): string {
  if (value == null) return '—';
  if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (Math.abs(value) >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
  return `$${value.toFixed(2)}`;
}

export function formatPct(value: number | null | undefined, digits = 2): string {
  if (value == null) return '—';
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}%`;
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value == null) return '—';
  return value.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
