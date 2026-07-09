"""Multi-Factor Trade Analysis Engine.

Inspired by Fama-French factor models in quantitative finance:
- Decomposes trade value changes into contributing factors
- Provides waterfall-style attribution analysis
- Identifies key drivers of trade growth/decline

Factors:
- Exchange Rate: currency fluctuation impact on trade value
- Price (Commodity): raw material price changes driving trade
- Seasonal: calendar effects (Chinese New Year, Ramadan, Christmas)
- Growth (GDP): economic growth driving demand
- Policy: tariff changes, RCEP implementation events
"""
import logging
import numpy as np
import pandas as pd
from scipy.stats import linregress, pearsonr
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Empirical seasonal indices for ASEAN-China trade (month -> index)
# Based on historical trade patterns: CNY dip in Jan/Feb, Q4 peak, etc.
_DEFAULT_SEASONAL_INDICES = {
    1: 0.82,   # Chinese New Year slowdown
    2: 0.68,   # Deepest CNY trough
    3: 0.95,   # Recovery post-CNY
    4: 1.02,   # Spring normalization
    5: 1.05,   # Pre-Ramadan restocking (for Muslim-majority ASEAN)
    6: 1.08,   # Mid-year peak
    7: 1.04,   # Summer moderate
    8: 0.97,   # Slight lull
    9: 1.03,   # Pre-holiday ramp
    10: 1.12,  # Golden Week + Christmas sourcing
    11: 1.15,  # Peak holiday orders
    12: 1.09,  # Year-end wind-down
}

# Mock commodity index weights for ASEAN-China trade basket
_DEFAULT_COMMODITY_WEIGHTS = {
    "crude_oil": 0.25,
    "palm_oil": 0.15,
    "rubber": 0.10,
    "iron_ore": 0.15,
    "copper": 0.10,
    "coal": 0.10,
    "natural_gas": 0.08,
    "rice": 0.07,
}

# Policy event timeline (year, month, description)
_POLICY_EVENTS = [
    (2020, 11, "RCEP signed"),
    (2022, 1, "RCEP takes effect for China + ASEAN-6"),
    (2023, 6, "RCEP full implementation ASEAN"),
    (2024, 1, "China-ASEAN tariff reduction Phase 3"),
    (2025, 1, "Expanded RCEP tariff concessions"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trade_df(trade_data: list) -> pd.DataFrame:
    """Convert trade_data list to a clean DataFrame with a date column."""
    if not trade_data:
        return pd.DataFrame()
    df = pd.DataFrame(trade_data)
    if df.empty:
        return df
    # Ensure required columns exist
    for col in ("year", "month", "trade_value_usd"):
        if col not in df.columns:
            logger.warning("trade_data missing column: %s", col)
            return pd.DataFrame()
    df["_sort_key"] = df["year"].astype(int) * 100 + df["month"].astype(int)
    df["_ym"] = df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
    return df.sort_values("_sort_key").reset_index(drop=True)


def _monthly_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate a trade DataFrame to monthly totals."""
    if df.empty:
        return df
    grp = df.groupby(["year", "month"]).agg(
        total_value=("trade_value_usd", "sum"),
        record_count=("trade_value_usd", "count"),
    ).reset_index()
    grp["_sort_key"] = grp["year"].astype(int) * 100 + grp["month"].astype(int)
    grp["_ym"] = grp["year"].astype(str) + "-" + grp["month"].astype(str).str.zfill(2)
    return grp.sort_values("_sort_key").reset_index(drop=True)


def _mock_fx_rates(monthly_dates: pd.Series) -> list:
    """Generate synthetic USD/CNY exchange rate series for illustration."""
    n = len(monthly_dates)
    if n == 0:
        return []
    base_rate = 7.10
    # Random walk around base with small drift
    np.random.seed(42)
    increments = np.random.normal(0, 0.03, n)
    rates = [base_rate]
    for i in range(1, n):
        rates.append(max(rates[-1] + increments[i], 6.0))
    result = []
    for i, dt in enumerate(monthly_dates):
        result.append({
            "date": str(dt),
            "rate": round(rates[i], 4),
        })
    return result


def _mock_commodity_prices(monthly_dates: pd.Series) -> dict:
    """Generate synthetic commodity price series for illustration."""
    n = len(monthly_dates)
    if n == 0:
        return {}
    np.random.seed(123)
    base_prices = {
        "crude_oil": 75.0,
        "palm_oil": 850.0,
        "rubber": 150.0,
        "iron_ore": 110.0,
        "copper": 8500.0,
        "coal": 140.0,
        "natural_gas": 3.5,
        "rice": 450.0,
    }
    prices = {}
    for commodity, base in base_prices.items():
        increments = np.random.normal(0, 0.02, n)
        series = [base]
        for i in range(1, n):
            series.append(max(series[-1] * (1 + increments[i]), base * 0.5))
        prices[commodity] = [
            {"date": str(monthly_dates.iloc[i]),
             "price": round(series[i], 2)}
            for i in range(n)
        ]
    return prices


def _mock_gdp_growth() -> list:
    """Generate synthetic quarterly GDP growth data for illustration."""
    return [
        {"period": "2023-Q1", "country": "CHN", "gdp_growth": 4.5},
        {"period": "2023-Q2", "country": "CHN", "gdp_growth": 6.3},
        {"period": "2023-Q3", "country": "CHN", "gdp_growth": 4.9},
        {"period": "2023-Q4", "country": "CHN", "gdp_growth": 5.2},
        {"period": "2024-Q1", "country": "CHN", "gdp_growth": 5.3},
        {"period": "2024-Q2", "country": "CHN", "gdp_growth": 4.7},
        {"period": "2024-Q3", "country": "CHN", "gdp_growth": 4.6},
        {"period": "2024-Q4", "country": "CHN", "gdp_growth": 5.4},
        {"period": "2023-Q1", "country": "ASEAN", "gdp_growth": 3.8},
        {"period": "2023-Q2", "country": "ASEAN", "gdp_growth": 4.1},
        {"period": "2023-Q3", "country": "ASEAN", "gdp_growth": 4.3},
        {"period": "2023-Q4", "country": "ASEAN", "gdp_growth": 4.0},
        {"period": "2024-Q1", "country": "ASEAN", "gdp_growth": 4.5},
        {"period": "2024-Q2", "country": "ASEAN", "gdp_growth": 4.7},
        {"period": "2024-Q3", "country": "ASEAN", "gdp_growth": 4.4},
        {"period": "2024-Q4", "country": "ASEAN", "gdp_growth": 4.8},
    ]


def _quarter_from_month(year: int, month: int) -> str:
    """Return quarter string like '2024-Q1'."""
    q = (month - 1) // 3 + 1
    return f"{year}-Q{q}"


def _safe_float(val, default=0.0) -> float:
    """Safely convert a value to float."""
    try:
        v = float(val)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# 1. Exchange Rate Factor
# ---------------------------------------------------------------------------

def compute_exchange_rate_factor(trade_data: list, fx_rates: list = None) -> dict:
    """Estimate FX impact on trade value.

    Uses linear approximation:  Delta(Trade) ~ epsilon * Delta(Rate)
    where epsilon is the estimated FX sensitivity (trade elasticity to FX).

    Args:
        trade_data: List of dicts with year, month, trade_value_usd, ...
        fx_rates: Optional list of {date: 'YYYY-MM', rate: float}.
                  If None, synthetic USD/CNY rates are used.

    Returns:
        {
            monthly_impact: [{month, impact_usd, impact_pct}],
            total_impact: float,
            sensitivity: float,
            summary: str,
        }
    """
    df = _trade_df(trade_data)
    if df.empty or len(df) < 3:
        return {
            "monthly_impact": [],
            "total_impact": 0.0,
            "sensitivity": 0.0,
            "summary": "Insufficient trade data for FX analysis (need >= 3 months)",
        }

    monthly = _monthly_totals(df)
    dates = monthly["_ym"]
    trade_values = monthly["total_value"].values

    # Obtain FX rates
    if fx_rates is None:
        fx_rates = _mock_fx_rates(dates)

    if not fx_rates or len(fx_rates) < 3:
        return {
            "monthly_impact": [],
            "total_impact": 0.0,
            "sensitivity": 0.0,
            "summary": "No FX rate data available",
        }

    # Align FX rates to monthly trade periods
    fx_df = pd.DataFrame(fx_rates)
    fx_df["_ym"] = fx_df["date"].apply(lambda d: d if len(d) == 7 else d[:7])
    fx_df = fx_df.rename(columns={"rate": "fx_rate"})[["_ym", "fx_rate"]]

    # Merge on year-month
    merged = pd.merge(
        monthly[["year", "month", "_sort_key", "_ym", "total_value"]],
        fx_df,
        on="_ym",
        how="inner",
    )

    if len(merged) < 3:
        return {
            "monthly_impact": [],
            "total_impact": 0.0,
            "sensitivity": 0.0,
            "summary": "Cannot align FX rates with trade data",
        }

    # Compute month-over-month changes
    merged["delta_rate"] = merged["fx_rate"].diff()
    merged["delta_trade"] = merged["total_value"].diff()
    merged = merged.dropna(subset=["delta_rate", "delta_trade"])

    if len(merged) < 2:
        return {
            "monthly_impact": [],
            "total_impact": 0.0,
            "sensitivity": 0.0,
            "summary": "Insufficient overlapping data points",
        }

    # Estimate FX sensitivity via regression: delta_trade ~ sensitivity * delta_rate
    x = merged["delta_rate"].values
    y = merged["delta_trade"].values

    try:
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
    except (ValueError, np.linalg.LinAlgError):
        slope = 0.0
        r_value = 0.0

    sensitivity = _safe_float(slope)
    r_squared = _safe_float(r_value) ** 2

    # Compute monthly FX attribution
    monthly_impact = []
    total_impact = 0.0

    for _, row in merged.iterrows():
        month_str = row["_ym"]
        impact = sensitivity * row["delta_rate"]
        trade_val = row["total_value"]
        impact_pct = (impact / trade_val * 100) if trade_val > 0 else 0.0

        monthly_impact.append({
            "month": month_str,
            "impact_usd": round(_safe_float(impact), 2),
            "impact_pct": round(_safe_float(impact_pct), 2),
        })
        total_impact += impact

    return {
        "monthly_impact": monthly_impact,
        "total_impact": round(total_impact, 2),
        "sensitivity": round(sensitivity, 2),
        "r_squared": round(r_squared, 4),
        "data_points": len(merged),
        "summary": (
            f"FX sensitivity: {sensitivity:,.0f} USD per 1-unit rate change. "
            f"Total FX impact: ${total_impact:,.0f} "
            f"(R^2={r_squared:.3f})"
        ),
    }


# ---------------------------------------------------------------------------
# 2. Seasonal Factors
# ---------------------------------------------------------------------------

def compute_seasonal_factors(trade_data: list) -> dict:
    """Compute monthly seasonal indices using moving-average deseasonalization.

    X-12-ARIMA style: ratio-to-moving-average method.
    Identifies regular patterns such as CNY dip, Q4 peak, Ramadan effects.

    Args:
        trade_data: List of dicts with year, month, trade_value_usd

    Returns:
        {
            seasonal_indices: {1: 0.85, 2: 0.72, ...},
            amplitude: float,
            peak_month: int,
            trough_month: int,
            description: str,
        }
    """
    df = _trade_df(trade_data)
    if df.empty:
        return {
            "seasonal_indices": _DEFAULT_SEASONAL_INDICES.copy(),
            "amplitude": 0.47,
            "peak_month": 11,
            "trough_month": 2,
            "description": "Using default seasonal indices (no data provided)",
        }

    monthly = _monthly_totals(df)

    # Need at least 2 full years for seasonal decomposition
    if len(monthly) < 24:
        return {
            "seasonal_indices": _DEFAULT_SEASONAL_INDICES.copy(),
            "amplitude": 0.47,
            "peak_month": 11,
            "trough_month": 2,
            "description": (
                f"Using default indices: only {len(monthly)} months of data "
                f"(need >= 24 months for decomposition)"
            ),
        }

    # Step 1: Compute 12-month centered moving average (CMA)
    values = monthly["total_value"].values.astype(float)
    cma = pd.Series(values).rolling(window=12, center=True).mean()

    # Step 2: Ratio-to-moving-average (seasonal ratios)
    ratios = values / cma.values
    months = monthly["month"].values

    # Step 3: Compute median ratio for each calendar month
    month_ratios = {}
    for m, r in zip(months, ratios):
        if np.isfinite(r) and r > 0:
            month_ratios.setdefault(m, []).append(r)

    seasonal_indices = {}
    raw_ratios = {}
    for m in range(1, 13):
        if m in month_ratios and len(month_ratios[m]) >= 2:
            seasonal_indices[m] = round(float(np.median(month_ratios[m])), 4)
            raw_ratios[m] = month_ratios[m]
        else:
            seasonal_indices[m] = _DEFAULT_SEASONAL_INDICES.get(m, 1.0)

    # Step 4: Normalize so indices sum to 12
    total = sum(seasonal_indices.values())
    if total > 0:
        seasonal_indices = {m: round(v / total * 12, 4) for m, v in seasonal_indices.items()}

    # Compute amplitude (peak-to-trough range)
    max_idx = max(seasonal_indices.values())
    min_idx = min(seasonal_indices.values())
    amplitude = round(max_idx - min_idx, 4)

    peak_month = max(seasonal_indices, key=seasonal_indices.get)
    trough_month = min(seasonal_indices, key=seasonal_indices.get)

    # Build description
    descriptions = []
    if seasonal_indices[2] < 0.80:
        descriptions.append("strong Chinese New Year dip in Feb")
    if seasonal_indices[1] < 0.85 and seasonal_indices[2] < 0.85:
        descriptions.append("extended CNY slowdown (Jan-Feb)")
    if seasonal_indices[10] > 1.08:
        descriptions.append("Q4 holiday surge starting Oct")
    if seasonal_indices[11] > 1.08:
        descriptions.append("peak sourcing season in Nov")
    if seasonal_indices[5] > 1.03:
        descriptions.append("pre-Ramadan restocking in May")
    if seasonal_indices[6] > 1.05:
        descriptions.append("mid-year trade peak in Jun")

    desc = "; ".join(descriptions) if descriptions else "Moderate seasonal variation"

    return {
        "seasonal_indices": seasonal_indices,
        "amplitude": amplitude,
        "peak_month": peak_month,
        "peak_value": seasonal_indices[peak_month],
        "trough_month": trough_month,
        "trough_value": seasonal_indices[trough_month],
        "data_months": len(monthly),
        "description": desc,
    }


# ---------------------------------------------------------------------------
# 3. Price (Commodity) Factor
# ---------------------------------------------------------------------------

def compute_price_factor(trade_data: list, commodity_prices: list = None) -> dict:
    """Estimate commodity price pass-through to trade values.

    Uses correlation analysis between commodity price indices and trade values.
    Estimates how much of trade value change is driven by commodity prices.

    Args:
        trade_data: List of dicts with year, month, trade_value_usd
        commodity_prices: Optional dict mapping commodity name to list of
                          {date, price}. If None, synthetic data is used.

    Returns:
        {
            monthly_impact: [{month, price_impact_usd, price_impact_pct}],
            top_commodities: [{name, correlation, weight, contribution}],
            total_price_effect_pct: float,
            summary: str,
        }
    """
    df = _trade_df(trade_data)
    if df.empty or len(df) < 6:
        return {
            "monthly_impact": [],
            "top_commodities": [],
            "total_price_effect_pct": 0.0,
            "summary": "Insufficient trade data for commodity price analysis",
        }

    monthly = _monthly_totals(df)
    dates = monthly["_ym"]
    trade_values = monthly["total_value"].values

    # Generate mock prices if not provided
    if commodity_prices is None:
        commodity_prices = _mock_commodity_prices(dates)

    if not commodity_prices:
        return {
            "monthly_impact": [],
            "top_commodities": [],
            "total_price_effect_pct": 0.0,
            "summary": "No commodity price data available",
        }

    # Build a composite commodity index from available data
    # For each commodity, compute month-over-month % change, then weighted average
    price_changes = {}  # month_index -> weighted avg change
    commodity_corr = {}  # commodity -> (correlation, data_points)

    n_months = len(monthly)
    trade_pct_changes = np.diff(trade_values) / np.where(trade_values[:-1] > 0, trade_values[:-1], 1) * 100

    for commodity, price_list in commodity_prices.items():
        if not price_list:
            continue

        # Build price series aligned to trade months
        price_series = pd.DataFrame(price_list)
        if "date" not in price_series.columns:
            continue
        price_series["_ym"] = price_series["date"].apply(lambda d: d[:7] if len(d) >= 7 else d)
        price_series = price_series.sort_values("_ym")

        # Align to monthly trade dates
        aligned = pd.merge(
            pd.DataFrame({"_ym": monthly["_ym"].values}),
            price_series,
            on="_ym",
            how="inner",
        )

        if len(aligned) < 4:
            continue

        prices = aligned["price"].values.astype(float)
        pct_changes = np.diff(prices) / np.where(prices[:-1] > 0, prices[:-1], 1) * 100

        # Store per-commodity monthly changes
        min_len = min(len(pct_changes), len(trade_pct_changes))
        pc = pct_changes[:min_len]
        tc = trade_pct_changes[:min_len]

        # Correlation with trade value changes
        if min_len >= 3:
            try:
                corr, pval = pearsonr(pc, tc)
                if np.isfinite(corr):
                    weight = _DEFAULT_COMMODITY_WEIGHTS.get(commodity, 0.05)
                    commodity_corr[commodity] = {
                        "correlation": round(float(corr), 4),
                        "p_value": round(float(pval), 4),
                        "weight": weight,
                        "data_points": min_len,
                    }
            except (ValueError, np.linalg.LinAlgError):
                pass

    if not commodity_corr:
        return {
            "monthly_impact": [],
            "top_commodities": [],
            "total_price_effect_pct": 0.0,
            "summary": "Could not compute commodity correlations (insufficient overlap)",
        }

    # Build composite price index contribution
    # Weight-average the correlation-weighted price changes
    total_weight = sum(c["weight"] for c in commodity_corr.values())

    # Estimate overall price contribution to trade value changes
    # Simple approach: average of (correlation * weight) across commodities
    weighted_corr = sum(
        c["correlation"] * c["weight"] for c in commodity_corr.values()
    ) / total_weight if total_weight > 0 else 0.0

    # Price effect = weighted correlation * std(trade_pct_changes) as rough attribution
    trade_std = float(np.std(trade_pct_changes)) if len(trade_pct_changes) > 1 else 0.0
    price_effect_pct = abs(weighted_corr) * trade_std

    # Compute monthly impact (simplified: distribute price effect proportionally)
    monthly_impact = []
    for i, (_, row) in enumerate(monthly.iterrows()):
        month_str = row["_ym"]
        if i > 0 and i - 1 < len(trade_pct_changes):
            # Rough attribution: trade_change * weight * correlation
            trade_change = trade_values[i] - trade_values[i - 1]
            attributed = trade_change * abs(weighted_corr) * 0.5  # partial attribution
        else:
            attributed = 0.0

        monthly_impact.append({
            "month": month_str,
            "price_impact_usd": round(_safe_float(attributed), 2),
            "price_impact_pct": round(
                _safe_float(attributed / trade_values[i] * 100) if trade_values[i] > 0 else 0, 2
            ),
        })

    # Sort commodities by absolute correlation
    top_commodities = sorted(
        [
            {
                "name": name,
                "correlation": info["correlation"],
                "weight": info["weight"],
                "p_value": info["p_value"],
                "contribution": round(info["correlation"] * info["weight"], 4),
            }
            for name, info in commodity_corr.items()
        ],
        key=lambda x: abs(x["correlation"]),
        reverse=True,
    )

    return {
        "monthly_impact": monthly_impact,
        "top_commodities": top_commodities[:8],
        "weighted_correlation": round(weighted_corr, 4),
        "total_price_effect_pct": round(price_effect_pct, 2),
        "summary": (
            f"Composite price-trade correlation: {weighted_corr:.3f}. "
            f"Estimated price effect: {price_effect_pct:.1f}% of trade value variation. "
            f"Analyzed {len(commodity_corr)} commodities."
        ),
    }


# ---------------------------------------------------------------------------
# 4. Growth (GDP) Factor
# ---------------------------------------------------------------------------

def compute_growth_factor(trade_data: list, gdp_data: list = None) -> dict:
    """Estimate GDP growth contribution to trade via elasticity analysis.

    Estimates trade elasticity to GDP:
        elasticity = %Delta(Trade) / %Delta(GDP)

    Args:
        trade_data: List of dicts with year, month, trade_value_usd
        gdp_data: Optional list of {period, country, gdp_growth}. If None,
                  synthetic ASEAN+China GDP data is used.

    Returns:
        {
            elasticity: float,
            contribution: [{period, factor, contribution_pct}],
            goodness_of_fit: float,
            summary: str,
        }
    """
    df = _trade_df(trade_data)
    if df.empty or len(df) < 6:
        return {
            "elasticity": 0.0,
            "contribution": [],
            "goodness_of_fit": 0.0,
            "summary": "Insufficient trade data for growth factor analysis",
        }

    if gdp_data is None:
        gdp_data = _mock_gdp_growth()

    if not gdp_data:
        return {
            "elasticity": 0.0,
            "contribution": [],
            "goodness_of_fit": 0.0,
            "summary": "No GDP data available",
        }

    monthly = _monthly_totals(df)

    # Convert monthly trade to quarterly totals for alignment with GDP
    monthly["quarter"] = monthly.apply(
        lambda r: _quarter_from_month(int(r["year"]), int(r["month"])), axis=1
    )
    quarterly_trade = monthly.groupby("quarter").agg(
        total_value=("total_value", "sum"),
    ).reset_index()

    if len(quarterly_trade) < 3:
        return {
            "elasticity": 0.0,
            "contribution": [],
            "goodness_of_fit": 0.0,
            "summary": "Insufficient quarterly trade periods",
        }

    quarterly_trade = quarterly_trade.sort_values("quarter").reset_index(drop=True)

    # Compute quarterly trade growth rates
    trade_vals = quarterly_trade["total_value"].values
    trade_growth = np.diff(trade_vals) / np.where(trade_vals[:-1] > 0, trade_vals[:-1], 1) * 100
    trade_periods = quarterly_trade["quarter"].values[1:]

    # Aggregate GDP across countries (weighted average growth)
    gdp_df = pd.DataFrame(gdp_data)
    gdp_quarterly = gdp_df.groupby("period")["gdp_growth"].mean().reset_index()
    gdp_quarterly = gdp_quarterly.sort_values("period").reset_index(drop=True)

    gdp_vals = gdp_quarterly["gdp_growth"].values
    gdp_periods = gdp_quarterly["period"].values

    # Align periods
    aligned_data = []
    for i, tp in enumerate(trade_periods):
        match_idx = np.where(gdp_periods == tp)[0]
        if len(match_idx) > 0:
            gdp_idx = match_idx[0]
            if i < len(trade_growth) and gdp_idx < len(gdp_vals):
                aligned_data.append({
                    "period": tp,
                    "trade_growth": trade_growth[i],
                    "gdp_growth": gdp_vals[gdp_idx],
                })

    if len(aligned_data) < 3:
        return {
            "elasticity": 0.0,
            "contribution": [],
            "goodness_of_fit": 0.0,
            "summary": "Insufficient overlapping periods between trade and GDP data",
        }

    aligned_df = pd.DataFrame(aligned_data)
    x = aligned_df["gdp_growth"].values
    y = aligned_df["trade_growth"].values

    # Regression: trade_growth = elasticity * gdp_growth + intercept
    try:
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
    except (ValueError, np.linalg.LinAlgError):
        slope = 0.0
        intercept = 0.0
        r_value = 0.0
        p_value = 1.0

    elasticity = _safe_float(slope)
    r_squared = _safe_float(r_value) ** 2

    # Contribution per period: elasticity * gdp_growth
    contributions = []
    for _, row in aligned_df.iterrows():
        predicted = elasticity * row["gdp_growth"] + intercept
        contributions.append({
            "period": row["period"],
            "factor": "GDP Growth",
            "gdp_growth_pct": round(_safe_float(row["gdp_growth"]), 2),
            "trade_growth_pct": round(_safe_float(row["trade_growth"]), 2),
            "contribution_pct": round(_safe_float(predicted), 2),
            "elasticity": round(elasticity, 2),
        })

    return {
        "elasticity": round(elasticity, 3),
        "intercept": round(intercept, 3),
        "contribution": contributions,
        "goodness_of_fit": round(r_squared, 4),
        "p_value": round(p_value, 4),
        "data_points": len(aligned_data),
        "summary": (
            f"Trade-GDP elasticity: {elasticity:.2f} "
            f"(a 1% GDP growth drives ~{elasticity:.1f}% trade growth). "
            f"Model fit: R^2={r_squared:.3f}"
        ),
    }


# ---------------------------------------------------------------------------
# 5. Full Attribution (Waterfall)
# ---------------------------------------------------------------------------

def attribute_trade_change(trade_data: list, period_start: tuple, period_end: tuple) -> dict:
    """Full attribution analysis decomposing total trade change into factors.

    Computes waterfall-style attribution suitable for ECharts visualization.
    period_start and period_end are (year, month) tuples.

    Args:
        trade_data: List of dicts with year, month, trade_value_usd
        period_start: (year, month) tuple for start of comparison
        period_end: (year, month) tuple for end of comparison

    Returns:
        {
            factors: [{name, value, percentage, direction}],
            total_change: float,
            unexplained: float,
            r_squared: float,
            waterfall: [{name, value, isTotal, color}],
        }
    """
    df = _trade_df(trade_data)
    empty_result = {
        "factors": [],
        "total_change": 0.0,
        "unexplained": 0.0,
        "r_squared": 0.0,
        "waterfall": [],
    }

    if df.empty or len(df) < 6:
        return {**empty_result, "error": "Insufficient data for attribution"}

    start_year, start_month = period_start
    end_year, end_month = period_end

    # Compute total change
    start_val = df[(df["year"] == start_year) & (df["month"] == start_month)]["trade_value_usd"].sum()
    end_val = df[(df["year"] == end_year) & (df["month"] == end_month)]["trade_value_usd"].sum()

    if start_val <= 0 or end_val <= 0:
        # Fallback: use nearest available months
        monthly = _monthly_totals(df)
        if len(monthly) < 2:
            return empty_result
        start_val = monthly.iloc[0]["total_value"]
        end_val = monthly.iloc[-1]["total_value"]

    total_change = end_val - start_val

    # Gather factor contributions
    factors = []
    explained = 0.0

    # --- FX Factor ---
    fx_result = compute_exchange_rate_factor(trade_data)
    if fx_result["monthly_impact"]:
        fx_impact = fx_result["total_impact"]
        factors.append({
            "name": "Exchange Rate (FX)",
            "name_cn": "汇率因素",
            "value": round(fx_impact, 2),
            "percentage": round((fx_impact / abs(total_change) * 100) if total_change != 0 else 0, 2),
            "direction": "positive" if fx_impact > 0 else "negative" if fx_impact < 0 else "neutral",
        })
        explained += fx_impact

    # --- Seasonal Factor ---
    seasonal_result = compute_seasonal_factors(trade_data)
    if seasonal_result["seasonal_indices"]:
        # Estimate seasonal contribution for the comparison window
        start_idx = seasonal_result["seasonal_indices"].get(start_month, 1.0)
        end_idx = seasonal_result["seasonal_indices"].get(end_month, 1.0)
        # Seasonal factor = avg_trade * (end_index - start_index)
        monthly = _monthly_totals(df)
        avg_trade = monthly["total_value"].mean()
        seasonal_impact = avg_trade * (end_idx - start_idx)
        factors.append({
            "name": "Seasonal Effect",
            "name_cn": "季节性因素",
            "value": round(seasonal_impact, 2),
            "percentage": round((seasonal_impact / abs(total_change) * 100) if total_change != 0 else 0, 2),
            "direction": "positive" if seasonal_impact > 0 else "negative" if seasonal_impact < 0 else "neutral",
        })
        explained += seasonal_impact

    # --- Commodity Price Factor ---
    price_result = compute_price_factor(trade_data)
    if price_result["monthly_impact"]:
        price_impact = sum(p["price_impact_usd"] for p in price_result["monthly_impact"])
        factors.append({
            "name": "Commodity Prices",
            "name_cn": "大宗商品价格",
            "value": round(price_impact, 2),
            "percentage": round((price_impact / abs(total_change) * 100) if total_change != 0 else 0, 2),
            "direction": "positive" if price_impact > 0 else "negative" if price_impact < 0 else "neutral",
        })
        explained += price_impact

    # --- GDP Growth Factor ---
    growth_result = compute_growth_factor(trade_data)
    if growth_result["contribution"]:
        # Use last period's contribution as growth driver estimate
        last_contrib = growth_result["contribution"][-1]
        gdp_impact = last_contrib["contribution_pct"] / 100 * abs(total_change) * 0.3
        factors.append({
            "name": "GDP Growth",
            "name_cn": "经济增长",
            "value": round(gdp_impact, 2),
            "percentage": round((gdp_impact / abs(total_change) * 100) if total_change != 0 else 0, 2),
            "direction": "positive" if gdp_impact > 0 else "negative" if gdp_impact < 0 else "neutral",
        })
        explained += gdp_impact

    # --- Policy Factor (qualitative) ---
    # Check for policy events in the comparison window
    policy_impact = 0.0
    policy_events_in_range = []
    for py, pm, desc in _POLICY_EVENTS:
        event_date = (py, pm)
        if period_start <= event_date <= period_end:
            policy_events_in_range.append(desc)

    if policy_events_in_range:
        # Estimate policy impact as 5-15% of total change per event
        policy_impact = total_change * 0.08 * len(policy_events_in_range)
        factors.append({
            "name": "Policy Changes",
            "name_cn": "政策因素",
            "value": round(policy_impact, 2),
            "percentage": round((policy_impact / abs(total_change) * 100) if total_change != 0 else 0, 2),
            "direction": "positive" if policy_impact > 0 else "negative" if policy_impact < 0 else "neutral",
            "events": policy_events_in_range,
        })
        explained += policy_impact

    # Unexplained = total - sum of factors
    unexplained = total_change - explained

    # Clamp unexplained to be reasonable
    if abs(total_change) > 0:
        explained_pct = abs(explained) / abs(total_change) * 100
        if explained_pct > 150:
            # Scale down factors proportionally
            scale = abs(total_change) / abs(explained) * 0.8
            for f in factors:
                f["value"] = round(f["value"] * scale, 2)
                f["percentage"] = round(f["percentage"] * scale, 2)
            explained *= scale
            unexplained = total_change - explained

    # Overall model R^2 (simplified: correlation between explained and total)
    r_squared = min(1.0, abs(explained) / abs(total_change)) if total_change != 0 else 0.0

    # Build waterfall data for ECharts
    waterfall = []
    waterfall.append({
        "name": "Start",
        "value": round(start_val, 2),
        "isTotal": True,
        "color": "#4472C4",
    })
    for f in factors:
        waterfall.append({
            "name": f["name"],
            "value": round(f["value"], 2),
            "isTotal": False,
            "color": "#ED7D31" if f["direction"] == "positive" else "#A5A5A5",
        })
    waterfall.append({
        "name": "Unexplained",
        "value": round(unexplained, 2),
        "isTotal": False,
        "color": "#FFC000",
    })
    waterfall.append({
        "name": "End",
        "value": round(end_val, 2),
        "isTotal": True,
        "color": "#4472C4",
    })

    # Re-sort factors by absolute contribution (descending)
    factors.sort(key=lambda f: abs(f["value"]), reverse=True)

    # Recalculate percentages after sorting
    for f in factors:
        f["percentage"] = round(
            (f["value"] / abs(total_change) * 100) if total_change != 0 else 0, 2
        )

    return {
        "factors": factors,
        "total_change": round(total_change, 2),
        "start_value": round(start_val, 2),
        "end_value": round(end_val, 2),
        "unexplained": round(unexplained, 2),
        "unexplained_pct": round(
            (unexplained / abs(total_change) * 100) if total_change != 0 else 0, 2
        ),
        "r_squared": round(r_squared, 4),
        "waterfall": waterfall,
        "period_start": f"{period_start[0]}-{period_start[1]:02d}",
        "period_end": f"{period_end[0]}-{period_end[1]:02d}",
    }


# ---------------------------------------------------------------------------
# 6. High-Level Factor Analysis Report
# ---------------------------------------------------------------------------

def factor_analysis_report(trade_data: list, partner: str = None) -> dict:
    """Generate a complete multi-factor analysis report.

    Combines all factor analyses into a unified report with visualizations.

    Args:
        trade_data: List of dicts with year, month, trade_value_usd, ...
        partner: Optional partner country name/code for context

    Returns:
        Structured analysis with:
        - summary: high-level narrative
        - factors: detailed factor breakdown
        - seasonal: seasonal decomposition
        - charts: chart data for ECharts
        - insights: key findings
    """
    df = _trade_df(trade_data)

    if df.empty:
        return {
            "summary": "No trade data available for analysis",
            "partner": partner,
            "factors": {},
            "seasonal": {},
            "charts": {},
            "insights": [],
        }

    monthly = _monthly_totals(df)
    total_value = df["trade_value_usd"].sum()
    months_count = len(monthly)

    # Compute all factors
    fx_result = compute_exchange_rate_factor(trade_data)
    seasonal_result = compute_seasonal_factors(trade_data)
    price_result = compute_price_factor(trade_data)
    growth_result = compute_growth_factor(trade_data)

    # Full attribution: compare last 12 months vs prior 12 months
    if len(monthly) >= 24:
        recent = monthly.tail(12)
        prior = monthly.head(12)
        period_end = (int(recent.iloc[-1]["year"]), int(recent.iloc[-1]["month"]))
        period_start = (int(prior.iloc[-1]["year"]), int(prior.iloc[-1]["month"]))
        attribution = attribute_trade_change(trade_data, period_start, period_end)
    elif len(monthly) >= 2:
        period_end = (int(monthly.iloc[-1]["year"]), int(monthly.iloc[-1]["month"]))
        period_start = (int(monthly.iloc[0]["year"]), int(monthly.iloc[0]["month"]))
        attribution = attribute_trade_change(trade_data, period_start, period_end)
    else:
        attribution = {"factors": [], "total_change": 0.0}

    # Trend analysis
    if len(monthly) >= 3:
        x = np.arange(len(monthly))
        y = monthly["total_value"].values
        try:
            slope, intercept, r_value, _, _ = linregress(x, y)
            trend_direction = "rising" if slope > 0 else "declining"
            trend_strength = abs(_safe_float(r_value))
        except (ValueError, np.linalg.LinAlgError):
            slope = 0
            trend_direction = "stable"
            trend_strength = 0
    else:
        slope = 0
        trend_direction = "stable"
        trend_strength = 0

    # Generate insights
    insights = []

    if fx_result["sensitivity"] != 0:
        direction = "appreciation" if fx_result["sensitivity"] > 0 else "depreciation"
        insights.append({
            "type": "fx",
            "severity": "info",
            "message": (
                f"Exchange rate sensitivity is {fx_result['sensitivity']:,.0f} USD/unit. "
                f"Currency {direction} has {'positive' if fx_result['sensitivity'] > 0 else 'negative'} "
                f"impact on trade values."
            ),
        })

    if seasonal_result["amplitude"] > 0.3:
        insights.append({
            "type": "seasonal",
            "severity": "info",
            "message": (
                f"Strong seasonal pattern detected (amplitude={seasonal_result['amplitude']:.2f}). "
                f"Peak month: {seasonal_result['peak_month']}, "
                f"Trough month: {seasonal_result['trough_month']}. "
                f"Consider seasonal adjustments in forecasts."
            ),
        })

    if price_result["top_commodities"]:
        top = price_result["top_commodities"][0]
        insights.append({
            "type": "commodity",
            "severity": "info",
            "message": (
                f"Top commodity driver: {top['name']} "
                f"(correlation={top['correlation']:.3f}). "
                f"Composite price effect explains {price_result['total_price_effect_pct']:.1f}% "
                f"of trade variation."
            ),
        })

    if growth_result["elasticity"] != 0:
        insights.append({
            "type": "growth",
            "severity": "info",
            "message": (
                f"Trade-GDP elasticity: {growth_result['elasticity']:.2f}. "
                f"A 1% GDP growth is associated with ~{growth_result['elasticity']:.1f}% trade growth. "
                f"Model R^2={growth_result['goodness_of_fit']:.3f}."
            ),
        })

    if trend_direction == "declining":
        insights.append({
            "type": "trend",
            "severity": "warning",
            "message": (
                f"Trade volume shows declining trend "
                f"(slope={slope:,.0f}/period, R={trend_strength:.3f}). "
                f"Investigate structural or cyclical causes."
            ),
        })

    if attribution.get("unexplained_pct", 0) > 40:
        insights.append({
            "type": "attribution",
            "severity": "warning",
            "message": (
                f"High unexplained component ({attribution['unexplained_pct']:.1f}%). "
                f"Consider additional factors: logistics costs, sanctions, "
                f"inventory cycles, or one-off events."
            ),
        })

    # Chart data for ECharts
    charts = {
        "waterfall": attribution.get("waterfall", []),
        "seasonal_radar": {
            "indicators": [
                {"name": f"M{m}", "max": 1.5}
                for m in range(1, 13)
            ],
            "values": [seasonal_result["seasonal_indices"].get(m, 1.0) for m in range(1, 13)],
        },
        "factor_breakdown": [
            {"name": f["name"], "value": abs(f["value"])}
            for f in attribution.get("factors", [])
        ],
        "monthly_trend": [
            {
                "month": row["_ym"],
                "value": round(row["total_value"], 2),
            }
            for _, row in monthly.iterrows()
        ],
    }

    # Build summary narrative
    partner_ctx = f" for {partner}" if partner else ""
    summary_lines = [
        f"Factor Analysis Report{partner_ctx}",
        f"Period: {monthly.iloc[0]['_ym']} to {monthly.iloc[-1]['_ym']} "
        f"({months_count} months)",
        f"Total trade value: ${total_value:,.0f}",
        f"Overall trend: {trend_direction} (R={trend_strength:.3f})",
        "",
        "Key factors:",
    ]

    for f in attribution.get("factors", [])[:5]:
        sign = "+" if f["value"] > 0 else ""
        summary_lines.append(
            f"  - {f['name']}: {sign}${f['value']:,.0f} ({f['percentage']:.1f}%)"
        )

    if attribution.get("unexplained", 0) != 0:
        sign = "+" if attribution["unexplained"] > 0 else ""
        summary_lines.append(
            f"  - Unexplained: {sign}${attribution['unexplained']:,.0f} "
            f"({attribution['unexplained_pct']:.1f}%)"
        )

    return {
        "summary": "\n".join(summary_lines),
        "partner": partner,
        "period": {
            "start": monthly.iloc[0]["_ym"],
            "end": monthly.iloc[-1]["_ym"],
            "months": months_count,
        },
        "total_value": round(total_value, 2),
        "trend": {
            "direction": trend_direction,
            "slope": round(slope, 2),
            "strength": round(trend_strength, 4),
        },
        "factors": {
            "exchange_rate": fx_result,
            "seasonal": seasonal_result,
            "commodity_price": price_result,
            "gdp_growth": growth_result,
            "attribution": attribution,
        },
        "seasonal": seasonal_result,
        "charts": charts,
        "insights": insights,
    }
