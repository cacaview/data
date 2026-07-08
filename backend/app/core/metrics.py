"""In-process Prometheus-style metrics.

A minimal implementation that:
- Records request count by path + method + status
- Records request duration by path + method
- Exposes /api/metrics in Prometheus text format

For multi-worker deployments, replace with prometheus_client or
opentelemetry-exporter-prometheus.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Dict, Tuple

import structlog

logger = structlog.get_logger(__name__)


class MetricsRegistry:
    """Thread-safe in-memory metrics registry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._request_count: Dict[Tuple[str, str, int], int] = defaultdict(int)
        self._request_duration_sum_ms: Dict[Tuple[str, str], float] = defaultdict(float)
        self._request_duration_count: Dict[Tuple[str, str], int] = defaultdict(int)
        self._errors_by_code: Dict[str, int] = defaultdict(int)
        self._start_time = time.time()

    def record_request(
        self, method: str, path: str, status_code: int, duration_ms: float
    ) -> None:
        with self._lock:
            self._request_count[(path, method, status_code)] += 1
            self._request_duration_sum_ms[(path, method)] += duration_ms
            self._request_duration_count[(path, method)] += 1
            if status_code >= 400:
                self._errors_by_code[str(status_code)] += 1

    def render(self) -> str:
        """Render metrics in Prometheus text format."""
        with self._lock:
            lines: list[str] = []
            uptime_s = time.time() - self._start_time

            lines.append("# HELP actap_uptime_seconds Process uptime in seconds")
            lines.append("# TYPE actap_uptime_seconds gauge")
            lines.append(f"actap_uptime_seconds {uptime_s:.2f}")

            lines.append("# HELP actap_http_requests_total Total HTTP requests")
            lines.append("# TYPE actap_http_requests_total counter")
            for (path, method, status), count in sorted(self._request_count.items()):
                lines.append(
                    f'actap_http_requests_total{{path="{path}",method="{method}",'
                    f'status="{status}"}} {count}'
                )

            lines.append("# HELP actap_http_request_duration_ms_sum Sum of request durations")
            lines.append("# TYPE actap_http_request_duration_ms_sum counter")
            for (path, method), total_ms in sorted(self._request_duration_sum_ms.items()):
                lines.append(
                    f'actap_http_request_duration_ms_sum{{path="{path}",'
                    f'method="{method}"}} {total_ms:.2f}'
                )

            lines.append("# HELP actap_http_request_duration_ms_count Request count for duration")
            lines.append("# TYPE actap_http_request_duration_ms_count counter")
            for (path, method), count in sorted(self._request_duration_count.items()):
                lines.append(
                    f'actap_http_request_duration_ms_count{{path="{path}",'
                    f'method="{method}"}} {count}'
                )

            lines.append("# HELP actap_http_errors_total Total 4xx/5xx responses")
            lines.append("# TYPE actap_http_errors_total counter")
            for status, count in sorted(self._errors_by_code.items()):
                lines.append(
                    f'actap_http_errors_total{{status="{status}"}} {count}'
                )

            return "\n".join(lines) + "\n"


# Singleton
registry = MetricsRegistry()
