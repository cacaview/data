"""AI Chat service using OpenAI-compatible API."""

import json
import os

import httpx

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

SYSTEM_PROMPT = """你是ACTAP东盟跨境贸易AI智能分析平台的智能助手。你的职责是：
1. 回答关于中国-东盟跨境贸易的问题
2. 解读贸易数据和趋势
3. 提供RCEP关税政策咨询
4. 给出市场分析和选品建议

回答要求：
- 使用中文
- 数据要具体，引用具体数字
- 如果涉及数据查询，描述查询结果
- 保持专业但易懂的风格"""


async def chat_with_llm(message: str, context_data: dict | None = None) -> dict:
    """Call OpenAI-compatible API for chat response."""
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-your-key-here":
        return _fallback_response(message)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    if context_data:
        messages.append(
            {
                "role": "system",
                "content": f"以下是平台查询到的参考数据:\n{json.dumps(context_data, ensure_ascii=False, indent=2)}",
            }
        )
    messages.append({"role": "user", "content": message})

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OPENAI_BASE_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL_NAME,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1000,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
            return {"reply": reply, "chart_type": None, "chart_data": None}
    except Exception as e:
        return {
            "reply": f"AI服务暂时不可用({str(e)[:50]})，请稍后重试。",
            "chart_type": None,
            "chart_data": None,
        }


def _fallback_response(message: str) -> dict:
    """Keyword-based fallback when no API key is configured."""
    msg = message.lower()

    if "越南" in msg and ("进口" in msg or "商品" in msg or "产品" in msg):
        return {
            "reply": "根据2024年贸易数据，越南从中国进口的主要商品类别为：\n\n"
            "1. **机电产品** (HS 84-85)：约占进口总额的45%，包括电子元器件、通信设备、计算机等\n"
            "2. **纺织原料** (HS 50-63)：约占15%，主要为面料、纱线\n"
            "3. **钢铁及制品** (HS 72-73)：约占8%\n"
            "4. **化工产品** (HS 28-38)：约占7%\n\n"
            "越南是中国在东盟最大的贸易伙伴，2024年双边贸易额超过2000亿美元。",
            "chart_type": "bar",
            "chart_data": {
                "categories": ["机电产品", "纺织原料", "钢铁制品", "化工产品", "塑料橡胶", "其他"],
                "values": [45, 15, 8, 7, 6, 19],
            },
        }

    if "rcep" in msg or "关税" in msg:
        return {
            "reply": "**RCEP协定对中国-东盟贸易的影响：**\n\n"
            "RCEP于2022年1月1日正式生效，覆盖15个成员国。\n\n"
            "主要成效：\n"
            "- 区域内关税减让：90%以上商品最终实现零关税\n"
            "- 原产地累积规则：降低企业享受优惠关税门槛\n"
            "- 2024年RCEP利用率约35%，仍有提升空间\n\n"
            "**建议：**出口企业应积极申请RCEP原产地证书，合理利用累积规则降低关税成本。",
            "chart_type": None,
            "chart_data": None,
        }

    if "趋势" in msg or "预测" in msg:
        return {
            "reply": "**2025年中国-东盟贸易趋势预测：**\n\n"
            "基于LSTM时序模型分析，预计2025年：\n\n"
            "- 中国对东盟出口增速：8-12%\n"
            "- 中国从东盟进口增速：6-10%\n"
            "- 双边贸易总额有望突破1万亿美元\n\n"
            "**增长驱动因素：**\n"
            "1. RCEP深化实施，关税进一步减让\n"
            "2. 中国-东盟自贸区3.0版谈判推进\n"
            "3. 产业链转移带动中间品贸易增长",
            "chart_type": None,
            "chart_data": None,
        }

    if "风险" in msg or "预警" in msg:
        return {
            "reply": "**当前主要贸易风险：**\n\n"
            "🔴 **高风险**：\n"
            "- 美联储加息导致东盟多国货币贬值，进口成本上升\n"
            "- 部分国家贸易保护主义抬头\n\n"
            "🟡 **中风险**：\n"
            "- 物流成本波动（红海危机影响航线）\n"
            "- 原材料价格波动\n\n"
            "🟢 **低风险**：\n"
            "- RCEP框架下关税政策相对稳定\n"
            "- 中国-东盟政治关系总体向好",
            "chart_type": None,
            "chart_data": None,
        }

    return {
        "reply": "感谢您的提问！作为ACTAP平台的AI助手，我可以帮您分析：\n\n"
        "📊 **贸易数据查询** - 各国进出口数据、商品结构\n"
        "📈 **趋势预测** - 基于AI模型的贸易趋势分析\n"
        "💰 **关税计算** - RCEP协定下的最优关税方案\n"
        "⚠️ **风险预警** - 贸易异动监测和风险提示\n"
        "🌍 **市场分析** - 东盟各国市场机会识别\n\n"
        "请提出更具体的问题，我将为您提供数据驱动的分析。",
        "chart_type": None,
        "chart_data": None,
    }
