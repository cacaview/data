# Changelog / 变更日志

All notable changes to ACTAP are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added (in this refactor)

#### Security & runtime resilience (Phase 1)
- **API Key authentication** middleware (`X-API-Key`) for sensitive endpoints
- **Rate limiting** middleware (sliding window, IP-keyed, 120 req/min global, 10 req/min strict)
- **CORS whitelist** via `CORS_ORIGINS` env var (production-restricted)
- **Request ID tracking** with W3C `traceparent` support; response header `X-Request-ID`
- **Structured error responses** with `error_code` + sanitized messages in production
- **Health endpoints**: `/api/health` (liveness) + `/api/health/ready` (DB+cache checks)
- **`DATABASE_URL` env var** now actually respected; DB files moved to `DATA_DIR`
- **Container hardening**: non-root user (uid 1001), multi-stage builds, HEALTHCHECK
- **Production config validator** — fails fast on missing/insecure prod settings

#### Architecture & code quality (Phase 2)
- **4-layer backend**: `api/routes → services → repositories → models`
- **Constants module** (`app/core/constants.py`) — all magic numbers named
- **Long functions split**: `get_ranking` (110 → 60 lines), `get_country_compare`
- **Repository layer** (`app/repositories/trade_repo.py`) — all SQLAlchemy queries
- **Service layer** (`app/services/trade_service.py`) — pure business logic
- **ruff** lint + format (`pyproject.toml`)
- **Frontend typed end-to-end**: domain types in `src/types/`, zero `any` in `api.ts`
- **Generic `useApi` hook** for data fetching

#### Observability (Phase 3)
- **structlog** for structured JSON logging (production) / colored (TTY)
- **`request_id` auto-injected** into all log lines via `contextvars`
- **Prometheus metrics** at `/api/metrics`: `actap_http_requests_total`, `actap_http_request_duration_ms_*`, `actap_http_errors_total`, `actap_uptime_seconds`
- **W3C traceparent** parsing for distributed tracing

#### Testing (Phase 4)
- **pytest** infrastructure with in-memory SQLite fixtures
- **Unit tests** for constants, config, repositories, services, middleware, analytics, risk score, RCEP savings
- **Integration tests** for all 8 route modules + middleware chain + auth
- **GitHub Actions CI**: backend (lint + test on Python 3.10/3.11/3.12) + frontend (oxlint + tsc + build)
- Coverage gate: `--cov-fail-under=60`

#### Configuration (Phase 5)
- **`pydantic-settings`** for type-safe config
- **3 env files**: `.env.dev`, `.env.staging`, `.env.prod`
- **2 compose files**: `docker-compose.yml` (dev) + `docker-compose.prod.yml` (prod)
- **Production compose**: 4 workers, resource limits, `no-new-privileges`, JSON logging
- **Data dir isolation** — `.gitignore` excludes `data/`, persists via Docker volume

#### Deployment (Phase 6)
- **Multi-stage Dockerfiles** for both backend (Python) and frontend (Node→nginx)
- **systemd units** with security hardening (`NoNewPrivileges`, `ProtectSystem=strict`)
- **Release script** (`deploy/scripts/release.sh`) with auto-rollback on health-check failure
- **GHCR image push** via `release.yml` workflow on `v*.*.*` tags
- **OPERATIONS.md** runbook covering deploy, secrets, backups, monitoring, troubleshooting

#### Documentation (Phase 7)
- **README.md** rewritten (Chinese + English)
- **CONTRIBUTING.md** with PR checklist
- **CHANGELOG.md** (this file)
- **docs/OPERATIONS.md** — full SRE runbook
- **docs/API.md** — endpoint reference
- **docs/adr/0001-layered-architecture.md** — first ADR

### Changed
- `app/main.py` rewritten with explicit middleware chain + exception handlers
- `app/models/database.py` reads `DATABASE_URL` env var
- `app/data/cache.py` reads `DATA_DIR` env var
- `frontend/Dockerfile` now builds production assets (was running dev server)
- `frontend/src/services/api.ts` fully typed (was all `any`)

### Fixed
- CORS no longer accepts `*` with credentials in production
- Frontend Dockerfile no longer exposes source code in production
- DB files no longer generated inside source tree
- `CURRENT_YEAR=2025` magic value centralized as configurable constant

### Security
- 5 P0 vulnerabilities eliminated (no auth, open CORS, dev-only frontend, unused env vars, bare DB writes)
- 7 P1 risks addressed (no health check, root container, no rate limit, no structured logs, etc.)
- All 25 identified tech-debt items either fixed or documented as known limitations

---

## Previous versions

Prior to this refactor, the project shipped a single MVP build
(see git history: `8bfa4da feat: Integrate real data sources + P0 killer features`).
This refactor delivers the first production-grade release.
