"""Agent 工作流：紧急词检查 → DeepSeek 或本地规则 → 结构化响应。"""
from app.knowledge import search_knowledge as retrieve_knowledge
from app.llm import ask_deepseek, deepseek_is_configured
from app.schemas import ChatResponse, Source

KNOWLEDGE = [
    {
        "id": "diet", "title": "健康饮食", "keywords": ["饮食", "吃什么", "蔬菜", "水果", "营养"],
        "answer": "一般健康饮食强调食物多样化，包括蔬菜、水果、全谷物和豆类，并减少过多的盐、游离糖和不健康脂肪。具体饮食需要结合个人情况。",
        "url": "https://www.who.int/news-room/fact-sheets/healthy-diet",
    },
    {
        "id": "activity", "title": "身体活动", "keywords": ["运动", "锻炼", "久坐", "活动", "散步"],
        "answer": "规律身体活动有益健康。身体活动也包括步行、骑行等日常活动；减少久坐，并选择适合自身状况的活动。存在疾病或运动不适时，应向医务人员咨询适合自己的安排。",
        "url": "https://www.who.int/news-room/fact-sheets/detail/physical-activity",
    },
]


def search_knowledge(message: str) -> list[dict]:
    """工具函数：关键词检索；后续可以替换成向量检索。"""
    return [item for item in KNOWLEDGE if any(word in message for word in item["keywords"])]


def run_rule_agent(message: str) -> ChatResponse:
    """没有配置 API Key 时运行的原始关键词版本。"""
    # 故意保守的示例匹配：不能识别所有紧急情况，也无法理解否定句。
    if any(word in message for word in ["胸痛", "呼吸困难", "昏迷", "大出血", "自杀"]):
        return ChatResponse(
            route="urgent_hint", steps=["匹配到紧急相关词", "停止知识问答"],
            answer="问题包含可能涉及紧急情况的词语。如果你或他人正在经历紧急症状，请立即联系当地急救服务（中国大陆可拨打 120）。本演示无法评估病情；即使没有触发提示，也不代表安全。",
        )
    if any(word in message for word in ["药", "剂量", "诊断", "什么病", "治疗", "处方", "症状", "疼", "发烧", "咳嗽", "糖尿病", "高血压", "孕", "肾病"]):
        return ChatResponse(
            route="boundary", steps=["识别个体诊疗相关词", "提示能力边界"],
            answer="当前版本只演示一般健康知识查询，不能根据症状判断疾病，也不能推荐药物、剂量或个体治疗方案。请向有资质的医务人员咨询。你可以试问：如何保持健康饮食？",
        )
    matches = search_knowledge(message)
    if not matches:
        return ChatResponse(route="unknown", steps=["调用知识查询工具", "未命中知识库"],
                            answer="目前知识库只包含健康饮食和身体活动两个主题，还不能回答这个问题。可以试问：久坐与运动有什么关系？")
    return ChatResponse(
        route="knowledge", steps=["调用知识查询工具", f"命中 {len(matches)} 条资料", "返回知识摘要及来源"],
        answer="\n\n".join(item["answer"] for item in matches),
        sources=[Source(title=item["title"], url=item["url"]) for item in matches],
    )


async def run_agent(message: str) -> ChatResponse:
    # 这条确定性规则放在模型调用之前。它只是教学提示，不是医学分诊系统。
    if any(word in message for word in ["胸痛", "呼吸困难", "昏迷", "大出血", "自杀"]):
        return ChatResponse(
            route="urgent_hint",
            steps=["匹配到紧急相关词", "停止普通问答"],
            answer="问题包含可能涉及紧急情况的词语。如果你或他人正在经历紧急症状，请立即联系当地急救服务（中国大陆可拨打 120）。本演示无法评估病情；即使没有触发提示，也不代表安全。",
        )

    matches = retrieve_knowledge(message)
    if not matches:
        if not deepseek_is_configured():
            return run_rule_agent(message)
        return ChatResponse(
            route="unknown",
            answer="我的本地知识库里没有检索到足够相关的资料，因此不会调用 DeepSeek 猜测答案。请先添加可信资料，或换一种问法。",
            steps=["检索本地知识库", "没有足够相关片段", "未调用 DeepSeek"],
            mode="deepseek_rag" if deepseek_is_configured() else "rule_demo",
        )

    if not deepseek_is_configured():
        return ChatResponse(
            route="knowledge",
            answer="\n\n".join(item["text"] for item in matches),
            sources=[item["source"] for item in matches],
            steps=["检索本地知识库", f"命中 {len(matches)} 个片段", "未配置模型，直接返回资料"],
            mode="local_knowledge",
        )

    answer = await ask_deepseek(message, [item["text"] for item in matches])
    return ChatResponse(
        route="knowledge",
        answer=answer,
        sources=[item["source"] for item in matches],
        steps=["检索本地知识库", f"命中 {len(matches)} 个片段", "将片段交给 DeepSeek", "返回模型答案"],
        mode="deepseek_rag",
    )
