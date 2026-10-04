"""本地 Markdown/TXT 知识库和轻量级字符 n-gram 检索。"""
from collections import Counter
from pathlib import Path
import re
import uuid

from app.schemas import Source


ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT / "knowledge_base"
SUPPORTED_SUFFIXES = {".md", ".txt"}
MAX_DOCUMENT_BYTES = 1_000_000
MAX_CHUNK_CHARS = 900
MIN_RELEVANCE = 0.20


def ensure_knowledge_dir() -> None:
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)


def _tokens(text: str) -> list[str]:
    """保留英文词，并将连续汉字拆为相邻二字片段，支持基础中文词面检索。"""
    result: list[str] = []
    for part in re.findall(r"[\u3400-\u9fff]+|[a-zA-Z0-9]+", text.casefold()):
        if re.fullmatch(r"[\u3400-\u9fff]+", part):
            result.extend(part[i:i + 2] for i in range(len(part) - 1))
            if len(part) == 1:
                result.append(part)
        else:
            result.append(part)
    return result


def _chunks(text: str) -> list[str]:
    """Return chunks, starting a new group when a new explicit source appears."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[tuple[str, str | None]] = []
    buffer = ""
    source_url: str | None = None
    for paragraph in paragraphs:
        if re.match(r"^#\s+", paragraph):
            continue
        link = re.fullmatch(r"(?i)(?:来源|source_url)\s*[:：]\s*(https?://\S+)", paragraph)
        if link:
            if buffer:
                chunks.append((buffer, source_url))
                buffer = ""
            source_url = link.group(1).rstrip(")]，。")
            continue
        while len(paragraph) > MAX_CHUNK_CHARS:
            if buffer:
                chunks.append((buffer, source_url))
                buffer = ""
            chunks.append((paragraph[:MAX_CHUNK_CHARS], source_url))
            paragraph = paragraph[MAX_CHUNK_CHARS:]
        if buffer and len(buffer) + len(paragraph) > MAX_CHUNK_CHARS:
            chunks.append((buffer, source_url))
            buffer = ""
        buffer = f"{buffer}\n\n{paragraph}".strip()
    if buffer:
        chunks.append((buffer, source_url))
    return chunks


def _doc_id(path: Path) -> str:
    return path.name.split("--", 1)[0] if "--" in path.name else path.stem


def _metadata(text: str, path: Path) -> tuple[str, str | None]:
    heading = re.search(r"(?m)^#\s+(.+?)\s*$", text)
    title = heading.group(1).strip() if heading else path.stem
    link = re.search(r"(?im)^\s*(?:来源|source_url)\s*[:：]\s*(https?://\S+)\s*$", text)
    return title, link.group(1).rstrip(")]，。") if link else None


def list_documents() -> list[dict]:
    ensure_knowledge_dir()
    documents = []
    for path in sorted(KNOWLEDGE_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            text = path.read_text(encoding="utf-8-sig")
            title, source_url = _metadata(text, path)
            documents.append({
                "id": _doc_id(path),
                "title": title,
                "filename": path.name,
                "source_url": source_url,
                "characters": len(text),
            })
    return documents


def add_document(filename: str, content: bytes) -> dict:
    ensure_knowledge_dir()
    original = Path(filename or "document.md").name
    suffix = Path(original).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError("只支持 .md 或 .txt 文件")
    if not content:
        raise ValueError("文件内容不能为空")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError("单个文件不能超过 1 MB")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("文件必须使用 UTF-8 编码") from exc
    if not text.strip():
        raise ValueError("文件内容不能为空")

    doc_id = uuid.uuid4().hex
    safe_original = re.sub(r"[^\w.-]+", "_", original, flags=re.UNICODE).strip("._")[:80] or f"document{suffix}"
    path = KNOWLEDGE_DIR / f"{doc_id}--{safe_original}"
    path.write_text(text, encoding="utf-8")
    title, source_url = _metadata(text, path)
    return {"id": doc_id, "title": title, "filename": path.name, "source_url": source_url, "characters": len(text)}


def get_document(doc_id: str) -> tuple[dict, str] | None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", doc_id):
        return None
    ensure_knowledge_dir()
    candidates = list(KNOWLEDGE_DIR.glob(f"{doc_id}--*"))
    candidates.extend(KNOWLEDGE_DIR / f"{doc_id}{suffix}" for suffix in SUPPORTED_SUFFIXES)
    for path in candidates:
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            text = path.read_text(encoding="utf-8-sig")
            title, source_url = _metadata(text, path)
            return ({"id": _doc_id(path), "title": title, "filename": path.name, "source_url": source_url}, text)
    return None


def search_knowledge(query: str, limit: int = 4) -> list[dict]:
    """检索本地文件的文本片段；没有足够词面重叠时返回空列表。"""
    query_tokens = set(_tokens(query))
    if not query_tokens:
        return []
    ranked: list[dict] = []
    for document in list_documents():
        loaded = get_document(document["id"])
        if not loaded:
            continue
        _, text = loaded
        title, document_url = _metadata(text, Path(document["filename"]))
        for index, (chunk, chunk_url) in enumerate(_chunks(text), start=1):
            chunk_tokens = set(_tokens(chunk))
            overlap = query_tokens & chunk_tokens
            score = len(overlap) / len(query_tokens)
            if score >= MIN_RELEVANCE:
                ranked.append({
                    "title": title,
                    "text": chunk,
                    "score": score,
                    "source": Source(
                        title=f"{title}（片段 {index}）",
                        url=chunk_url or document_url or f"/api/knowledge/{document['id']}",
                    ),
                })
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit]
