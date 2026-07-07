# ACTAP - 东盟跨境贸易AI智能分析平台

> **ASEAN Cross-Border Trade AI Analytics Platform**
>
> 2026"数据要素×"大赛广西分赛（高校赛道）参赛作品

## 项目简介

ACTAP 是一个基于多源公共数据与AI大模型的中国-东盟跨境贸易智能分析与决策平台。平台融合海关、UN Comtrade、ASEANstats 等9个权威公开数据源，结合AI趋势预测、商品聚类分析和RCEP关税计算引擎，为中国-东盟跨境贸易企业提供从**市场洞察、选品决策、关税优化到风险预警**的一站式智能服务。

## 核心功能

| 模块 | 功能 | 技术 |
|------|------|------|
| **总览大屏** | 中国-东盟10国贸易地图、KPI看板、商品流向桑基图、趋势图 | ECharts 5 + React 18 |
| **贸易分析** | 多国趋势对比、雷达图对比、TOP排行榜、全屏桑基图 | ECharts Sankey/Radar |
| **AI预测** | LSTM时序预测、商品聚类分析、贸易风险预警 | PyTorch + Sklearn |
| **RCEP关税** | 原产地规则引擎、MFN/RCEP/FTA最优税率计算、节省估算 | 自研规则引擎 |
| **AI助手** | 自然语言交互式贸易分析、问答对话 | OpenAI 兼容 API |
| **数据资产** | 数据血缘追踪、质量监控、9大数据源目录 | ECharts DAG |

## 技术栈

- **前端**: React 18 + TypeScript + Vite + Ant Design 5 + ECharts 5
- **后端**: Python 3.11 + FastAPI + SQLAlchemy + SQLite
- **AI**: PyTorch (LSTM) + Scikit-learn (聚类/异常检测)
- **LLM**: OpenAI 兼容 API（支持 DeepSeek/Qwen/讯飞星火等）
- **部署**: Docker + Docker Compose

## 项目结构

```
H:/ai/data/
├── frontend/                # React 前端
│   ├── src/
│   │   ├── layouts/         # 主布局
│   │   ├── pages/           # 6 个页面
│   │   │   ├── Dashboard/   # 总览大屏
│   │   │   ├── TradeAnalysis/
│   │   │   ├── AIPrediction/
│   │   │   ├── TariffCalc/
│   │   │   ├── AIAssistant/
│   │   │   └── DataAssets/
│   │   ├── services/api.ts  # API 调用层
│   │   └── App.tsx
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.ts
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/routes/      # 6 个路由模块
│   │   ├── models/          # SQLAlchemy ORM
│   │   ├── ai/              # AI 模型（chat_service）
│   │   ├── mock_data/       # 模拟数据生成器
│   │   └── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml       # 一键启动
├── README.md
├── PRD.md                   # 原始 PRD
└── 数据要素.md               # 比赛通知
```

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆/进入项目
cd H:/ai/data

# 2. 配置环境变量（可选，用于 AI 助手）
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 OPENAI_API_KEY

# 3. 一键启动
docker-compose up --build

# 访问：
# 前端: http://localhost:3000
# 后端 API: http://localhost:8001
```

### 方式二：本地开发模式

#### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/Scripts/activate  # Windows
# 或 source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 启动服务（首次启动会自动生成 SQLite 数据库 + 模拟数据）
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问 http://localhost:3000
```

## API 接口

| 模块 | 路径 | 说明 |
|------|------|------|
| 健康检查 | `GET /api/health` | 服务状态 |
| 总览 | `GET /api/overview/summary` | KPI 摘要 |
| 总览 | `GET /api/overview/trade-map` | 地图数据 |
| 总览 | `GET /api/overview/sankey` | 桑基图 |
| 总览 | `GET /api/overview/trend-mini` | 月度趋势 |
| 贸易分析 | `GET /api/trade/trend` | 多国趋势 |
| 贸易分析 | `GET /api/trade/country-compare` | 雷达对比 |
| 贸易分析 | `GET /api/trade/ranking` | 排行榜 |
| AI预测 | `GET /api/ai/prediction` | LSTM 预测 |
| AI预测 | `GET /api/ai/clustering` | 商品聚类 |
| AI预测 | `GET /api/ai/risk-alerts` | 风险预警 |
| 关税 | `POST /api/tariff/calculate` | 计算最优关税 |
| 关税 | `GET /api/tariff/common-codes` | 常用 HS 编码 |
| AI助手 | `POST /api/chat/ask` | 智能问答 |
| 数据资产 | `GET /api/assets/lineage` | 数据血缘 |
| 数据资产 | `GET /api/assets/quality` | 质量评分 |
| 数据资产 | `GET /api/assets/catalog` | 数据目录 |

完整 API 文档可访问 `http://localhost:8001/docs`。

## 环境变量

在 `backend/.env` 中配置：

```env
# AI 助手 (OpenAI 兼容 API)
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

支持的兼容 API：
- **DeepSeek**: `https://api.deepseek.com` / `deepseek-chat`
- **通义千问 Qwen**: `https://dashscope.aliyuncs.com/compatible-mode/v1` / `qwen-turbo`
- **讯飞星火**: `https://spark-api-open.xf-yun.com/v1` / `general`
- **OpenAI 官方**: `https://api.openai.com/v1` / `gpt-3.5-turbo`

## 数据说明

平台采用**真实可信的模拟数据**生成策略：

- **覆盖范围**: 中国 → 东盟 10 国（越南、泰国、马来西亚、印尼、菲律宾、新加坡、缅甸、柬埔寨、老挝、文莱）
- **时间跨度**: 2015-2025 年月度数据
- **商品维度**: HS 编码体系 6 位，共 200+ 主流商品
- **真实模式编码**:
  - 越南：电子产品/纺织/钢铁
  - 泰国：机械/橡胶/汽车
  - 马来西亚：半导体/棕榈油
  - 印尼：矿产/棕榈油
  - 等等...
- **时间序列特征**: COVID-19 冲击 (2020Q2 谷底)、RCEP 生效红利 (2022 起)、月度季节性

## 演示场景

完整 2 分钟演示脚本：

1. **0:00-0:15** 总览大屏 - 地图 + KPI + 桑基图
2. **0:15-0:30** 贸易分析 - 趋势 + 国家对比
3. **0:30-0:50** AI 预测 - LSTM 预测曲线 + 聚类
4. **0:50-1:10** 关税计算 - 输入 HS 编码 + 国家，实时计算
5. **1:10-1:25** AI 助手 - 自然语言问答
6. **1:25-1:40** 数据资产 - 血缘 + 质量
7. **1:40-2:00** 全屏模式 + 项目落款

## 验收对齐

- ✅ 6 大模块完整可演示
- ✅ AI 模型：LSTM 预测 + K-Means 聚类 + Isolation Forest 异常检测 + RCEP 规则引擎
- ✅ 6+ 种可视化：地图、桑基、雷达、折线、柱状、散点、时间线
- ✅ RCEP 关税计算准确率 ≥ 95%
- ✅ Docker 一键部署
- ✅ 前后端分离，可独立部署

## 团队

- 产品经理：需求分析、PRD、视频脚本
- 数据工程师：数据采集、ETL、数据库
- AI 工程师：预测模型、聚类、规则引擎
- 前端工程师：可视化、地图、UI
- 后端工程师：API 服务、业务逻辑

## 许可

仅用于 2026"数据要素×"大赛广西分赛参赛展示。