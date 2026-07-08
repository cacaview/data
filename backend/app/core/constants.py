"""Centralized constants and magic-number replacements.

All threshold values, magic numbers, and hardcoded lists that were
previously scattered across route files live here. Importing from
this module keeps business logic free of unexplained literals.
"""

from __future__ import annotations

# === Country codes ===
ASEAN_COUNTRY_CODES: list[str] = [
    "BRN",
    "KHM",
    "IDN",
    "LAO",
    "MYS",
    "MMR",
    "PHL",
    "SGP",
    "THA",
    "VNM",
]
ASEAN_COUNTRY_NAMES: dict[str, str] = {
    "BRN": "文莱",
    "KHM": "柬埔寨",
    "IDN": "印度尼西亚",
    "LAO": "老挝",
    "MYS": "马来西亚",
    "MMR": "缅甸",
    "PHL": "菲律宾",
    "SGP": "新加坡",
    "THA": "泰国",
    "VNM": "越南",
}

REPORTER_CODE = "CHN"  # All trade data is reported from China

# Fallback coordinates (latitude, longitude) for countries whose DB row has
# lat/lon = NULL. Source: ASEAN country centroids (Wikipedia/Wikidata).
_COUNTRY_COORDS_FALLBACK: dict[str, tuple[float, float]] = {
    "CHN": (35.86, 104.19),
    "BRN": (4.53, 114.73),
    "KHM": (12.57, 104.99),
    "IDN": (-0.79, 113.92),
    "LAO": (19.86, 102.50),
    "MYS": (4.21, 101.98),
    "MMR": (21.91, 95.96),
    "PHL": (12.88, 121.77),
    "SGP": (1.35, 103.82),
    "THA": (15.87, 100.99),
    "VNM": (14.06, 108.28),
}

_CHINA_COORDS: tuple[float, float] = (35.86, 104.19)


def get_country_coords(code: str) -> tuple[float, float] | None:
    """Resolve a country's lat/lon. Prefers DB row values; falls back to
    the bundled centroid when the DB value is NULL/missing.
    Returns None only if `code` is not in the fallback table.
    """
    return _COUNTRY_COORDS_FALLBACK.get(code)


# === Ranking / clustering thresholds ===
RANKING_DEFAULT_LIMIT: int = 10
RANKING_MAX_LIMIT: int = 50

# Clustering tercile cutoffs (relative to max trade value)
CLUSTERING_HIGH_THRESHOLD: float = 0.66
CLUSTERING_MID_THRESHOLD: float = 0.33

# === Risk / volatility thresholds ===
VOLATILITY_HIGH_THRESHOLD: float = 50.0  # Coefficient of variation (%)
VOLATILITY_MEDIUM_THRESHOLD: float = 30.0

# YoY drop thresholds (percent)
YOY_DROP_HIGH_THRESHOLD: float = -20.0
YOY_DROP_MEDIUM_THRESHOLD: float = -10.0

# Month-over-month trade-value change thresholds (percent)
MOM_CHANGE_HIGH_THRESHOLD: float = 40.0  # Above this = high severity alert
MOM_CHANGE_MEDIUM_THRESHOLD: float = 15.0  # Above this = medium severity alert

# === Burst detection ===
# Rolling Z-score above this value flags a "burst" product
BURST_ZSCORE_THRESHOLD: float = 2.0
BURST_MIN_YOY_GROWTH: float = 0.5  # 50% YoY growth
BURST_MIN_HISTORY_MONTHS: int = 12

# === Tariff / RCEP ===
DEFAULT_RCEP_UTILIZATION_PCT: float = 80.0
HS_SECTION_NORMALIZATION_BASE: int = 20  # Used for diversity normalization
GDP_BILLION_USD_FALLBACK: float = 1.0  # Avoid div-by-zero for missing GDP

# === Date / time ===
DEFAULT_DATA_YEAR_FALLBACK: int = 2024

# === AI prediction ===
LSTM_LOOKBACK_MONTHS: int = 12
LSTM_PREDICTION_HORIZON_MONTHS: int = 6
LSTM_MODEL_NAME: str = "LSTM-Mock"

# === Pagination / API limits ===
TREND_MAX_RECORDS: int = 5000
TOP_RISK_ALERTS: int = 20
TOP_BURST_PRODUCTS: int = 20
