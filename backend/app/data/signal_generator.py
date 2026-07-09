"""Real-Time Trading Signals Generator for Trade Data.

Inspired by quantitative trading signal systems:
- Momentum signals: rate of change, MACD-style, RSI
- Mean-reversion signals: Bollinger Bands, Z-score
- Breakout signals: Donchian channel, historical highs/lows
- Volatility signals: rolling volatility, GARCH-style
- Composite signal: weighted combination with confidence score

Signals:
- BUY (growth opportunity): positive composite signal > threshold
- HOLD (stable): neutral composite signal
- SELL (risk warning): negative composite signal < threshold
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_array(series) -> np.ndarray:
    """Convert input to a clean float64 numpy array, dropping NaN/Inf."""
    arr = np.asarray(series, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    return arr


def _ema(values: np.ndarray, span: int) -> np.ndarray:
    """Exponential moving average via pandas (centered on the input array)."""
    if len(values) == 0:
        return np.array([], dtype=np.float64)
    return pd.Series(values).ewm(span=span, adjust=False).mean().to_numpy()


def _pct_change(series: np.ndarray) -> np.ndarray:
    """Element-wise percentage change, guarding against zero division."""
    if len(series) < 2:
        return np.array([], dtype=np.float64)
    prev = series[:-1]
    curr = series[1:]
    with np.errstate(divide="ignore", invalid="ignore"):
        changes = np.where(prev != 0, (curr - prev) / np.abs(prev) * 100.0, 0.0)
    return changes


# ---------------------------------------------------------------------------
# 1. Momentum Signal (MACD-style)
# ---------------------------------------------------------------------------

def compute_momentum_signal(
    series,
    fast_period: int = 6,
    slow_period: int = 12,
) -> dict:
    """MACD-like momentum indicator for trade data.

    Computes a fast/slow EMA divergence and detects signal-line crossovers
    to produce a directional momentum reading.

    Args:
        series: Numeric time-series of trade values (list or np.ndarray).
        fast_period: Fast EMA span (months).
        slow_period: Slow EMA span (months).

    Returns:
        Dict with keys:
            current_signal (float): Latest EMA divergence, scaled to [-100, 100].
            trend (str): "up" / "down" / "neutral".
            strength (float): Signal magnitude, 0-100.
    """
    arr = _safe_array(series)
    min_len = slow_period + 2  # need enough data for slow EMA + smoothing

    if len(arr) < min_len:
        return {"current_signal": 0.0, "trend": "neutral", "strength": 0.0}

    fast_ema = _ema(arr, fast_period)
    slow_ema = _ema(arr, slow_period)

    macd_line = fast_ema - slow_ema
    signal_line = _ema(macd_line, max(fast_period, 3))

    # Current divergence = MACD line minus its own signal line
    divergence = macd_line[-1] - signal_line[-1]

    # Normalise to [-100, 100] using the range of the MACD line
    macd_range = np.max(np.abs(macd_line)) if np.max(np.abs(macd_line)) > 0 else 1.0
    normalised = float(np.clip(divergence / macd_range * 100, -100, 100))

    # Crossover: current divergence and previous divergence have opposite signs
    if len(macd_line) >= 2:
        prev_div = macd_line[-2] - signal_line[-2]
        bullish_cross = prev_div < 0 and divergence >= 0
        bearish_cross = prev_div > 0 and divergence <= 0
    else:
        bullish_cross = False
        bearish_cross = False

    # Trend classification
    if bullish_cross or normalised > 10:
        trend = "up"
    elif bearish_cross or normalised < -10:
        trend = "down"
    else:
        trend = "neutral"

    strength = min(abs(normalised), 100.0)

    return {
        "current_signal": round(normalised, 2),
        "trend": trend,
        "strength": round(strength, 2),
    }


# ---------------------------------------------------------------------------
# 2. RSI (Relative Strength Index)
# ---------------------------------------------------------------------------

def compute_rsi(series, period: int = 12) -> dict:
    """Relative Strength Index adapted for monthly trade data.

    RSI = 100 - 100 / (1 + RS), where RS = avg_gain / avg_loss over *period*.

    Interpretation for trade volume/value:
        > 70 -- overbought (potential sell signal: growth may be unsustainable)
        < 30 -- oversold   (potential buy signal: undervalued, recovery possible)

    Args:
        series: Numeric time-series of trade values.
        period: Look-back window (default 12 months).

    Returns:
        Dict with keys:
            rsi_value (float): 0-100.
            zone (str): "overbought" / "neutral" / "oversold".
            signal (str): "sell" / "hold" / "buy".
    """
    arr = _safe_array(series)

    if len(arr) < period + 1:
        return {"rsi_value": 50.0, "zone": "neutral", "signal": "hold"}

    deltas = np.diff(arr)

    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Wilder's smoothed average (exponential)
    avg_gain = pd.Series(gains).ewm(alpha=1.0 / period, adjust=False).mean().iloc[-1]
    avg_loss = pd.Series(losses).ewm(alpha=1.0 / period, adjust=False).mean().iloc[-1]

    if avg_gain == 0 and avg_loss == 0:
        # Constant series -- no movement, neutral RSI
        rsi_value = 50.0
    elif avg_loss == 0:
        rsi_value = 100.0
    elif avg_gain == 0:
        rsi_value = 0.0
    else:
        rs = avg_gain / avg_loss
        rsi_value = 100.0 - 100.0 / (1.0 + rs)

    rsi_value = float(np.clip(rsi_value, 0, 100))

    if rsi_value > 70:
        zone, signal = "overbought", "sell"
    elif rsi_value < 30:
        zone, signal = "oversold", "buy"
    else:
        zone, signal = "neutral", "hold"

    return {
        "rsi_value": round(rsi_value, 2),
        "zone": zone,
        "signal": signal,
    }


# ---------------------------------------------------------------------------
# 3. Mean-Reversion Signal (Bollinger Bands + Z-Score)
# ---------------------------------------------------------------------------

def compute_mean_reversion_signal(series, window: int = 12) -> dict:
    """Bollinger Bands mean-reversion signal for trade values.

    Computes rolling mean, standard deviation, and the current Z-score to
    determine whether the latest value is likely to revert towards the mean.

    Args:
        series: Numeric time-series of trade values.
        window: Rolling look-back window (months).

    Returns:
        Dict with keys:
            z_score (float): Standard deviations from the rolling mean.
            upper_band (float): Upper Bollinger band.
            lower_band (float): Lower Bollinger band.
            mean (float): Rolling mean.
            signal (str): "mean_reversion_up" / "neutral" / "mean_reversion_down".
    """
    arr = _safe_array(series)

    if len(arr) < window:
        return {
            "z_score": 0.0,
            "upper_band": 0.0,
            "lower_band": 0.0,
            "mean": float(arr[-1]) if len(arr) > 0 else 0.0,
            "signal": "neutral",
        }

    s = pd.Series(arr)
    rolling_mean = s.rolling(window=window).mean()
    rolling_std = s.rolling(window=window).std(ddof=0)

    mean_val = float(rolling_mean.iloc[-1])
    std_val = float(rolling_std.iloc[-1])
    current = float(arr[-1])

    # Fall back to overall stats if rolling std is zero
    if std_val == 0 or np.isnan(std_val):
        std_val = float(np.std(arr, ddof=0)) if np.std(arr) > 0 else 1e-9

    z_score = (current - mean_val) / std_val
    upper_band = mean_val + 2 * std_val
    lower_band = mean_val - 2 * std_val

    # Extreme Z-scores suggest mean reversion
    if z_score > 1.5:
        signal = "mean_reversion_down"  # above band, expect fall
    elif z_score < -1.5:
        signal = "mean_reversion_up"  # below band, expect rise
    else:
        signal = "neutral"

    return {
        "z_score": round(float(z_score), 2),
        "upper_band": round(upper_band, 2),
        "lower_band": round(lower_band, 2),
        "mean": round(mean_val, 2),
        "signal": signal,
    }


# ---------------------------------------------------------------------------
# 4. Breakout Signal (Donchian Channel)
# ---------------------------------------------------------------------------

def compute_breakout_signal(series, lookback: int = 24) -> dict:
    """Donchian-channel breakout detection for trade values.

    Compares the latest value against the N-period high and low to detect
    potential breakouts, with confirmation via the second-latest value.

    Args:
        series: Numeric time-series of trade values.
        lookback: Number of periods for the channel (default 24 months).

    Returns:
        Dict with keys:
            level (float): Current value.
            upper_channel (float): Highest value in lookback window.
            lower_channel (float): Lowest value in lookback window.
            is_breakout (bool): Whether the current value is a breakout.
            direction (str): "up" / "down" / "neutral".
    """
    arr = _safe_array(series)

    if len(arr) < max(lookback, 3):
        n = len(arr)
        if n == 0:
            return {
                "level": 0.0, "upper_channel": 0.0, "lower_channel": 0.0,
                "is_breakout": False, "direction": "neutral",
            }
        return {
            "level": float(arr[-1]),
            "upper_channel": float(np.max(arr)),
            "lower_channel": float(np.min(arr)),
            "is_breakout": False,
            "direction": "neutral",
        }

    window = arr[-lookback:]
    upper = float(np.max(window))
    lower = float(np.min(window))
    current = float(arr[-1])
    previous = float(arr[-2])

    # A breakout occurs when the current value surpasses the channel while
    # the previous value was still inside.
    is_up_breakout = current > upper and previous <= upper
    is_down_breakout = current < lower and previous >= lower

    is_breakout = is_up_breakout or is_down_breakout

    if is_up_breakout:
        direction = "up"
    elif is_down_breakout:
        direction = "down"
    else:
        direction = "neutral"

    return {
        "level": round(current, 2),
        "upper_channel": round(upper, 2),
        "lower_channel": round(lower, 2),
        "is_breakout": bool(is_breakout),
        "direction": direction,
    }


# ---------------------------------------------------------------------------
# 5. Volatility Signal
# ---------------------------------------------------------------------------

def compute_volatility_signal(series, window: int = 12) -> dict:
    """Rolling volatility estimation with regime detection.

    Computes the annualised (monthly) volatility of percentage changes and
    classifies the current regime as low / medium / high.

    Args:
        series: Numeric time-series of trade values.
        window: Rolling window for volatility estimation.

    Returns:
        Dict with keys:
            current_vol (float): Latest rolling volatility (%).
            historical_vol (float): Long-run average volatility (%).
            regime (str): "low" / "medium" / "high".
            trend (str): "increasing" / "decreasing" / "stable".
    """
    arr = _safe_array(series)

    if len(arr) < window + 1:
        return {
            "current_vol": 0.0,
            "historical_vol": 0.0,
            "regime": "low",
            "trend": "stable",
        }

    pct = _pct_change(arr)
    vol = pd.Series(pct).rolling(window=window).std()

    current_vol = float(vol.iloc[-1]) if np.isfinite(vol.iloc[-1]) else 0.0
    historical_vol = float(np.nanmean(vol)) if np.any(np.isfinite(vol)) else 0.0

    # Regime classification
    ratio = current_vol / historical_vol if historical_vol > 0 else 1.0

    if ratio > 1.5:
        regime = "high"
    elif ratio < 0.7:
        regime = "low"
    else:
        regime = "medium"

    # Trend: compare recent half of volatility series to earlier half
    vol_clean = vol.dropna()
    if len(vol_clean) >= 4:
        mid = len(vol_clean) // 2
        recent_avg = float(vol_clean.iloc[mid:].mean())
        earlier_avg = float(vol_clean.iloc[:mid].mean())
        if earlier_avg > 0:
            pct_change = (recent_avg - earlier_avg) / earlier_avg
            if pct_change > 0.15:
                trend = "increasing"
            elif pct_change < -0.15:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"
    else:
        trend = "stable"

    return {
        "current_vol": round(current_vol, 4),
        "historical_vol": round(historical_vol, 4),
        "regime": regime,
        "trend": trend,
    }


# ---------------------------------------------------------------------------
# 6. Composite Signal Generator
# ---------------------------------------------------------------------------

# Default weights for combining sub-signals
_SIGNAL_WEIGHTS = {
    "momentum": 0.30,
    "rsi": 0.20,
    "mean_reversion": 0.25,
    "breakout": 0.15,
    "volatility": 0.10,
}


def _sub_signal_to_score(signal_name: str, signal_data: dict) -> float:
    """Map a sub-signal result to a [-100, 100] score.

    Positive = bullish, negative = bearish.
    """
    if signal_name == "momentum":
        return float(signal_data.get("current_signal", 0))

    if signal_name == "rsi":
        # RSI 0-100 -> score: 50 is neutral, >70 is bearish, <30 is bullish
        rsi = signal_data.get("rsi_value", 50.0)
        return -(rsi - 50) * 2  # 0->100, 100->-100

    if signal_name == "mean_reversion":
        # Negative Z = undervalued = bullish
        z = signal_data.get("z_score", 0.0)
        return float(np.clip(-z * 30, -100, 100))

    if signal_name == "breakout":
        direction = signal_data.get("direction", "neutral")
        if direction == "up":
            return 80.0
        elif direction == "down":
            return -80.0
        return 0.0

    if signal_name == "volatility":
        regime = signal_data.get("regime", "medium")
        trend = signal_data.get("trend", "stable")
        base = {"low": -20, "medium": 0, "high": 20}.get(regime, 0)
        if trend == "decreasing":
            base -= 15
        elif trend == "increasing":
            base += 15
        return float(np.clip(base, -100, 100))

    return 0.0


def _build_description(action: str, composite: float, signals: dict) -> str:
    """Generate a human-readable Chinese summary of the composite signal."""
    parts = []

    if action == "BUY":
        parts.append("综合信号呈积极态势（买入信号）")
    elif action == "SELL":
        parts.append("综合信号呈消极态势（卖出信号）")
    else:
        parts.append("综合信号中性，建议观望（持有）")

    # Highlight the most influential sub-signal
    sub_scores = {}
    for name, _weight in _SIGNAL_WEIGHTS.items():
        sub_scores[name] = _sub_signal_to_score(name, signals.get(name, {}))

    name_cn = {
        "momentum": "动量",
        "rsi": "RSI",
        "mean_reversion": "均值回归",
        "breakout": "突破",
        "volatility": "波动率",
    }

    # Find strongest signal
    if sub_scores:
        strongest_name = max(sub_scores, key=lambda k: abs(sub_scores[k]))
        strongest_val = sub_scores[strongest_name]
        if abs(strongest_val) > 20:
            direction = "看涨" if strongest_val > 0 else "看跌"
            parts.append(f"主要驱动：{name_cn.get(strongest_name, strongest_name)}信号{direction}")

    # Momentum detail
    mom = signals.get("momentum", {})
    if mom.get("trend") == "up":
        parts.append("动量指标上升")
    elif mom.get("trend") == "down":
        parts.append("动量指标下降")

    # RSI detail
    rsi_data = signals.get("rsi", {})
    if rsi_data.get("zone") == "overbought":
        parts.append("RSI处于超买区域")
    elif rsi_data.get("zone") == "oversold":
        parts.append("RSI处于超卖区域")

    # Volatility detail
    vol = signals.get("volatility", {})
    if vol.get("regime") == "high":
        parts.append("市场波动率偏高，注意风险")
    elif vol.get("regime") == "low":
        parts.append("市场波动率偏低")

    # Breakout detail
    bk = signals.get("breakout", {})
    if bk.get("is_breakout"):
        if bk.get("direction") == "up":
            parts.append("检测到向上突破")
        elif bk.get("direction") == "down":
            parts.append("检测到向下突破，需关注")

    return "。".join(parts) + "。"


def generate_signals(
    trade_data: list,
    partner: str = None,
    hs_code: str = None,
    momentum_fast: int = 6,
    momentum_slow: int = 12,
    rsi_period: int = 12,
    bb_window: int = 12,
    breakout_lookback: int = 24,
    vol_window: int = 12,
) -> dict:
    """High-level API: generate a comprehensive trading signal report.

    Aggregates momentum, RSI, mean-reversion, breakout, and volatility
    signals into a single composite score with a recommended action.

    Args:
        trade_data: List of dicts, each with at least:
            - trade_value_usd (float): Trade value.
            - year (int): Year.
            - month (int): Month.
            Optional keys: partner, hs_code, id, source, etc.
        partner: ISO-3166 alpha-3 partner code to filter by (optional).
        hs_code: HS-6 product code to filter by (optional).
        momentum_fast: Fast EMA period for momentum signal.
        momentum_slow: Slow EMA period for momentum signal.
        rsi_period: RSI look-back period.
        bb_window: Bollinger Bands / mean-reversion window.
        breakout_lookback: Donchian channel look-back period.
        vol_window: Rolling volatility window.

    Returns:
        Dict with keys:
            composite_score (float): -100 (strong sell) to 100 (strong buy).
            action (str): "BUY" / "HOLD" / "SELL".
            confidence (float): 0-1, how confident the recommendation is.
            signals (dict): Sub-signal results.
            history (list): Monthly composite score history.
            description (str): Human-readable summary in Chinese.
    """
    # --- Filter and extract time series ----------------------------------
    if not trade_data:
        return _empty_report("没有可用的交易数据")

    df = pd.DataFrame(trade_data)
    if df.empty or "trade_value_usd" not in df.columns:
        return _empty_report("交易数据格式不正确")

    # Optional filtering
    if partner and "partner" in df.columns:
        df = df[df["partner"] == partner]
    if hs_code and "hs_code" in df.columns:
        df = df[df["hs_code"] == hs_code]

    if df.empty:
        return _empty_report(f"筛选后无数据（partner={partner}, hs_code={hs_code}）")

    # Build monthly time series (sorted chronologically)
    if "year" in df.columns and "month" in df.columns:
        df = df.copy()
        df["_sort_key"] = df["year"].astype(int) * 100 + df["month"].astype(int)
        df = df.sort_values("_sort_key")
        monthly = df.groupby(["year", "month"])["trade_value_usd"].sum().reset_index()
        monthly["_sort_key"] = monthly["year"].astype(int) * 100 + monthly["month"].astype(int)
        monthly = monthly.sort_values("_sort_key").reset_index(drop=True)
        series = monthly["trade_value_usd"].to_numpy(dtype=np.float64)
    else:
        series = df["trade_value_usd"].to_numpy(dtype=np.float64)

    series = _safe_array(series)

    if len(series) < 3:
        return _empty_report("数据点不足（至少需要3个月）")

    # --- Compute sub-signals ---------------------------------------------
    signals = {
        "momentum": compute_momentum_signal(series, momentum_fast, momentum_slow),
        "rsi": compute_rsi(series, rsi_period),
        "mean_reversion": compute_mean_reversion_signal(series, bb_window),
        "breakout": compute_breakout_signal(series, breakout_lookback),
        "volatility": compute_volatility_signal(series, vol_window),
    }

    # --- Composite score --------------------------------------------------
    composite_score = 0.0
    for name, weight in _SIGNAL_WEIGHTS.items():
        sub_score = _sub_signal_to_score(name, signals.get(name, {}))
        composite_score += sub_score * weight

    composite_score = float(np.clip(composite_score, -100, 100))

    # Action and confidence
    if composite_score > 25:
        action = "BUY"
    elif composite_score < -25:
        action = "SELL"
    else:
        action = "HOLD"

    confidence = min(abs(composite_score) / 75.0, 1.0)

    # --- Historical monthly scores ---------------------------------------
    history = _compute_history(
        series,
        momentum_fast=momentum_fast,
        momentum_slow=momentum_slow,
        rsi_period=rsi_period,
        bb_window=bb_window,
        breakout_lookback=breakout_lookback,
        vol_window=vol_window,
    )

    # Attach year/month labels if available
    if "year" in df.columns and "month" in df.columns:
        dates = monthly[["year", "month"]].to_dict("records")
        for i, entry in enumerate(history):
            if i < len(dates):
                entry["year"] = dates[i]["year"]
                entry["month"] = dates[i]["month"]

    # --- Assemble report --------------------------------------------------
    description = _build_description(action, composite_score, signals)

    return {
        "composite_score": round(composite_score, 2),
        "action": action,
        "confidence": round(confidence, 2),
        "signals": signals,
        "history": history,
        "description": description,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _empty_report(reason: str) -> dict:
    """Return a neutral zero-confidence report when data is insufficient."""
    return {
        "composite_score": 0.0,
        "action": "HOLD",
        "confidence": 0.0,
        "signals": {
            "momentum": compute_momentum_signal(np.array([])),
            "rsi": compute_rsi(np.array([])),
            "mean_reversion": compute_mean_reversion_signal(np.array([])),
            "breakout": compute_breakout_signal(np.array([])),
            "volatility": compute_volatility_signal(np.array([])),
        },
        "history": [],
        "description": f"数据不足，无法生成信号。{reason}",
    }


def _compute_history(
    series: np.ndarray,
    momentum_fast: int = 6,
    momentum_slow: int = 12,
    rsi_period: int = 12,
    bb_window: int = 12,
    breakout_lookback: int = 24,
    vol_window: int = 12,
) -> list:
    """Compute month-by-month composite scores for the full series.

    For each time step *t* (starting from the first window large enough for
    all sub-signals), compute the sub-signals on the slice ``series[:t+1]``
    and combine them into a composite score.

    Returns a list of dicts with keys: composite_score (float), action (str).
    """
    min_required = max(momentum_slow + 2, rsi_period + 1, bb_window, breakout_lookback, vol_window + 1)
    history = []

    for t in range(len(series)):
        segment = series[: t + 1]
        if len(segment) < min_required:
            history.append({"composite_score": 0.0, "action": "HOLD"})
            continue

        sigs = {
            "momentum": compute_momentum_signal(segment, momentum_fast, momentum_slow),
            "rsi": compute_rsi(segment, rsi_period),
            "mean_reversion": compute_mean_reversion_signal(segment, bb_window),
            "breakout": compute_breakout_signal(segment, breakout_lookback),
            "volatility": compute_volatility_signal(segment, vol_window),
        }

        score = 0.0
        for name, weight in _SIGNAL_WEIGHTS.items():
            score += _sub_signal_to_score(name, sigs.get(name, {})) * weight
        score = float(np.clip(score, -100, 100))

        if score > 25:
            action = "BUY"
        elif score < -25:
            action = "SELL"
        else:
            action = "HOLD"

        history.append({
            "composite_score": round(score, 2),
            "action": action,
        })

    return history
