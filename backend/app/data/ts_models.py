"""Advanced Time Series Models for Trade Forecasting.

Replaces mock LSTM with production-grade models:
- ARIMA/SARIMA with auto parameter selection (AIC/BIC)
- Holt-Winters Triple Exponential Smoothing
- STL Decomposition (Trend + Seasonal + Residual)
- Prophet-style change point detection
- Model ensemble with walk-forward validation
"""

import logging
import warnings
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conditional imports -- the module works even if statsmodels is absent or
# only partially installed.  Every public function degrades gracefully.
# ---------------------------------------------------------------------------
_HAS_STATS_MODELS = False
_adfuller = None
_ARIMA = None
_ExpSmoothing = None
_STL = None

try:
    from statsmodels.tsa.stattools import adfuller as _adfuller  # noqa: F811
    from statsmodels.tsa.arima.model import ARIMA as _ARIMA  # noqa: F811
    from statsmodels.tsa.holtwinters import ExponentialSmoothing as _ExpSmoothing  # noqa: F811
    from statsmodels.tsa.seasonal import STL as _STL  # noqa: F811

    _HAS_STATS_MODELS = True
except ImportError:
    logger.warning(
        "statsmodels not fully available -- time-series models will use "
        "lightweight fallbacks."
    )

# Minimum observations required for each model family
_MIN_ARIMA = 12
_MIN_HW = 24
_MIN_STL = 24
_MIN_CP = 10


def _missing_sm_error(model_name: str) -> dict[str, Any]:
    """Standard error dict when statsmodels is unavailable."""
    return {
        "model": model_name,
        "error": "statsmodels not installed -- pip install statsmodels",
        "fitted": [],
        "forecast": [],
    }


# =========================================================================
# Internal helpers
# =========================================================================

def _clean_series(data: np.ndarray) -> np.ndarray:
    """Remove NaN/Inf and flatten to 1-D float array."""
    arr = np.asarray(data, dtype=float).ravel()
    arr = arr[np.isfinite(arr)]
    return arr


def _is_constant(arr: np.ndarray, tol: float = 1e-12) -> bool:
    """True if every value is (approximately) the same."""
    if len(arr) < 2:
        return True
    return float(np.ptp(arr)) < tol * (abs(float(np.mean(arr))) + 1.0)


def _safe_forecast_dates(n_hist: int, horizon: int, last_year: int,
                         last_month: int) -> list[str]:
    """Generate YYYY-MM date strings for the forecast horizon."""
    dates: list[str] = []
    y, m = last_year, last_month
    for _ in range(horizon):
        m += 1
        if m > 12:
            m = 1
            y += 1
        dates.append(f"{y}-{m:02d}")
    return dates


def _aic_weight(aic_values: dict[str, float]) -> dict[str, float]:
    """Inverse-AIC weighting so lower-AIC models get higher weight.

    Returns normalised weights summing to 1.0.
    """
    if not aic_values:
        return {}
    aics = np.array(list(aic_values.values()), dtype=float)
    # Shift so minimum is 0 (avoids overflow in exp)
    shifted = aics - aics.min()
    raw = np.exp(-0.5 * shifted)
    total = raw.sum()
    if total == 0:
        n = len(raw)
        return {k: 1.0 / n for k in aic_values}
    return {k: float(v / total) for k, v in zip(aic_values, raw)}


def _constant_forecast(arr: np.ndarray, horizon: int,
                       dates: list[str]) -> list[dict]:
    """Produce flat-line forecast for a constant (or near-constant) series."""
    val = float(np.mean(arr))
    std = float(max(np.std(arr), abs(val) * 0.02))
    pts: list[dict] = []
    for i, d in enumerate(dates):
        margin = std * (1 + 0.1 * i)
        pts.append(
            {"date": d, "predicted": round(val, 2),
             "lower": round(val - margin, 2), "upper": round(val + margin, 2)}
        )
    return pts


def _compute_mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Mean Absolute Percentage Error (%).  Ignores zero actuals."""
    mask = np.abs(actual) > 1e-10
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def _adstock_order(data: np.ndarray, max_lag: int = 1) -> int:
    """Pick differencing order via ADF test (0 or 1)."""
    if len(data) < 6 or _adfuller is None:
        return 0
    try:
        pvalue = _adfuller(data, autolag="AIC")[1]
        return 0 if pvalue < 0.05 else min(max_lag, 1)
    except Exception:
        return 1 if np.abs(np.mean(np.diff(data))) > 0 else 0


# =========================================================================
# 1.  Auto ARIMA / SARIMA
# =========================================================================

def auto_arima(
    data: np.ndarray,
    seasonal: bool = True,
    max_p: int = 5,
    max_q: int = 5,
    seasonal_period: int = 12,
) -> dict[str, Any]:
    """Auto-select the best ARIMA/SARIMA (p,d,q) via AIC minimisation.

    Parameters
    ----------
    data : np.ndarray
        1-D time series of observed values.
    seasonal : bool
        Whether to fit a seasonal (SARIMA) variant.
    max_p, max_q : int
        Maximum autoregressive / moving-average orders to search.
    seasonal_period : int
        Seasonal period (default 12 for monthly data).

    Returns
    -------
    dict with keys:
        fitted, forecast, confidence intervals, model summary,
        selected order, AIC/BIC, diagnostics.
    """
    arr = _clean_series(data)
    if len(arr) < _MIN_ARIMA:
        return {
            "model": "auto_arima",
            "error": f"Insufficient data ({len(arr)} obs, need >= {_MIN_ARIMA})",
            "fitted": [],
            "forecast": [],
        }

    if _is_constant(arr):
        n = len(arr)
        last_year = 2024  # placeholder; caller should override via forecast_trade_series
        dates = _safe_forecast_dates(n, 6, 2024, 1)
        pts = _constant_forecast(arr, 6, dates)
        return {
            "model": "auto_arima",
            "order": (0, 0, 0),
            "aic": 0.0,
            "bic": 0.0,
            "fitted": [round(float(v), 2) for v in arr],
            "forecast": pts,
            "diagnostics": {"constant_series": True},
        }

    if not _HAS_STATS_MODELS:
        return _missing_sm_error("auto_arima")

    d = _adstock_order(arr)

    best_aic = np.inf
    best_order = (1, d, 1)
    best_model = None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p in range(0, max_p + 1):
            for q in range(0, max_q + 1):
                if p == 0 and q == 0:
                    continue
                try:
                    if seasonal and len(arr) >= 2 * seasonal_period:
                        m = _ARIMA(
                            arr,
                            order=(p, d, q),
                            seasonal_order=(1, 0, 1, seasonal_period),
                            enforce_stationarity=False,
                            enforce_invertibility=False,
                        )
                    else:
                        m = _ARIMA(
                            arr, order=(p, d, q),
                            enforce_stationarity=False,
                            enforce_invertibility=False,
                        )
                    res = m.fit()
                    if res.aic < best_aic:
                        best_aic = res.aic
                        best_order = (p, d, q)
                        best_model = res
                except Exception:
                    continue

    if best_model is None:
        return {
            "model": "auto_arima",
            "error": "Could not fit any ARIMA model",
            "fitted": [],
            "forecast": [],
        }

    fitted_vals = best_model.fittedvalues

    # Forecast
    n_forecast = 6
    forecast_result = best_model.get_forecast(steps=n_forecast)
    mean_fc = forecast_result.predicted_mean
    ci = forecast_result.conf_int(alpha=0.05)

    dates_fc = _safe_forecast_dates(len(arr), n_forecast, 2024, 1)

    def _fc_val(obj: Any, i: int) -> float:
        """Extract value from Series or ndarray."""
        return float(obj.iloc[i]) if hasattr(obj, "iloc") else float(obj[i])

    def _ci_val(obj: Any, i: int, col: int) -> float:
        """Extract CI value from DataFrame/Series or ndarray."""
        if hasattr(obj, "iloc"):
            return float(obj.iloc[i, col]) if obj.ndim == 2 else float(obj.iloc[i])
        arr_obj = np.asarray(obj)
        return float(arr_obj[i, col]) if arr_obj.ndim == 2 else float(arr_obj[i])

    forecast_points = []
    for i in range(n_forecast):
        forecast_points.append({
            "date": dates_fc[i],
            "predicted": round(_fc_val(mean_fc, i), 2),
            "lower": round(_ci_val(ci, i, 0), 2),
            "upper": round(_ci_val(ci, i, 1), 2),
        })

    return {
        "model": "auto_arima",
        "order": best_order,
        "aic": round(float(best_model.aic), 2),
        "bic": round(float(best_model.bic), 2),
        "fitted": [round(float(v), 2) for v in fitted_vals],
        "forecast": forecast_points,
        "diagnostics": {
            "n_obs": len(arr),
            "differencing_order": d,
            "seasonal": seasonal,
        },
    }


# =========================================================================
# 2.  Holt-Winters Triple Exponential Smoothing
# =========================================================================

def holt_winters(
    data: np.ndarray,
    seasonal_periods: int = 12,
) -> dict[str, Any]:
    """Triple exponential smoothing with auto seasonal-type detection.

    Parameters
    ----------
    data : np.ndarray
        1-D time series.
    seasonal_periods : int
        Number of observations per seasonal cycle.

    Returns
    -------
    dict with fitted values, forecast, confidence intervals, diagnostics.
    """
    arr = _clean_series(data)
    if len(arr) < _MIN_HW:
        return {
            "model": "holt_winters",
            "error": f"Insufficient data ({len(arr)} obs, need >= {_MIN_HW})",
            "fitted": [],
            "forecast": [],
        }

    if _is_constant(arr):
        dates = _safe_forecast_dates(len(arr), 6, 2024, 1)
        pts = _constant_forecast(arr, 6, dates)
        return {
            "model": "holt_winters",
            "seasonal_type": "none",
            "fitted": [round(float(v), 2) for v in arr],
            "forecast": pts,
            "diagnostics": {"constant_series": True},
        }

    if not _HAS_STATS_MODELS:
        return _missing_sm_error("holt_winters")

    best_aic = np.inf
    best_type = "add"
    best_model = None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for stype in ("add", "mul"):
            try:
                m = _ExpSmoothing(
                    arr,
                    trend="add",
                    seasonal=stype,
                    seasonal_periods=seasonal_periods,
                    initialization_method="estimated",
                )
                res = m.fit(optimized=True)
                if res.aic < best_aic:
                    best_aic = res.aic
                    best_type = stype
                    best_model = res
            except Exception:
                continue

    if best_model is None:
        return {
            "model": "holt_winters",
            "error": "Could not fit Holt-Winters model",
            "fitted": [],
            "forecast": [],
        }

    fitted_vals = best_model.fittedvalues

    # Forecast
    n_forecast = 6
    fc = best_model.forecast(steps=n_forecast)
    # Approximate confidence intervals using residual std
    resid = arr - fitted_vals[: len(arr)]
    resid_std = float(np.std(resid)) if len(resid) > 1 else 0.0
    z = 1.96  # 95 %

    dates_fc = _safe_forecast_dates(len(arr), n_forecast, 2024, 1)
    forecast_points = []
    for i in range(n_forecast):
        fc_val = float(fc.iloc[i]) if hasattr(fc, "iloc") else float(fc[i])
        se = resid_std * np.sqrt(1 + 0.1 * i)
        forecast_points.append({
            "date": dates_fc[i],
            "predicted": round(fc_val, 2),
            "lower": round(fc_val - z * se, 2),
            "upper": round(fc_val + z * se, 2),
        })

    return {
        "model": "holt_winters",
        "seasonal_type": best_type,
        "aic": round(float(best_model.aic), 2),
        "fitted": [round(float(v), 2) for v in fitted_vals],
        "forecast": forecast_points,
        "diagnostics": {
            "n_obs": len(arr),
            "seasonal_periods": seasonal_periods,
        },
    }


# =========================================================================
# 3.  STL Decomposition
# =========================================================================

def stl_decompose(
    data: np.ndarray,
    period: int = 12,
) -> dict[str, Any]:
    """STL (Seasonal and Trend decomposition using Loess).

    Parameters
    ----------
    data : np.ndarray
        1-D time series.
    period : int
        Seasonal period.

    Returns
    -------
    dict with trend, seasonal, residual component arrays and summary.
    """
    if not _HAS_STATS_MODELS:
        err = _missing_sm_error("stl_decompose")
        err["trend"] = []
        err["seasonal"] = []
        err["residual"] = []
        return err

    arr = _clean_series(data)
    if len(arr) < _MIN_STL:
        return {
            "model": "stl_decompose",
            "error": f"Insufficient data ({len(arr)} obs, need >= {_MIN_STL})",
            "trend": [],
            "seasonal": [],
            "residual": [],
        }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stl = _STL(arr, period=period, robust=True)
        result = stl.fit()

    trend = result.trend
    seasonal = result.seasonal
    resid = result.resid

    # Strength of seasonality (Hyndman, 2021)
    var_resid = float(np.var(resid))
    var_seas_resid = float(np.var(seasonal + resid))
    seasonality_strength = max(0.0, 1.0 - var_resid / var_seas_resid) if var_seas_resid > 0 else 0.0

    # Trend strength
    var_trend_resid = float(np.var(trend + resid))
    trend_strength = max(0.0, 1.0 - var_resid / var_trend_resid) if var_trend_resid > 0 else 0.0

    return {
        "model": "stl_decompose",
        "trend": [round(float(v), 2) for v in trend],
        "seasonal": [round(float(v), 2) for v in seasonal],
        "residual": [round(float(v), 2) for v in resid],
        "diagnostics": {
            "n_obs": len(arr),
            "period": period,
            "seasonality_strength": round(seasonality_strength, 3),
            "trend_strength": round(trend_strength, 3),
            "residual_std": round(float(np.std(resid)), 2),
        },
    }


# =========================================================================
# 4.  Change-Point Detection (Prophet-style)
# =========================================================================

def change_point_detect(
    data: np.ndarray,
    n_cp: int = 3,
) -> dict[str, Any]:
    """Detect structural breaks / regime changes via CUSUM-based approach.

    Uses cumulative sum of normalised deviations to locate points where
    the mean level of the series shifts significantly.

    Parameters
    ----------
    data : np.ndarray
        1-D time series.
    n_cp : int
        Maximum number of change points to detect.

    Returns
    -------
    dict with change_point indices, confidence levels, segment means.
    """
    arr = _clean_series(data)
    if len(arr) < _MIN_CP:
        return {
            "model": "change_point_detect",
            "error": f"Insufficient data ({len(arr)} obs, need >= {_MIN_CP})",
            "change_points": [],
        }

    if _is_constant(arr):
        return {
            "model": "change_point_detect",
            "change_points": [],
            "segments": [],
            "diagnostics": {"constant_series": True},
        }

    n = len(arr)
    mu = float(np.mean(arr))
    sigma = float(np.std(arr))
    if sigma < 1e-12:
        sigma = abs(mu) * 0.01 + 1e-12

    normalised = (arr - mu) / sigma

    # ---- CUSUM (two-sided) ------------------------------------------------
    cusum_pos = np.cumsum(np.maximum(normalised, 0))
    cusum_neg = np.cumsum(np.maximum(-normalised, 0))
    cusum = cusum_pos - cusum_neg

    # Detect peaks in |CUSUM| as potential change points
    abs_cusum = np.abs(cusum)
    # Second derivative to find inflection points
    if n < 3:
        return {
            "model": "change_point_detect",
            "change_points": [],
            "segments": [],
        }

    # Use a sliding-window peak detection
    window = max(3, n // 10)
    candidates: list[tuple[int, float]] = []

    for i in range(window, n - window):
        local_max = abs_cusum[i] == max(abs_cusum[i - window: i + window + 1])
        # Significance: jump in CUSUM must exceed threshold
        threshold = sigma * np.sqrt(2 * np.log(n))  # asymptotic threshold
        if local_max and abs_cusum[i] > threshold:
            candidates.append((i, float(abs_cusum[i])))

    # Keep top n_cp by magnitude
    candidates.sort(key=lambda x: x[1], reverse=True)
    cp_indices = sorted({c[0] for c in candidates[:n_cp]})

    # Compute confidence level for each detected point
    max_cusum = max(abs_cusum) if len(abs_cusum) > 0 else 1.0
    change_points = []
    for idx in cp_indices:
        confidence = min(1.0, abs_cusum[idx] / max_cusum) if max_cusum > 0 else 0.0
        change_points.append({
            "index": int(idx),
            "confidence": round(confidence, 3),
            "value_before": round(float(np.mean(arr[max(0, idx - 3): idx])), 2),
            "value_after": round(float(np.mean(arr[idx: min(n, idx + 3)])), 2),
        })

    # Segment means (between consecutive change points)
    boundaries = [0] + cp_indices + [n]
    segments = []
    for i in range(len(boundaries) - 1):
        seg = arr[boundaries[i]: boundaries[i + 1]]
        segments.append({
            "start": int(boundaries[i]),
            "end": int(boundaries[i + 1]) - 1,
            "mean": round(float(np.mean(seg)), 2),
            "std": round(float(np.std(seg)), 2),
        })

    return {
        "model": "change_point_detect",
        "change_points": change_points,
        "segments": segments,
        "diagnostics": {
            "n_obs": n,
            "cusum_max": round(float(max_cusum), 2),
            "global_mean": round(mu, 2),
            "global_std": round(sigma, 2),
        },
    }


# =========================================================================
# 5.  Ensemble Forecast (ARIMA + Holt-Winters, walk-forward CV)
# =========================================================================

def ensemble_forecast(
    data: np.ndarray,
    horizon: int = 6,
    min_train_size: int | None = None,
) -> dict[str, Any]:
    """Combine ARIMA and Holt-Winters via inverse-AIC weighting.

    Includes walk-forward cross-validation to assess generalisation.

    Parameters
    ----------
    data : np.ndarray
        1-D time series.
    horizon : int
        Forecast horizon in periods.
    min_train_size : int | None
        Minimum training window for walk-forward CV.  Defaults to 60 %
        of the series length.

    Returns
    -------
    dict with ensemble predictions, per-model weights, CV metrics.
    """
    if not _HAS_STATS_MODELS:
        return _missing_sm_error("ensemble")

    arr = _clean_series(data)
    n = len(arr)
    if n < max(_MIN_ARIMA, _MIN_HW):
        return {
            "model": "ensemble",
            "error": f"Insufficient data ({n} obs, need >= {max(_MIN_ARIMA, _MIN_HW)})",
            "forecast": [],
        }

    if _is_constant(arr):
        dates = _safe_forecast_dates(n, horizon, 2024, 1)
        pts = _constant_forecast(arr, horizon, dates)
        return {
            "model": "ensemble",
            "weights": {"arima": 0.5, "holt_winters": 0.5},
            "forecast": pts,
            "cv_mape": 0.0,
        }

    # --- Fit both models on full data to get AIC weights --------------------
    aic_vals: dict[str, float] = {}
    arima_result = None
    hw_result = None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        # ARIMA
        try:
            d = _adstock_order(arr)
            m_a = _ARIMA(arr, order=(1, d, 1),
                         enforce_stationarity=False,
                         enforce_invertibility=False)
            arima_result = m_a.fit(disp=False)
            aic_vals["arima"] = float(arima_result.aic)
        except Exception:
            pass

        # Holt-Winters
        try:
            m_hw = _ExpSmoothing(
                arr, trend="add", seasonal="add",
                seasonal_periods=12,
                initialization_method="estimated",
            )
            hw_result = m_hw.fit(optimized=True)
            aic_vals["holt_winters"] = float(hw_result.aic)
        except Exception:
            pass

    if len(aic_vals) >= 2:
        weights = _aic_weight(aic_vals)
    elif aic_vals:
        # Single model succeeded -- give it all the weight
        weights = {k: 1.0 for k in aic_vals}
    else:
        weights = {}

    # --- Generate forecasts from each model --------------------------------
    combined_forecast = np.zeros(horizon)
    combined_lower = np.zeros(horizon)
    combined_upper = np.zeros(horizon)
    model_forecasts: dict[str, np.ndarray] = {}

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        if arima_result is not None:
            try:
                fc_a = arima_result.get_forecast(steps=horizon)
                fc_mean = np.asarray(fc_a.predicted_mean)
                ci_a = fc_a.conf_int(alpha=0.05)
                ci_lower = np.asarray(ci_a.iloc[:, 0]) if hasattr(ci_a, "iloc") else np.asarray(ci_a)[:, 0]
                ci_upper = np.asarray(ci_a.iloc[:, 1]) if hasattr(ci_a, "iloc") else np.asarray(ci_a)[:, 1]
                model_forecasts["arima"] = fc_mean
                w = weights.get("arima", 0.0)
                combined_forecast += w * fc_mean
                combined_lower += w * ci_lower
                combined_upper += w * ci_upper
            except Exception:
                pass

        if hw_result is not None:
            try:
                fc_raw = hw_result.forecast(steps=horizon)
                fc_h = np.asarray(fc_raw)
                fv_raw = hw_result.fittedvalues
                fv_arr = np.asarray(fv_raw)[:n]
                resid = arr - fv_arr
                resid_std = float(np.std(resid))
                model_forecasts["holt_winters"] = fc_h
                w = weights.get("holt_winters", 0.0)
                combined_forecast += w * fc_h
                for i in range(horizon):
                    se = resid_std * np.sqrt(1 + 0.1 * i)
                    combined_lower[i] += w * (fc_h[i] - 1.96 * se)
                    combined_upper[i] += w * (fc_h[i] + 1.96 * se)
            except Exception:
                pass

    # --- Walk-forward cross-validation --------------------------------------
    cv_mape = 0.0
    if min_train_size is None:
        min_train_size = max(max(_MIN_ARIMA, _MIN_HW), int(n * 0.6))

    if n > min_train_size + 2:
        test_start = min_train_size
        cv_errors: list[float] = []

        for t in range(test_start, n):
            train = arr[:t]
            actual = arr[t]
            preds: list[float] = []

            # Lightweight ARIMA prediction for CV
            try:
                d = _adstock_order(train)
                m_cv = _ARIMA(train, order=(1, d, 1),
                              enforce_stationarity=False,
                              enforce_invertibility=False)
                res_cv = m_cv.fit(disp=False)
                preds.append(float(res_cv.forecast(steps=1).iloc[0]))
            except Exception:
                pass

            # Lightweight HW prediction for CV
            try:
                hw_cv = _ExpSmoothing(
                    train, trend="add", seasonal="add",
                    seasonal_periods=min(12, len(train) - 1),
                    initialization_method="estimated",
                )
                res_hw = hw_cv.fit(optimized=True)
                preds.append(float(res_hw.forecast(steps=1).iloc[0]))
            except Exception:
                pass

            if preds and abs(actual) > 1e-10:
                mean_pred = float(np.mean(preds))
                cv_errors.append(abs(actual - mean_pred) / abs(actual))

        if cv_errors:
            cv_mape = float(np.mean(cv_errors)) * 100

    # --- Assemble result ---------------------------------------------------
    dates_fc = _safe_forecast_dates(n, horizon, 2024, 1)
    forecast_points = []
    for i in range(horizon):
        forecast_points.append({
            "date": dates_fc[i],
            "predicted": round(float(combined_forecast[i]), 2),
            "lower": round(float(combined_lower[i]), 2),
            "upper": round(float(combined_upper[i]), 2),
        })

    return {
        "model": "ensemble",
        "weights": {k: round(v, 3) for k, v in weights.items()},
        "forecast": forecast_points,
        "cv_mape": round(cv_mape, 2),
        "cv_train_size": min_train_size,
        "diagnostics": {
            "n_obs": n,
            "models_fitted": list(aic_vals.keys()),
            "aic": {k: round(v, 2) for k, v in aic_vals.items()},
        },
    }


# =========================================================================
# 6.  High-level API: forecast_trade_series
# =========================================================================

def forecast_trade_series(
    trade_data: list[dict],
    partner: str,
    hs_code: str,
    horizon: int = 6,
) -> dict[str, Any]:
    """Aggregate raw trade records into monthly totals and forecast.

    This is the primary entry-point that downstream API routes should call.
    It aggregates the input records by (year, month), fits the best model,
    and returns predictions compatible with the ``PredictionResult`` schema.

    Parameters
    ----------
    trade_data : list[dict]
        Raw trade records.  Each dict should contain at least
        ``trade_value_usd`` (numeric), ``year`` (int), ``month`` (int).
    partner : str
        Partner country code (for labelling).
    hs_code : str
        HS product code (for labelling).
    horizon : int
        Number of months to forecast.

    Returns
    -------
    dict with:
        model_name, mape, data (list of PredictionPoint-compatible dicts),
        diagnostics, meta.
    """
    if not trade_data:
        return _empty_result(partner, hs_code)

    # ---- Aggregate monthly ------------------------------------------------
    df = pd.DataFrame(trade_data)
    required_cols = {"trade_value_usd", "year", "month"}
    if not required_cols.issubset(df.columns):
        return _empty_result(partner, hs_code)

    monthly = (
        df.groupby(["year", "month"])["trade_value_usd"]
        .sum()
        .reset_index()
        .sort_values(["year", "month"])
        .reset_index(drop=True)
    )

    values = monthly["trade_value_usd"].values.astype(float)
    n = len(values)

    if n < 3:
        return _empty_result(partner, hs_code)

    # Date labels
    date_labels = [
        f"{int(r.year)}-{int(r.month):02d}" for _, r in monthly.iterrows()
    ]

    # ---- Decide best model ------------------------------------------------
    best_model_name = "holt_winters"  # default
    best_mape = np.inf
    best_result: dict[str, Any] | None = None

    # Try Holt-Winters first (strong default for trade data)
    hw = holt_winters(values, seasonal_periods=12)
    if "error" not in hw:
        fitted_arr = np.array(hw["fitted"][:n], dtype=float)
        if len(fitted_arr) == n and not _is_constant(values):
            mape = _compute_mape(values, fitted_arr)
            best_model_name = "holt_winters"
            best_mape = mape
            best_result = hw

    # Try ARIMA
    ar = auto_arima(values, seasonal=True)
    if "error" not in ar:
        fitted_arr = np.array(ar["fitted"][:n], dtype=float)
        if len(fitted_arr) == n and not _is_constant(values):
            mape = _compute_mape(values, fitted_arr)
            if mape < best_mape:
                best_model_name = "auto_arima"
                best_mape = mape
                best_result = ar

    # Try ensemble (uses both internally)
    ens = ensemble_forecast(values, horizon=horizon)
    if "error" not in ens and ens.get("cv_mape", 100) < best_mape:
        best_model_name = "ensemble"
        best_mape = ens["cv_mape"]
        best_result = ens

    # Fallback: simple exponential smoothing if nothing worked
    if best_result is None or "error" in (best_result or {}):
        best_result = _naive_forecast(values, horizon, date_labels)
        best_model_name = "naive"
        best_mape = 0.0

    # ---- Build PredictionPoint-compatible output --------------------------
    data_points = _build_prediction_points(
        values, date_labels, best_result, horizon,
    )

    return {
        "model_name": f"TS-{best_model_name}",
        "mape": round(best_mape, 2),
        "data": data_points,
        "diagnostics": {
            "partner": partner,
            "hs_code": hs_code,
            "n_obs": n,
            "selected_model": best_model_name,
            "horizon": horizon,
        },
        "meta": best_result.get("diagnostics", {}),
    }


# ---- helpers for forecast_trade_series -----------------------------------

def _empty_result(partner: str, hs_code: str) -> dict[str, Any]:
    return {
        "model_name": "TS-none",
        "mape": 0.0,
        "data": [],
        "diagnostics": {
            "partner": partner,
            "hs_code": hs_code,
            "error": "No usable data",
        },
        "meta": {},
    }


def _naive_forecast(
    values: np.ndarray, horizon: int, date_labels: list[str],
) -> dict[str, Any]:
    """Last-value-carry-forward as ultimate fallback."""
    last_val = float(values[-1])
    std_val = float(np.std(values)) if len(values) > 1 else abs(last_val) * 0.05
    last_year = int(date_labels[-1].split("-")[0])
    last_month = int(date_labels[-1].split("-")[1])
    dates = _safe_forecast_dates(len(values), horizon, last_year, last_month)
    pts = []
    for i, d in enumerate(dates):
        margin = std_val * (1 + 0.1 * i)
        pts.append({
            "date": d,
            "predicted": round(last_val, 2),
            "lower": round(last_val - margin, 2),
            "upper": round(last_val + margin, 2),
        })
    return {
        "model": "naive",
        "fitted": [round(float(v), 2) for v in values],
        "forecast": pts,
    }


def _build_prediction_points(
    values: np.ndarray,
    date_labels: list[str],
    model_result: dict[str, Any],
    horizon: int,
) -> list[dict[str, Any]]:
    """Merge historical actuals + fitted values + forecast into output list.

    Forecast dates are regenerated from the last observed date label so they
    are always contiguous with the historical data, regardless of what the
    individual model functions produced internally.
    """
    n = len(values)
    points: list[dict[str, Any]] = []

    # Historical portion
    fitted = model_result.get("fitted", [])
    for i in range(n):
        pt: dict[str, Any] = {
            "date": date_labels[i],
            "actual": round(float(values[i]), 2),
        }
        if i < len(fitted):
            pt["predicted"] = round(float(fitted[i]), 2)
        points.append(pt)

    # Forecast portion -- regenerate dates from the actual last observation
    forecast = model_result.get("forecast", [])
    if isinstance(forecast, list) and forecast and isinstance(forecast[0], dict):
        last_label = date_labels[-1]
        last_y, last_m = (int(x) for x in last_label.split("-"))
        correct_dates = _safe_forecast_dates(n, horizon, last_y, last_m)
        for i, fp in enumerate(forecast):
            d = correct_dates[i] if i < len(correct_dates) else fp.get("date", "")
            points.append({
                "date": d,
                "predicted": fp.get("predicted"),
                "lower": fp.get("lower"),
                "upper": fp.get("upper"),
            })

    return points
