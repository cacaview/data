"""AI chat assistant routes -- keyword-matching Q&A with trade data context."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas_db import TradeRecord, Country
from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter()

# ── Keyword -> handler mapping for offline Q&A ─────────────────────────────

_SUGGESTED_QUESTIONS = [
    "中国与东盟贸易总额是多少？",
    "哪个国家是中国最大的贸易伙伴？",
    "2024年贸易增长最快的商品类别是什么？",
    "RCEP协定对关税有什么影响？",
    "如何利用RCEP原产地规则降低关税？",
    "电子产品出口到越南的关税是多少？",
    "中国对东盟出口的主要产品有哪些？",
    "今年贸易趋势如何？",
]


def _answer_top_partner(db: Session) -> ChatResponse:
    latest = db.query(func.max(TradeRecord.year)).scalar()
    row = (
        db.query(TradeRecord.partner, func.sum(TradeRecord.trade_value_usd).label("total"))
        .filter(TradeRecord.year == latest, TradeRecord.reporter == "CHN")
        .group_by(TradeRecord.partner)
        .order_by(func.sum(TradeRecord.trade_value_usd).desc())
        .first()
    )
    if not row:
        return ChatResponse(reply="暂无贸易数据可供分析。")

    country = db.query(Country).filter(Country.code == row[0]).first()
    name = country.name_cn if country else row[0]
    return ChatResponse(
        reply=f"根据{latest}年数据，中国最大的贸易伙伴是**{name}**，"
              f"双边贸易额约为 **{row[1] / 1e8:.2f} 亿美元**。",
        chart_type="bar",
    )


def _answer_total_trade(db: Session) -> ChatResponse:
    latest = db.query(func.max(TradeRecord.year)).scalar()
    total = (
        db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 0.0))
        .filter(TradeRecord.year == latest, TradeRecord.reporter == "CHN")
        .scalar()
    )
    prev = (
        db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 0.0))
        .filter(TradeRecord.year == (latest or 0) - 1, TradeRecord.reporter == "CHN")
        .scalar()
    )
    growth = ((total - prev) / prev * 100) if prev else 0.0
    return ChatResponse(
        reply=f"中国与东盟{latest}年贸易总额约为 **{total / 1e8:.2f} 亿美元**，"
              f"同比增长 **{growth:.1f}%**。"
    )


def _answer_top_product(db: Session) -> ChatResponse:
    latest = db.query(func.max(TradeRecord.year)).scalar()
    row = (
        db.query(TradeRecord.hs_section, func.sum(TradeRecord.trade_value_usd).label("total"))
        .filter(
            TradeRecord.year == latest,
            TradeRecord.reporter == "CHN",
            TradeRecord.hs_section.isnot(None),
        )
        .group_by(TradeRecord.hs_section)
        .order_by(func.sum(TradeRecord.trade_value_usd).desc())
        .first()
    )
    if not row:
        return ChatResponse(reply="暂无商品类别数据。")
    return ChatResponse(
        reply=f"{latest}年中国与东盟贸易中，增长贡献最大的商品类别是 **{row[0]}**，"
              f"贸易额约 **{row[1] / 1e8:.2f} 亿美元**。",
        chart_type="pie",
    )


def _answer_rcep(db: Session) -> ChatResponse:
    return ChatResponse(
        reply=(
            "**RCEP（区域全面经济伙伴关系协定）** 对关税的主要影响：\n\n"
            "1. **关税减让**：覆盖90%以上的货物贸易关税，逐步降至零关税\n"
            "2. **原产地累积规则**：15个成员国的原材料和加工可累积计算区域价值成分\n"
            "3. **贸易便利化**：简化海关程序，加快通关速度\n"
            "4. **投资准入**：扩大市场开放，降低投资壁垒\n\n"
            "建议使用本平台的**关税计算器**功能，查询具体商品的RCEP优惠税率。"
        )
    )


def _answer_tariff_calc(db: Session) -> ChatResponse:
    return ChatResponse(
        reply=(
            "您可以使用平台的**关税计算**模块进行查询：\n\n"
            "1. 进入「关税计算」页面\n"
            "2. 输入商品HS编码\n"
            "3. 选择原产国和目的国\n"
            "4. 输入货物价值\n\n"
            "系统将自动比较MFN税率、RCEP税率和FTA税率，为您推荐最优关税方案。"
        )
    )


def _answer_export_products(db: Session) -> ChatResponse:
    latest = db.query(func.max(TradeRecord.year)).scalar()
    rows = (
        db.query(TradeRecord.hs_section, func.sum(TradeRecord.trade_value_usd).label("total"))
        .filter(
            TradeRecord.year == latest,
            TradeRecord.reporter == "CHN",
            TradeRecord.trade_flow == "export",
            TradeRecord.hs_section.isnot(None),
        )
        .group_by(TradeRecord.hs_section)
        .order_by(func.sum(TradeRecord.trade_value_usd).desc())
        .limit(5)
        .all()
    )
    if not rows:
        return ChatResponse(reply="暂无出口数据。")

    lines = [f"{i+1}. **{r[0]}** -- {r[1] / 1e8:.2f} 亿美元" for i, r in enumerate(rows)]
    return ChatResponse(
        reply=f"中国对东盟主要出口产品（{latest}年）：\n\n" + "\n".join(lines),
        chart_type="bar",
    )


def _answer_trend(db: Session) -> ChatResponse:
    rows = (
        db.query(
            TradeRecord.year,
            func.sum(TradeRecord.trade_value_usd).label("total"),
        )
        .filter(TradeRecord.reporter == "CHN")
        .group_by(TradeRecord.year)
        .order_by(TradeRecord.year)
        .all()
    )
    if len(rows) < 2:
        return ChatResponse(reply="历史数据不足以判断趋势。")

    lines = [f"- {r[0]}年: {r[1] / 1e8:.2f} 亿美元" for r in rows[-4:]]
    latest_change = (rows[-1][1] - rows[-2][1]) / rows[-2][1] * 100 if rows[-2][1] else 0
    direction = "增长" if latest_change > 0 else "下降"

    return ChatResponse(
        reply=f"近年来中国与东盟贸易趋势：\n\n" + "\n".join(lines)
              + f"\n\n最近一年同比{direction} **{abs(latest_change):.1f}%**。",
        chart_type="line",
    )


# Keyword table: (keywords, handler)
_KEYWORD_TABLE: list[tuple[list[str], callable]] = [
    (["最大贸易伙伴", "最大伙伴", "第一大", "第一伙伴", "top partner"], _answer_top_partner),
    (["贸易总额", "总贸易", "总额", "total trade"], _answer_total_trade),
    (["增长最快", "增长贡献", "最大商品", "top product", "主要产品", "出口产品"], _answer_top_product),
    (["rcep", "RCEP", "关税影响", "rcep影响"], _answer_rcep),
    (["关税计算", "计算关税", "关税是多少", "tariff", "hs编码"], _answer_tariff_calc),
    (["出口", "export", "出口到东盟"], _answer_export_products),
    (["趋势", "trend", "走势"], _answer_trend),
]


# ── POST /ask ───────────────────────────────────────────────────────────────
@router.post("/ask", response_model=ChatResponse)
def ask_chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Keyword-matching chatbot.

    Fallback implementation when no LLM API key is configured.
    """
    message = req.message.strip()
    if not message:
        return ChatResponse(reply="请输入您的问题。")

    message_lower = message.lower()

    # Try keyword matching
    for keywords, handler in _KEYWORD_TABLE:
        for kw in keywords:
            if kw.lower() in message_lower:
                return handler(db)

    # Fallback: generic help
    return ChatResponse(
        reply=(
            f"您询问了「{message}」。\n\n"
            "目前系统支持以下类型的问题：\n"
            "- 中国与东盟贸易总额\n"
            "- 最大贸易伙伴\n"
            "- 主要出口产品\n"
            "- RCEP关税影响\n"
            "- 关税计算方法\n"
            "- 贸易趋势\n\n"
            "请选择相关话题提问，或前往对应功能页面获取详细分析。"
        )
    )


# ── GET /suggestions ────────────────────────────────────────────────────────
@router.get("/suggestions")
def get_suggestions():
    """Return a list of suggested chat questions.

    Wrapped in `{suggestions: [...]}` to align with the frontend type
    declaration `ChatResponse.suggestions`.
    """
    return {"suggestions": _SUGGESTED_QUESTIONS}
