"""Constants module tests — ensure no value is silently changed."""
from app.core import constants as c


def test_asean_codes_count():
    assert len(c.ASEAN_COUNTRY_CODES) == 10


def test_reporter_is_china():
    assert c.REPORTER_CODE == "CHN"


def test_ranking_limits_are_sane():
    assert 1 <= c.RANKING_DEFAULT_LIMIT <= c.RANKING_MAX_LIMIT


def test_thresholds_ordered():
    # Volatility thresholds: medium < high
    assert c.VOLATILITY_MEDIUM_THRESHOLD < c.VOLATILITY_HIGH_THRESHOLD
    # YoY drop: medium > high (less negative)
    assert c.YOY_DROP_MEDIUM_THRESHOLD > c.YOY_DROP_HIGH_THRESHOLD
    # Clustering: mid < high
    assert c.CLUSTERING_MID_THRESHOLD < c.CLUSTERING_HIGH_THRESHOLD
    assert 0 < c.CLUSTERING_MID_THRESHOLD < 1
    assert 0 < c.CLUSTERING_HIGH_THRESHOLD < 1


def test_burst_zscore_positive():
    assert c.BURST_ZSCORE_THRESHOLD > 0


def test_gdp_fallback_is_safe():
    # The fallback must be non-zero to avoid div-by-zero
    assert c.GDP_BILLION_USD_FALLBACK > 0
