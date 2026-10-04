from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.agent import KNOWLEDGE, run_agent
from app.knowledge import MAX_DOCUMENT_BYTES, add_document, get_document, list_documents
from app.llm import LLMServiceError, deepseek_is_configured, deepseek_model
from app.schemas import ChatRequest, ChatResponse

app = FastAPI(title="健康知识 Agent · FastAPI 入门", version="0.2.0",
              description="先检索本地知识库，再调用 DeepSeek 的 RAG 教学项目。无诊断或临床分诊能力。")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health", tags=["基础"])
def health():
    configured = deepseek_is_configured()
    return {
        "status": "ok",
        "mode": "deepseek_rag" if configured else "local_knowledge",
        "model": deepseek_model() if configured else None,
        "knowledge_documents": len(list_documents()),
    }


@app.get("/api/topics", tags=["知识库"])
def topics(q: str = Query(default="", max_length=100)):
    # 查询参数示例：/api/topics?q=饮食
    return [{"id": item["id"], "title": item["title"]}
            for item in KNOWLEDGE if q in item["title"]]


@app.get("/api/topics/{topic_id}", tags=["知识库"])
def topic(topic_id: str):
    # 路径参数 + 404 错误示例。
    for item in KNOWLEDGE:
        if item["id"] == topic_id:
            return item
    raise HTTPException(status_code=404, detail="主题不存在")


@app.get("/api/knowledge", tags=["本地知识库"])
def knowledge_documents():
    return list_documents()


@app.post("/api/knowledge", tags=["本地知识库"])
async def upload_knowledge(file: UploadFile = File(...)):
    content = await file.read(MAX_DOCUMENT_BYTES + 1)
    try:
        result = add_document(file.filename or "document.md", content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@app.get("/api/knowledge/{doc_id}", tags=["本地知识库"])
def read_knowledge(doc_id: str):
    result = get_document(doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="知识文档不存在")
    metadata, text = result
    return {**metadata, "content": text}


@app.post("/api/chat", response_model=ChatResponse, tags=["Agent"])
async def chat(payload: ChatRequest):
    # Pydantic 先校验 JSON，合法请求才会进入本函数。
    try:
        return await run_agent(payload.message)
    except LLMServiceError as exc:
        # 不把 API Key、SDK 堆栈或第三方完整响应暴露给网页。
        raise HTTPException(status_code=503, detail=str(exc)) from exc
