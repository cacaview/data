"""Correlation & Cointegration Analysis Engine for Trade Data.

Inspired by quantitative finance pair trading and regime detection:
- Cross-country trade flow correlation matrices
- Lead-lag relationship detection between macro indicators and trade
- Cointegration testing for long-run equilibrium relationships
- Structural break detection
- Clustering analysis based on trade patterns
"""

import logging
from typing import List, Optional

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Minimum thresholds
# ---------------------------------------------------------------------------
_MIN_SERIES_LEN = 3          # shortest series for correlation / cointegration
_MIN_CORRELATION_OBS = 12    # minimum observations for reliable correlation
_MIN_COINTEGRATION_OBS = 20  # minimum observations for Engle-Granger


# ===================================================================
# 1. Correlation Matrix
# ===================================================================

def compute_correlation_matrix(
    trade_data: list,
    entities: str = "country",
    method: str = "pearson",
) -> dict:
    """Compute pairwise correlation matrix across countries or products.

    Pivots *trade_data* into a time series (rows = year-month) per entity,
    then calculates the correlation matrix.

    Args:
        trade_data: List of dicts each containing at least
            ``year``, ``month``, ``trade_value_usd``, and either
            ``partner`` (for country-level) or ``hs_code`` (for product-level).
        entities: ``"country"`` to correlate trade flows by partner country,
            ``"product"`` to correlate by HS code.
        method: ``"pearson"`` or ``"spearman"``.

    Returns:
        Dict with keys ``countries`` (entity labels), ``matrix`` (list of
        lists), ``method``, and ``n_observations``.
    """
    if not trade_data:
        return {"countries": [], "matrix": [], "method": method,
                "n_observations": 0}

    df = pd.DataFrame(trade_data)
    if df.empty:
        return {"countries": [], "matrix": [], "method": method,
                "n_observations": 0}

    # Determine entity key
    entity_col = "partner" if entities == "country" else "hs_code"
    if entity_col not in df.columns:
        logger.warning("Column '%s' not found in trade_data; falling back.", entity_col)
        return {"countries": [], "matrix": [], "method": method,
                "n_observations": 0}

    # Aggregate to monthly totals per entity
    df["date_key"] = df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
    pivot = (
        df.pivot_table(
            index="date_key",
            columns=entity_col,
            values="trade_value_usd",
            aggfunc="sum",
            fill_value=0,
        )
        .sort_index()
    )

    if pivot.shape[1] < 2:
        return {
            "countries": list(pivot.columns),
            "matrix": [[1.0]],
            "method": method,
            "n_observations": len(pivot),
        }

    # Drop entities with no variation (constant series -> NaN correlation)
    pivot = pivot.loc[:, pivot.std() > 0]
    if pivot.shape[1] < 2:
        return {"countries": list(pivot.columns), "matrix": [],
                "method": method, "n_observations": len(pivot)}

    corr_method = method if method in ("pearson", "spearman") else "pearson"
    corr_df = pivot.corr(method=corr_method)
    labels = list(corr_df.columns)
    matrix = [[round(float(corr_df.iloc[i, j]), 4) for j in range(len(labels))]
              for i in range(len(labels))]

    return {
        "countries": labels,
        "matrix": matrix,
        "method": corr_method,
        "n_observations": int(len(pivot)),
    }


# ===================================================================
# 2. Lead-Lag Detection
# ===================================================================

def detect_lead_lag(
    trade_data: list,
    macro_data: list,
    max_lag: int = 6,
) -> dict:
    """Cross-correlation analysis between macro indicators and trade flows.

    Determines which series leads the other by computing cross-correlations
    at lags from ``-max_lag`` to ``+max_lag``.

    Args:
        trade_data: Trade records with ``year``, ``month``,
            ``trade_value_usd`` (and optionally ``partner``).
        macro_data: Macro indicator records with ``year``, ``month``,
            ``value`` (and optionally ``indicator`` name).
        max_lag: Maximum lag (in months) in either direction.

    Returns:
        Dict with ``cross_correlation`` (list of {lag, correlation}),
        ``optimal_lag`` (int), ``significance`` (bool), and
        ``interpretation`` (str).
    """
    if not trade_data or not macro_data:
        return {"cross_correlation": [], "optimal_lag": 0,
                "significance": False, "interpretation": "Insufficient data"}

    trade_df = pd.DataFrame(trade_data)
    macro_df = pd.DataFrame(macro_data)

    if trade_df.empty or macro_df.empty:
        return {"cross_correlation": [], "optimal_lag": 0,
                "significance": False, "interpretation": "Empty datasets"}

    # Build monthly trade totals
    trade_df["_sort_key"] = trade_df["year"].astype(int) * 100 + trade_df["month"].astype(int)
    trade_monthly = (
        trade_df.groupby("_sort_key")["trade_value_usd"]
        .sum()
        .sort_index()
    )

    # Build monthly macro totals
    macro_df["_sort_key"] = macro_df["year"].astype(int) * 100 + macro_df["month"].astype(int)
    macro_monthly = (
        macro_df.groupby("_sort_key")["value"]
        .mean()  # average if multiple indicators per month
        .sort_index()
    )

    # Merge on common dates
    combined = pd.DataFrame({"trade": trade_monthly, "macro": macro_monthly}).dropna()
    if len(combined) < _MIN_CORRELATION_OBS:
        return {"cross_correlation": [], "optimal_lag": 0,
                "significance": False,
                "interpretation": f"Need at least {_MIN_CORRELATION_OBS} "
                                  f"common observations (got {len(combined)})"}

    trade_arr = combined["trade"].values
    macro_arr = combined["macro"].values

    # Normalise for cross-correlation
    trade_arr = (trade_arr - trade_arr.mean()) / (trade_arr.std() + 1e-12)
    macro_arr = (macro_arr - macro_arr.mean()) / (macro_arr.std() + 1e-12)

    n = len(trade_arr)
    cc_results = []

    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            corr = float(np.corrcoef(trade_arr[lag:], macro_arr[:n - lag])[0, 1]) \
                if n - lag >= _MIN_SERIES_LEN else 0.0
        else:
            corr = float(np.corrcoef(trade_arr[:n + lag], macro_arr[-lag:])[0, 1]) \
                if n + lag >= _MIN_SERIES_LEN else 0.0

        cc_results.append({"lag": lag, "correlation": round(corr, 4)})

    # Optimal lag
    best = max(cc_results, key=lambda x: abs(x["correlation"]))
    optimal_lag = best["lag"]
    best_corr = best["correlation"]

    # Significance via t-test
    df_test = max(n - 2, 1)
    t_stat = best_corr * np.sqrt(df_test / (1 - best_corr ** 2 + 1e-12))
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df_test))
    significant = bool(p_value < 0.05)

    if optimal_lag > 0:
        interpretation = (
            f"Macro indicator leads trade by {optimal_lag} months "
            f"(r={best_corr:.3f}, p={p_value:.4f})"
        )
    elif optimal_lag < 0:
        interpretation = (
            f"Trade leads macro indicator by {abs(optimal_lag)} months "
            f"(r={best_corr:.3f}, p={p_value:.4f})"
        )
    else:
        interpretation = (
            f"Contemporaneous relationship "
            f"(r={best_corr:.3f}, p={p_value:.4f})"
        )

    return {
        "cross_correlation": cc_results,
        "optimal_lag": int(optimal_lag),
        "best_correlation": round(best_corr, 4),
        "significance": significant,
        "p_value": round(float(p_value), 6),
        "interpretation": interpretation,
    }


# ===================================================================
# 3. Cointegration Test (Engle-Granger)
# ===================================================================

def cointegration_test(
    series_a: np.ndarray,
    series_b: np.ndarray,
) -> dict:
    """Engle-Granger two-step cointegration test.

    Step 1 -- regress series_a on series_b and collect residuals.
    Step 2 -- run ADF on the residuals (here approximated via the
    augmented Dickey-Fuller critical values from MacKinnon 1996).

    Args:
        series_a: First time series (1-D array).
        series_b: Second time series (1-D array).

    Returns:
        Dict with ``cointegrated`` (bool), ``test_statistic`` (float),
        ``p_value`` (float), and ``critical_values`` (dict).
    """
    a = np.asarray(series_a, dtype=float).flatten()
    b = np.asarray(series_b, dtype=float).flatten()

    # Align lengths
    n = min(len(a), len(b))
    if n < _MIN_COINTEGRATION_OBS:
        return {
            "cointegrated": False,
            "test_statistic": 0.0,
            "p_value": 1.0,
            "critical_values": {},
            "message": f"Need at least {_MIN_COINTEGRATION_OBS} observations "
                       f"(got {n})",
        }

    a, b = a[:n], b[:n]

    # Step 1: OLS regression  a = alpha + beta * b + epsilon
    b_with_const = np.column_stack([np.ones(n), b])
    try:
        coeffs, _, _, _ = np.linalg.lstsq(b_with_const, a, rcond=None)
    except np.linalg.LinAlgError:
        return {
            "cointegrated": False, "test_statistic": 0.0, "p_value": 1.0,
            "critical_values": {}, "message": "OLS regression failed",
        }

    residuals = a - b_with_const @ coeffs

    # Step 2: ADF on residuals (augmented with 1 lag for simplicity)
    y = residuals[1:]
    y_lag = residuals[:-1]
    dy = y - y_lag
    X = np.column_stack([np.ones(len(y)), y_lag])
    try:
        adf_coeffs, _, _, _ = np.linalg.lstsq(X, dy, rcond=None)
    except np.linalg.LinAlgError:
        return {
            "cointegrated": False, "test_statistic": 0.0, "p_value": 1.0,
            "critical_values": {}, "message": "ADF regression failed",
        }

    residuals_adf = dy - X @ adf_coeffs
    se = np.sqrt(np.sum(residuals_adf ** 2) / max(len(dy) - X.shape[1], 1))
    se_slope = se / np.sqrt(np.sum((y_lag - y_lag.mean()) ** 2) + 1e-12)
    test_stat = adf_coeffs[1] / se_slope if se_slope > 0 else 0.0

    # MacKinnon approximate critical values (constant-only, no trend)
    # Source: MacKinnon (1996), Table 1
    # n=20..100, we interpolate
    n_eff = n
    critical_n = np.array([20, 30, 40, 50, 60, 80, 100, 250, 500])
    cv_1pct = np.array([-3.75, -3.58, -3.50, -3.45, -3.41, -3.37, -3.34, -3.30, -3.28])
    cv_5pct = np.array([-3.00, -2.89, -2.83, -2.80, -2.77, -2.75, -2.73, -2.70, -2.69])
    cv_10pct = np.array([-2.63, -2.56, -2.52, -2.50, -2.48, -2.46, -2.45, -2.43, -2.42])

    if n_eff < critical_n[0]:
        n_eff = critical_n[0]
    elif n_eff > critical_n[-1]:
        n_eff = critical_n[-1]

    cv_1 = float(np.interp(n_eff, critical_n, cv_1pct))
    cv_5 = float(np.interp(n_eff, critical_n, cv_5pct))
    cv_10 = float(np.interp(n_eff, critical_n, cv_10pct))

    critical_values = {
        "1%": round(cv_1, 3),
        "5%": round(cv_5, 3),
        "10%": round(cv_10, 3),
    }

    # Approximate p-value (very rough, linear interpolation)
    # p < 0.01 if test_stat < cv_1, p < 0.05 if < cv_5, etc.
    if test_stat <= cv_1:
        p_approx = 0.01 * max(test_stat / cv_1, 0.001)  # <1%
    elif test_stat <= cv_5:
        p_approx = 0.01 + 0.04 * (test_stat - cv_1) / (cv_5 - cv_1 + 1e-12)
    elif test_stat <= cv_10:
        p_approx = 0.05 + 0.05 * (test_stat - cv_5) / (cv_10 - cv_5 + 1e-12)
    else:
        p_approx = min(0.10 + 0.90 * (abs(test_stat) - abs(cv_10)) /
                       (abs(cv_10) + 1e-12), 1.0)

    p_approx = float(np.clip(p_approx, 0.001, 1.0))
    cointegrated = bool(test_stat < cv_5)  # reject unit root at 5%

    return {
        "cointegrated": cointegrated,
        "test_statistic": round(float(test_stat), 4),
        "p_value": round(p_approx, 4),
        "critical_values": critical_values,
    }


# ===================================================================
# 4. Regime / Structural Break Detection
# ===================================================================

def detect_regime_changes(
    data: np.ndarray,
    dates: Optional[list] = None,
    min_segment: int = 12,
    threshold: float = 2.0,
) -> dict:
    """Detect structural breaks in a time series using CUSUM analysis.

    Computes cumulative sum of normalised deviations from the global mean,
    then identifies break-points where the CUSUM exceeds a threshold
    relative to the standard deviation.

    Args:
        data: 1-D numeric time series (e.g. monthly trade totals).
        dates: Optional list of date strings aligned with *data*.
        min_segment: Minimum observations between consecutive breaks.
        threshold: CUSUM threshold (in std-dev units) for flagging a break.

    Returns:
        Dict with ``breakpoints`` (list of dicts), ``regimes`` (list of
        dicts with start/end indices and mean), and ``n_regimes`` (int).
    """
    arr = np.asarray(data, dtype=float).flatten()
    n = len(arr)

    if n < max(min_segment * 2, 6):
        return {"breakpoints": [], "regimes": [], "n_regimes": 1,
                "message": "Insufficient data for break detection"}

    global_mean = arr.mean()
    std = arr.std()
    if std == 0:
        return {"breakpoints": [], "regimes": [{"start": 0, "end": n - 1,
                "mean": float(global_mean)}], "n_regimes": 1}

    normalised = (arr - global_mean) / std
    cusum = np.cumsum(normalised)

    # Find local extrema of CUSUM as candidate breakpoints
    candidates = []
    for i in range(1, n - 1):
        if abs(cusum[i]) > abs(cusum[i - 1]) and abs(cusum[i]) > abs(cusum[i + 1]):
            candidates.append((i, abs(cusum[i])))
        elif abs(cusum[i]) > threshold:
            candidates.append((i, abs(cusum[i])))

    # Filter by significance and minimum segment length
    candidates.sort(key=lambda x: x[1], reverse=True)
    break_indices: list = []
    for idx, _score in candidates:
        if all(abs(idx - b) >= min_segment for b in break_indices):
            break_indices.append(idx)

    break_indices.sort()

    # Build regimes
    boundaries = [0] + break_indices + [n]
    regimes = []
    breakpoints = []
    for i in range(len(boundaries) - 1):
        start, end = boundaries[i], boundaries[i + 1] - 1
        if i == len(boundaries) - 2:
            end = boundaries[i + 1]  # include last element
        seg_mean = float(arr[start:end + 1].mean())
        regimes.append({
            "start": int(start),
            "end": int(end),
            "mean": round(seg_mean, 2),
            "length": int(end - start + 1),
        })

        if dates and 0 <= start < len(dates) and i < len(break_indices):
            breakpoints.append({
                "index": int(break_indices[i]),
                "date": dates[break_indices[i]],
                "pre_mean": round(float(arr[boundaries[i]:break_indices[i]].mean()), 2),
                "post_mean": round(float(arr[break_indices[i]:boundaries[i + 1]].mean()), 2),
            })
        elif i < len(break_indices):
            breakpoints.append({
                "index": int(break_indices[i]),
                "date": None,
                "pre_mean": round(float(arr[boundaries[i]:break_indices[i]].mean()), 2),
                "post_mean": round(float(arr[break_indices[i]:boundaries[i + 1]].mean()), 2),
            })

    return {
        "breakpoints": breakpoints,
        "regimes": regimes,
        "n_regimes": len(regimes),
    }


# ===================================================================
# 5. Entity Clustering (K-Means + PCA)
# ===================================================================

def cluster_entities(
    trade_data: list,
    n_clusters: int = 3,
    entities: str = "country",
) -> dict:
    """Cluster countries or products by trade patterns using K-Means + PCA.

    Builds a feature matrix where each row is an entity and columns capture
    monthly trade-value profiles (normalised by total). PCA reduces
    dimensionality before clustering.

    Args:
        trade_data: List of trade records.
        n_clusters: Number of clusters (auto-capped to #entities - 1).
        entities: ``"country"`` or ``"product"``.

    Returns:
        Dict with ``clusters`` (list of dicts), ``explained_variance``
        (PCA ratios), and ``method`` info.
    """
    if not trade_data:
        return {"clusters": [], "explained_variance": [], "method": "kmeans"}

    df = pd.DataFrame(trade_data)
    entity_col = "partner" if entities == "country" else "hs_code"
    if entity_col not in df.columns:
        return {"clusters": [], "explained_variance": [], "method": "kmeans"}

    df["date_key"] = df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)

    # Build entity x time matrix
    pivot = df.pivot_table(
        index=entity_col, columns="date_key",
        values="trade_value_usd", aggfunc="sum", fill_value=0,
    ).sort_index(axis=1)

    if pivot.shape[0] < 2 or pivot.shape[1] < _MIN_SERIES_LEN:
        return {"clusters": [], "explained_variance": [], "method": "kmeans",
                "message": "Insufficient entities or time points"}

    # Normalise each entity to proportion of its total (profile shape)
    row_totals = pivot.sum(axis=1).replace(0, 1)
    normed = pivot.div(row_totals, axis=0)

    n_entities = normed.shape[0]
    actual_k = min(n_clusters, n_entities - 1)
    if actual_k < 1:
        actual_k = 1

    # PCA dimensionality reduction
    n_components = min(actual_k, normed.shape[1], normed.shape[0])
    pca = PCA(n_components=n_components)
    reduced = pca.fit_transform(normed.values)
    explained = [round(float(v), 4) for v in pca.explained_variance_ratio_]

    # K-Means
    kmeans = KMeans(n_clusters=actual_k, n_init=10, random_state=42)
    labels = kmeans.fit_predict(reduced)

    entity_names = list(normed.index)
    clusters_map = {}
    for name, label in zip(entity_names, labels):
        clusters_map.setdefault(int(label), []).append(name)

    # Build output
    clusters = []
    cluster_labels_map = {
        0: "Cluster A",
        1: "Cluster B",
        2: "Cluster C",
        3: "Cluster D",
        4: "Cluster E",
    }
    for cid in sorted(clusters_map):
        members = clusters_map[cid]
        centroid = kmeans.cluster_centers_[cid].tolist()
        clusters.append({
            "id": cid,
            "members": members,
            "centroid": [round(v, 4) for v in centroid],
            "label": cluster_labels_map.get(cid, f"Cluster {cid}"),
            "size": len(members),
        })

    return {
        "clusters": clusters,
        "explained_variance": explained,
        "method": "kmeans+pca",
        "n_entities": n_entities,
        "n_features": int(normed.shape[1]),
    }


# ===================================================================
# 6. Full Analysis
# ===================================================================

def full_analysis(
    trade_data: list,
    macro_data: Optional[list] = None,
) -> dict:
    """Run the complete correlation and cointegration analysis suite.

    Combines correlation matrix, lead-lag detection (if macro data is
    available), cointegration tests for the top-correlated pairs, regime
    detection, and entity clustering into a single comprehensive result.

    Args:
        trade_data: List of trade records.
        macro_data: Optional macro indicator records.

    Returns:
        Dict with sub-results keyed by analysis name, plus a ``summary``
        section with key take-aways.
    """
    result: dict = {"analyses": {}, "summary": {}}

    # --- Correlation matrix (country) ---
    corr_country = compute_correlation_matrix(trade_data, entities="country")
    result["analyses"]["correlation_country"] = corr_country

    # --- Correlation matrix (product) ---
    corr_product = compute_correlation_matrix(trade_data, entities="product")
    result["analyses"]["correlation_product"] = corr_product

    # --- Lead-lag ---
    if macro_data:
        lead_lag = detect_lead_lag(trade_data, macro_data)
        result["analyses"]["lead_lag"] = lead_lag
    else:
        result["analyses"]["lead_lag"] = {
            "message": "No macro data provided; skipping lead-lag analysis",
        }

    # --- Cointegration for top correlated country pairs ---
    cointegration_results = []
    if corr_country.get("matrix") and len(corr_country["countries"]) >= 2:
        # Build monthly time series per country for cointegration
        df = pd.DataFrame(trade_data)
        if "partner" in df.columns:
            df["date_key"] = (df["year"].astype(str) + "-"
                              + df["month"].astype(str).str.zfill(2))
            pivot = df.pivot_table(
                index="date_key", columns="partner",
                values="trade_value_usd", aggfunc="sum", fill_value=0,
            ).sort_index()

            countries = corr_country["countries"]
            matrix = corr_country["matrix"]
            tested = set()
            for i in range(len(countries)):
                for j in range(i + 1, len(countries)):
                    ci, cj = countries[i], countries[j]
                    if ci not in pivot.columns or cj in pivot.columns is False:
                        continue
                    # Skip low-correlation pairs (|r| < 0.3)
                    if abs(matrix[i][j]) < 0.3:
                        continue
                    pair_key = (ci, cj)
                    if pair_key in tested:
                        continue
                    tested.add(pair_key)

                    s_a = pivot[ci].values.astype(float)
                    s_b = pivot[cj].values.astype(float)
                    ct = cointegration_test(s_a, s_b)
                    ct["pair"] = [ci, cj]
                    ct["correlation"] = matrix[i][j]
                    cointegration_results.append(ct)

            # Sort by correlation strength
            cointegration_results.sort(key=lambda x: abs(x["correlation"]),
                                       reverse=True)
            cointegration_results = cointegration_results[:20]  # cap

    result["analyses"]["cointegration"] = cointegration_results

    # --- Regime detection on total trade ---
    df = pd.DataFrame(trade_data)
    if not df.empty:
        df["date_key"] = (df["year"].astype(str) + "-"
                          + df["month"].astype(str).str.zfill(2))
        monthly_total = (
            df.groupby("date_key")["trade_value_usd"]
            .sum()
            .sort_index()
        )
        dates_list = list(monthly_total.index)
        regimes = detect_regime_changes(
            monthly_total.values, dates=dates_list,
        )
        result["analyses"]["regime_detection"] = regimes

    # --- Clustering ---
    cluster_country = cluster_entities(trade_data, n_clusters=3,
                                       entities="country")
    cluster_product = cluster_entities(trade_data, n_clusters=3,
                                       entities="product")
    result["analyses"]["clustering_country"] = cluster_country
    result["analyses"]["clustering_product"] = cluster_product

    # --- Summary ---
    n_countries = len(corr_country.get("countries", []))
    n_products = len(corr_product.get("countries", []))
    n_coint = len(cointegration_results)
    n_cointegrated = sum(1 for c in cointegration_results if c["cointegrated"])
    n_regimes = result["analyses"].get("regime_detection", {}).get("n_regimes", 0)
    n_clust_country = len(cluster_country.get("clusters", []))
    n_clust_product = len(cluster_product.get("clusters", []))

    result["summary"] = {
        "n_entities_country": n_countries,
        "n_entities_product": n_products,
        "correlation_method": corr_country.get("method", "pearson"),
        "cointegration_pairs_tested": n_coint,
        "cointegration_pairs_found": n_cointegrated,
        "regime_count": n_regimes,
        "clusters_country": n_clust_country,
        "clusters_product": n_clust_product,
    }

    return result
