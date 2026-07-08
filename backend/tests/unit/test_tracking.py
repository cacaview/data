"""Request tracking middleware unit tests."""

from app.middleware.tracking import _extract_trace_id


def test_extract_trace_id_valid():
    # W3C format: version-trace_id-span_id-flags
    tp = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
    assert _extract_trace_id(tp) == "0af7651916cd43dd8448eb211c80319c"


def test_extract_trace_id_invalid_format():
    assert _extract_trace_id("not-a-traceparent") is None
    assert _extract_trace_id("") is None
    assert _extract_trace_id("00-shortid-blah-01") is None


def test_extract_trace_id_none_safe():
    assert _extract_trace_id(None) is None  # type: ignore[arg-type]
