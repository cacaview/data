# ACTAP — 东盟跨境贸易 AI 智能分析平台

> **ASEAN Cross-Border Trade AI Analytics Platform** | 中国—东盟双边贸易数据 + AI 智能分析

[English](#english) · [中文](#中文)

---

## 中文

### 项目简介

ACTAP 是一个面向中国—东盟跨境贸易的 AI 智能分析平台，整合 9 个权威数据源（UN Comtrade、World Bank、IMF、广西公共数据平台、北部湾港、RCEP 关税数据库等），提供：

- 📊 **总览仪表盘** — 关键指标、贸易地图、Top 5 增长产品
- 🔍 **贸易分析** — 月度趋势、ASEAN 雷达对比、Top-N 排名、桑基图
- 🤖 **AI 预测** — 6 个月 LSTM 预测、产品聚类、风险预警
- 🧮 **关税计算** — RCEP/ACFTA/MFN 三档对比，节省金额
- 💬 **AI 助手** — 基于贸易数据的对话式问答
- 🛡️ **风险与爆品** — 多因子风险评分、突发产品检测、价值链位置

### 技术栈 / Tech Stack

**Backend** · FastAPI 0.115 · SQLAlchemy 2.0 · Pydantic 2.9 · structlog · Prometheus
**Frontend** · React 19 · TypeScript 5.5 · Ant Design 6 · ECharts 6 · Vite 8
**Storage** · SQLite (5 tables) · File-based API cache (TTL 24h)
**Observability** · structlog (JSON) · `/api/metrics` (Prometheus) · W3C traceparent
**Quality** · ruff · pytest · GitHub Actions (lint → test → build → push)
**Deployment** · Docker multi-stage · docker-compose · systemd · GitHub Container Registry

### 架构 / Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Browser  ─→  Nginx (FE) :3000                             │
│                  │  /api/* proxy                            │
│                  ▼                                          │
│  FastAPI Backend :8001 (4 workers)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Middleware chain (outer → inner)                     │  │
│  │   CORS → RequestTracking → Prometheus → RateLimit →  │  │
│  │   APIKeyAuth → App                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│         │              │              │                     │
│         ▼              ▼              ▼                     │
│  services/      repositories/    middleware/                │
│  (business      (data access)   (auth, rate,               │
│   logic)                         errors, log)              │
│         │              │                                    │
│         └──────┬───────┘                                    │
│                ▼                                            │
│         SQLAlchemy ORM                                      │
│         │              │                                    │
│         ▼              ▼                                    │
│  SQLite (actap.db)   API cache (api_cache.db)               │
└────────────────────────────────────────────────────────────┘
```

### 本地启动 / Quickstart

#### 方式 A：Docker（推荐）

```bash
git clone <repo-url> actap && cd actap
cp .env.dev .env
docker compose up -d
# Frontend: http://localhost:3000
# Backend:  http://localhost:8001/docs
```

#### 方式 B：本地 Python + Node

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8001

# Frontend (separate terminal)
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### 部署 / Deployment

| 环境 | 命令 |
|------|------|
| Dev | `docker compose up -d` |
| Staging | `docker compose -f docker-compose.prod.yml --env-file .env.staging up -d` |
| Production | `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d` |
| Bare-metal (systemd) | `sudo cp deploy/systemd/*.service /etc/systemd/system && sudo systemctl enable --now actap-backend actap-frontend` |
| Release (CI) | Tag a commit `git tag v1.2.3 && git push --tags` → GitHub Actions builds and pushes to GHCR |
| Manual release | `./deploy/scripts/release.sh v1.2.3` (auto-rollback on health-check fail) |

详见 [`docs/OPERATIONS.md`](docs/OPERATIONS.md)。

### 开发 / Development

```bash
# Lint
cd backend && ruff check . && ruff format --check .
cd frontend && npm run lint

# Tests
cd backend && pytest -v --cov=app
# Coverage report → htmlcov/index.html

# OpenAPI 文档 (dev only)
open http://localhost:8001/docs
```

### 环境变量 / Environment

所有可调参数见 [`backend/.env.example`](backend/.env.example)。关键项：

- `ENVIRONMENT` — `development` / `staging` / `production`
- `API_KEY` — 生产必填；`X-API-Key` header 鉴权
- `CORS_ORIGINS` — 生产必须白名单（不能 `*`）
- `DATABASE_URL` — 默认 `sqlite:///./data/actap.db`
- `OPENAI_API_KEY` — AI 助手所需

### 贡献 / Contributing

欢迎贡献！请阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md) 与 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)。

### 许可证 / License

MIT

---

## English

### Overview

ACTAP is an AI-powered analytics platform for China–ASEAN cross-border trade. It integrates 9 authoritative data sources (UN Comtrade, World Bank, IMF, Guangxi Open Data, Beibu Gulf Port, RCEP Tariff DB) and provides:

- 📊 **Overview dashboard** — KPIs, trade map, top-5 growth products
- 🔍 **Trade analysis** — monthly trends, ASEAN radar, Top-N ranking, Sankey diagrams
- 🤖 **AI prediction** — 6-month LSTM forecast, product clustering, risk alerts
- 🧮 **Tariff calculator** — RCEP / ACFTA / MFN comparison with USD savings
- 💬 **AI assistant** — conversational Q&A over trade data
- 🛡️ **Risk & burst detection** — multi-factor risk scoring, anomaly detection, value-chain position

### Highlights

- **Type-safe end-to-end** — Pydantic + TypeScript strict types
- **Production-grade** — non-root Docker, structured logging, metrics, health checks, rate limiting, API key auth
- **Layered architecture** — `api → services → repositories → models`
- **Observable** — every request has a `request_id`, all logs are JSON in prod
- **Secure by default** — CORS whitelist enforced in prod, secrets from env, no hardcoded keys

### Project structure

```
actap/
├── backend/                  # FastAPI service
│   ├── app/
│   │   ├── api/routes/      # HTTP endpoints (thin layer)
│   │   ├── services/        # Business logic
│   │   ├── repositories/    # Data access
│   │   ├── core/            # Config, constants, logging, metrics
│   │   ├── middleware/      # Auth, rate limit, errors, tracking, metrics
│   │   ├── models/          # SQLAlchemy ORM + Pydantic schemas
│   │   ├── data/            # External API clients + cache + analytics
│   │   ├── ai/              # AI chat service
│   │   └── main.py          # App factory
│   ├── tests/               # pytest (unit + integration)
│   ├── pyproject.toml       # ruff + pytest config
│   └── Dockerfile
├── frontend/                 # React SPA
│   ├── src/
│   │   ├── types/           # TypeScript domain types
│   │   ├── services/        # Typed API client
│   │   ├── hooks/           # useApi, etc.
│   │   ├── utils/           # format, api helpers
│   │   ├── layouts/         # AppLayout
│   │   └── pages/           # 7 feature pages
│   ├── nginx.conf           # Production nginx config
│   └── Dockerfile
├── deploy/
│   ├── systemd/             # Production process supervision
│   └── scripts/             # release.sh (with auto-rollback)
├── docs/                    # Architecture, runbook, ADRs
├── .github/workflows/       # CI: lint → test → build → push
├── docker-compose.yml       # Dev
├── docker-compose.prod.yml  # Prod
├── .env.dev / .env.staging / .env.prod
└── README.md (this file)
```

### License

MIT — see [`LICENSE`](LICENSE).
