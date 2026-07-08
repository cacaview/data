# Contributing to ACTAP / 贡献指南

[English](#english) · [中文](#中文)

---

## English

Thanks for your interest in ACTAP! This document covers the development workflow, coding standards, and review process.

### Code of conduct

Be respectful, constructive, and inclusive. See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

### Workflow

1. **Fork** the repo and create a feature branch:
   ```bash
   git checkout -b feat/your-feature
   ```
2. **Make changes** following the standards below.
3. **Run local checks** before committing:
   ```bash
   # Backend
   cd backend
   ruff check . && ruff format --check .
   pytest -v --cov=app

   # Frontend
   cd frontend
   npm run lint
   npm run build
   ```
4. **Commit** with [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat(scope): short description
   fix(scope): short description
   refactor(scope): short description
   docs(scope): short description
   test(scope): short description
   ```
5. **Push** and open a pull request against `main`.
6. CI must pass (lint + tests on Python 3.10/3.11/3.12).
7. **One approval** from a maintainer is required to merge.

### Coding standards

#### Python (backend)

- **Style**: PEP 8 + ruff (configured in `backend/pyproject.toml`)
- **Type hints**: required on all public functions and class attributes
- **Architecture**: respect the 4-layer separation
  - `api/routes/` — thin HTTP layer (validate input, delegate to service, serialize output)
  - `services/` — business logic; no SQLAlchemy queries
  - `repositories/` — all DB access; no business logic
  - `models/` — ORM + Pydantic schemas only
- **Constants**: never use magic numbers; add to `app/core/constants.py`
- **Errors**: raise `BusinessError` for domain errors; let middleware sanitize
- **Tests**: every new feature needs at least one unit test; one integration test for new HTTP endpoints
- **Coverage**: core business logic (`app/services/`, `app/data/analytics.py`) must stay ≥ 80 %

#### TypeScript (frontend)

- **Style**: oxlint (configured in `frontend/.oxlintrc.json`)
- **Types**: NO `any`. Use the domain types in `src/types/`
- **State**: prefer the `useApi` hook over manual `useState<any>(null) + loading flag`
- **Components**: functional components with hooks
- **Formatting**: rely on editor auto-format on save

### Pull request checklist

- [ ] Branch is up to date with `main`
- [ ] Lint passes (`ruff` + `oxlint`)
- [ ] Tests added/updated; coverage not decreased
- [ ] API changes documented in [`docs/API.md`](docs/API.md)
- [ ] Architecture changes have an ADR in [`docs/adr/`](docs/adr/)
- [ ] CHANGELOG.md updated under "Unreleased"
- [ ] No hardcoded secrets
- [ ] No `console.log` / `print()` left in production code

### Reporting bugs

Open a GitHub issue with:
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Docker version, browser)
- Relevant log lines (include `request_id`)

### Security issues

**Do not** open a public issue. Email <security@your-org.com>.

---

## 中文

感谢关注 ACTAP！本文档介绍开发流程、编码规范与代码评审流程。

### 工作流

1. **Fork** 仓库并创建特性分支
2. **提交前** 运行本地检查（lint + test）
3. **Commit** 遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范
4. **Push** 并对 `main` 发起 PR
5. CI 全部通过 + 1 位维护者审批后合并

### 编码规范

#### Python 后端

- PEP 8 + ruff（见 `backend/pyproject.toml`）
- 所有公开函数必须带类型注解
- 严格遵循四层架构：`api → services → repositories → models`
- 不允许使用魔术数字，统一放到 `app/core/constants.py`
- 业务错误抛 `BusinessError`，由中间件统一脱敏
- 新功能必须配套单元测试；新 HTTP 端点必须有集成测试
- 核心业务代码覆盖率 ≥ 80%

#### TypeScript 前端

- oxlint 规范（`frontend/.oxlintrc.json`）
- **禁止 `any`**，使用 `src/types/` 中的领域类型
- 优先使用 `useApi` hook 替代 `useState<any>(null) + loading`
- 函数组件 + Hooks

### PR 自检清单

- [ ] 分支基于最新 `main`
- [ ] Lint 通过
- [ ] 测试已补充，覆盖率未下降
- [ ] API 变更已写入 `docs/API.md`
- [ ] 架构变更已添加 ADR
- [ ] CHANGELOG.md 已更新
- [ ] 无硬编码密钥
- [ ] 无残留 `console.log` / `print()`

### 报告 Bug

在 GitHub 提 issue，附上：复现步骤 / 预期 vs 实际 / 环境 / 日志（含 `request_id`）。

### 安全问题

**不要** 公开提 issue，发送邮件到 <security@your-org.com>。
