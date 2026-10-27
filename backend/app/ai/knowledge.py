"""知识库检索：文档解析 → 标题感知分块 → 混合检索（向量 + BM25）→ 引用与置信度。

升级点（相对初版字符哈希检索）：
1. 支持 Markdown / 文本 / Word(.docx) / PDF（PDF 需可选依赖 pypdf）；
2. 标题感知分块，块元数据包含 title / section / version / visibility；
3. 可配置 Embedding：local（默认，离线哈希向量）、bge（sentence-transformers）、api（OpenAI 兼容接口）；
4. 向量与 BM25 混合召回，按 RAG_HYBRID_ALPHA 加权；可选轻量重排（标题/章节命中加权）；
5. 返回相似度分数并按 RAG_MIN_SCORE 过滤，证据不足时显式标记 ok=False（供拒答）；
6. 按内容哈希增量同步 ChromaDB，文件新增/修改/删除都不需要清库。

默认 local 向量保证离线可运行；企业/面试场景可切换 BGE 或 API Embedding。
"""

import hashlib
import importlib
import importlib.util
import logging
import math
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from app.config import settings

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
CHROMA_DIR = Path(__file__).resolve().parent.parent.parent / "chroma_db"
logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".md", ".txt", ".docx", ".pdf"}
CHUNK_TARGET_CHARS = 200
_WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


# ==================== 文档读取与分块 ====================


def _read_docx(path: Path) -> str:
    """用标准库解析 .docx（本质是 zip + word/document.xml），不引入额外依赖。"""
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
        root = ET.fromstring(xml)
        paragraphs = []
        for paragraph in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
            text = "".join(
                node.text or ""
                for node in paragraph.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
            )
            if text.strip():
                paragraphs.append(text.strip())
        return "\n\n".join(paragraphs)
    except Exception as exc:  # noqa: BLE001 - 单个文件解析失败不影响其他文档
        logger.warning("Word 文档解析失败：%s（%s）", path.name, exc)
        return ""


def _optional_import(module_name: str):
    """可选依赖动态导入：未安装时返回 None，且不进入必装依赖清单。"""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def _read_pdf(path: Path) -> str:
    """PDF 解析依赖可选的 pypdf；未安装时跳过并提示，不影响其余文档。"""
    pypdf = _optional_import("pypdf")
    if pypdf is None:
        logger.warning("未安装 pypdf，跳过 PDF：%s（pip install pypdf 后可解析）", path.name)
        return ""
    try:
        reader = pypdf.PdfReader(str(path))
        return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("PDF 解析失败：%s（%s）", path.name, exc)
        return ""


def _read_source(path: Path) -> str:
    if path.suffix.lower() in {".md", ".txt"}:
        return path.read_text("utf-8")
    if path.suffix.lower() == ".docx":
        return _read_docx(path)
    if path.suffix.lower() == ".pdf":
        return _read_pdf(path)
    return ""


_FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """解析可选的 YAML 风格头部：title / version / visibility（不引入 PyYAML）。"""
    match = _FRONT_MATTER_PATTERN.match(text)
    if not match:
        return {}, text
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            metadata[key.strip().lower()] = value.strip().strip('"').strip("'")
    return metadata, text[match.end() :]


def _split_sections(body: str) -> list[tuple[str, str]]:
    """按 Markdown 标题切分章节；没有标题时整篇视为「正文」。"""
    sections: list[tuple[str, str]] = []
    current_title = "正文"
    buffer: list[str] = []
    for line in body.splitlines():
        if line.lstrip().startswith("#"):
            if "".join(buffer).strip():
                sections.append((current_title, "\n".join(buffer).strip()))
            current_title = line.lstrip("#").strip() or "正文"
            buffer = []
        else:
            buffer.append(line)
    if "".join(buffer).strip():
        sections.append((current_title, "\n".join(buffer).strip()))
    return sections or [("正文", body.strip())]


def _chunk_section(text: str) -> list[str]:
    """按空行聚合成 200 字左右的块，保证引用粒度适中。"""
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for index, paragraph in enumerate(paragraphs):
        current += paragraph + "\n\n"
        if len(current) >= CHUNK_TARGET_CHARS or index == len(paragraphs) - 1:
            chunks.append(current.strip())
            current = ""
    return chunks


def load_documents() -> list[dict]:
    """读取知识库目录，返回带标题/章节/版本/权限元数据的块。"""
    chunks: list[dict] = []
    for path in sorted(KNOWLEDGE_DIR.glob("*")):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        text = _read_source(path)
        if not text.strip():
            continue
        metadata, body = _parse_front_matter(text)
        sections = _split_sections(body)
        first_section = sections[0][0] if sections else ""
        title = metadata.get("title") or (first_section if first_section and first_section != "正文" else path.stem)
        version = metadata.get("version", "v1")
        visibility = metadata.get("visibility", "public").lower()
        chunk_index = 0
        for section, section_text in sections:
            for chunk_text in _chunk_section(section_text):
                chunks.append(
                    {
                        "id": f"{path.stem}_chunk{chunk_index}",
                        "source": path.name,
                        "title": title,
                        "section": section,
                        "version": version,
                        "visibility": visibility,
                        "text": chunk_text,
                    }
                )
                chunk_index += 1
    return chunks


# ==================== Embedding ====================


def build_local_embedding(text: str, dimensions: int = 128) -> list[float]:
    """离线确定性向量：字符 + 相邻双字符哈希，无需下载模型。"""
    normalized_text = "".join(text.lower().split())
    if not normalized_text:
        return [0.0] * dimensions

    tokens = list(normalized_text)
    tokens.extend(normalized_text[index : index + 2] for index in range(len(normalized_text) - 1))

    vector = [0.0] * dimensions
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
        vector_index = int.from_bytes(digest[:2], "big") % dimensions
        direction = 1.0 if digest[2] % 2 else -1.0
        vector[vector_index] += direction

    vector_length = math.sqrt(sum(value * value for value in vector))
    return [value / vector_length for value in vector] if vector_length else vector


_bge_model = None


def _bge_embedding(text: str) -> list[float]:
    """本地中文 Embedding（BGE 系列）；未安装 sentence-transformers 时抛错由调用方降级。"""
    global _bge_model
    if _bge_model is None:
        sentence_transformers = _optional_import("sentence_transformers")
        if sentence_transformers is None:
            raise RuntimeError("未安装 sentence-transformers，无法使用 BGE Embedding")
        _bge_model = sentence_transformers.SentenceTransformer(settings.RAG_EMBEDDING_MODEL)
    vector = _bge_model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def _api_embedding(text: str) -> list[float]:
    """OpenAI 兼容 Embedding 接口（可用 OPENAI_BASE_URL 指向兼容网关）。"""
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    response = client.embeddings.create(model=settings.RAG_EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def build_embedding(text: str) -> list[float]:
    """按 RAG_PROVIDER 选择向量实现；失败自动降级到 local 并记录日志。"""
    provider = (settings.RAG_PROVIDER or "local").strip().lower()
    if provider == "bge":
        try:
            return _bge_embedding(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("BGE Embedding 不可用，已降级 local：%s", exc)
    elif provider == "api":
        try:
            return _api_embedding(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("API Embedding 不可用，已降级 local：%s", exc)
    return build_local_embedding(text)


def embedding_provider() -> str:
    """实际生效的向量提供方（配置为 bge/api 但依赖不可用时显示 local）。"""
    provider = (settings.RAG_PROVIDER or "local").strip().lower()
    if provider == "bge":
        if importlib.util.find_spec("sentence_transformers") is None:
            return "local"
        return "bge"
    if provider == "api":
        return "api" if settings.OPENAI_API_KEY else "local"
    return "local"


def collection_name() -> str:
    """不同向量模型混用会导致维度不一致，因此按 provider+model 区分 collection。"""
    provider = embedding_provider()
    if provider == "local":
        return "lab_knowledge"
    model_slug = re.sub(r"[^a-zA-Z0-9]+", "_", settings.RAG_EMBEDDING_MODEL)[:40]
    return f"lab_knowledge_{provider}_{model_slug}"


# ==================== 增量同步 ====================


def build_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sync_collection(collection, documents: list[dict]) -> None:
    """按内容哈希增量同步：新增/修改 upsert，删除的文档从 collection 移除。"""
    indexed = collection.get(include=["metadatas"])
    indexed_ids = indexed.get("ids") or []
    indexed_metadatas = indexed.get("metadatas") or []
    indexed_metadata_by_id = {
        document_id: (metadata or {}) for document_id, metadata in zip(indexed_ids, indexed_metadatas)
    }
    local_document_by_id = {document["id"]: document for document in documents}

    deleted_ids = sorted(set(indexed_ids) - set(local_document_by_id))
    if deleted_ids:
        collection.delete(ids=deleted_ids)

    changed_documents = []
    for document in documents:
        old_metadata = indexed_metadata_by_id.get(document["id"], {})
        current_hash = build_content_hash(document["text"])
        if old_metadata.get("content_hash") != current_hash or old_metadata.get("source") != document["source"]:
            changed_documents.append((document, current_hash))

    if changed_documents:
        collection.upsert(
            ids=[document["id"] for document, _ in changed_documents],
            documents=[document["text"] for document, _ in changed_documents],
            metadatas=[
                {
                    "source": document["source"],
                    "title": document["title"],
                    "section": document["section"],
                    "version": document["version"],
                    "visibility": document["visibility"],
                    "content_hash": content_hash,
                }
                for document, content_hash in changed_documents
            ],
            embeddings=[build_embedding(document["text"]) for document, _ in changed_documents],
        )


# ==================== 混合检索 ====================


def _tokenize(text: str) -> list[str]:
    normalized = "".join(text.lower().split())
    tokens = list(normalized)
    tokens.extend(normalized[index : index + 2] for index in range(len(normalized) - 1))
    return tokens


def _bm25_scores(query: str, documents: list[dict], k1: float = 1.5, b: float = 0.75) -> dict[str, float]:
    """纯 Python BM25：中文按字符 + 双字切分，无需 jieba 依赖。"""
    query_tokens = _tokenize(query)
    if not query_tokens or not documents:
        return {}

    tokenized_documents = {doc["id"]: _tokenize(doc["text"]) for doc in documents}
    average_length = sum(len(tokens) for tokens in tokenized_documents.values()) / len(documents)
    document_frequency: dict[str, int] = {}
    for tokens in tokenized_documents.values():
        for token in set(tokens):
            document_frequency[token] = document_frequency.get(token, 0) + 1

    total_documents = len(documents)
    scores: dict[str, float] = {}
    for document in documents:
        tokens = tokenized_documents[document["id"]]
        score = 0.0
        for token in query_tokens:
            frequency = tokens.count(token)
            if not frequency:
                continue
            idf = math.log(1 + (total_documents - document_frequency[token] + 0.5) / (document_frequency[token] + 0.5))
            denominator = frequency + k1 * (1 - b + b * len(tokens) / (average_length or 1))
            score += idf * frequency * (k1 + 1) / (denominator or 1)
        scores[document["id"]] = score
    return scores


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    maximum = max(scores.values(), default=0.0)
    return {key: (value / maximum if maximum else 0.0) for key, value in scores.items()}


def simple_search(query: str, limit: int = 3, is_admin: bool = False) -> list[dict]:
    """无 ChromaDB 时的 BM25 检索（保留旧函数名，供降级路径使用）。"""
    documents = [doc for doc in load_documents() if is_admin or doc.get("visibility") != "admin"]
    scores = _normalize(_bm25_scores(query, documents))
    ranked = sorted(documents, key=lambda doc: scores.get(doc["id"], 0.0), reverse=True)
    return ranked[:limit]


def _merge_results(
    query: str,
    vector_items: list[dict],
    bm25_scores: dict[str, float],
    documents_by_id: dict[str, dict],
) -> list[dict]:
    """向量相似度与 BM25 分数合并，并把词面覆盖率纳入分数与阈值判断。

    仅按最大值归一化的 BM25 会让任意查询的“最相关文档”都得到 1.0，
    导致无证据查询也能通过阈值。这里用查询双字词的覆盖率给关键词分量加权，
    本地哈希向量（纯词面）模式还要求覆盖率不低于 RAG_MIN_COVERAGE。
    """
    alpha = min(max(settings.RAG_HYBRID_ALPHA, 0.0), 1.0)
    bm25_normalized = _normalize(bm25_scores)
    query_bigrams = [token for token in _tokenize(query) if len(token) == 2]

    merged: dict[str, dict] = {}
    for item in vector_items:
        merged[item["id"]] = {
            "id": item["id"],
            "text": item["text"],
            "metadata": item["metadata"],
            "vector_score": item["vector_score"],
            "bm25_score": bm25_normalized.get(item["id"], 0.0),
        }
    for document in documents_by_id.values():
        bm25_score = bm25_normalized.get(document["id"], 0.0)
        if bm25_score <= 0 or document["id"] in merged:
            continue
        merged[document["id"]] = {
            "id": document["id"],
            "text": document["text"],
            "metadata": {
                "source": document["source"],
                "title": document["title"],
                "section": document["section"],
                "version": document["version"],
                "visibility": document["visibility"],
            },
            "vector_score": 0.0,
            "bm25_score": bm25_score,
        }

    for item in merged.values():
        metadata = item["metadata"] or {}
        searchable_text = f"{metadata.get('title', '')} {metadata.get('section', '')} {item['text']}"
        hits = sum(1 for bigram in query_bigrams if bigram in searchable_text)
        coverage = hits / len(query_bigrams) if query_bigrams else 0.0
        item["coverage"] = round(coverage, 4)
        item["score"] = alpha * item["vector_score"] + (1 - alpha) * item["bm25_score"] * coverage + 0.05 * coverage
    return sorted(merged.values(), key=lambda item: item["score"], reverse=True)


def search_documents_with_meta(
    query: str,
    limit: int | None = None,
    is_admin: bool = False,
) -> dict:
    """混合检索：返回 {items, backend, ok, provider}。

    ok=False 表示证据不足（供上层拒答）；items 每项包含相似度分数与来源元数据。
    """
    limit = limit or settings.RAG_TOP_K
    provider = embedding_provider()
    all_documents = load_documents()
    visible_documents = [doc for doc in all_documents if is_admin or doc.get("visibility") != "admin"]
    documents_by_id = {doc["id"]: doc for doc in visible_documents}
    bm25_scores = _bm25_scores(query, visible_documents)

    if not visible_documents or limit <= 0:
        return {"items": [], "backend": "ChromaDB", "ok": False, "provider": provider}

    try:
        import chromadb

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_or_create_collection(name=collection_name())
        # 同步全部文档（包括 admin 可见文档），权限过滤在检索结果上完成
        sync_collection(collection, all_documents)
        document_count = collection.count()
        if document_count == 0:
            return {"items": [], "backend": "ChromaDB", "ok": False, "provider": provider}

        result = collection.query(
            query_embeddings=[build_embedding(query)],
            n_results=min(max(limit * 3, 5), document_count),
        )
        ids = result.get("ids", [[]])[0]
        texts = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        vector_items = []
        for document_id, text, metadata, distance in zip(ids, texts, metadatas, distances):
            metadata = metadata or {}
            if not is_admin and metadata.get("visibility") == "admin":
                continue
            # Chroma 使用余弦距离，范围 [0, 2]，转换成 [0, 1] 相似度
            similarity = max(0.0, 1.0 - float(distance) / 2.0)
            vector_items.append({"id": document_id, "text": text, "metadata": metadata, "vector_score": similarity})

        merged = _merge_results(query, vector_items, bm25_scores, documents_by_id)
        items = [
            {
                "id": item["id"],
                "text": item["text"],
                "source": item["metadata"].get("source", "knowledge"),
                "title": item["metadata"].get("title", ""),
                "section": item["metadata"].get("section", ""),
                "version": item["metadata"].get("version", "v1"),
                "score": round(item["score"], 4),
                "coverage": item["coverage"],
                "vector_score": round(item["vector_score"], 4),
                "bm25_score": round(item["bm25_score"], 4),
            }
            for item in merged
        ][:limit]
        # 本地哈希向量是纯词面匹配：没有词面命中就视为无证据（避免 0 覆盖也能拿分）
        if provider == "local":
            items = [item for item in items if item["coverage"] >= settings.RAG_MIN_COVERAGE]
        items = [item for item in items if item["score"] >= settings.RAG_MIN_SCORE]
        return {"items": items, "backend": "ChromaDB", "ok": bool(items), "provider": provider}
    except Exception as exc:  # noqa: BLE001 - RAG 不是核心业务硬依赖
        logger.warning("ChromaDB 检索失败，已切换到本地 BM25：%s", exc)
        ranked = simple_search(query, limit, is_admin=is_admin)
        scores = _normalize(bm25_scores)
        query_bigrams = [token for token in _tokenize(query) if len(token) == 2]
        items = []
        for document in ranked:
            searchable_text = f"{document['title']} {document['section']} {document['text']}"
            hits = sum(1 for bigram in query_bigrams if bigram in searchable_text)
            coverage = hits / len(query_bigrams) if query_bigrams else 0.0
            score = scores.get(document["id"], 0.0) * coverage
            if coverage < settings.RAG_MIN_COVERAGE or score < settings.RAG_MIN_SCORE:
                continue
            items.append(
                {
                    "id": document["id"],
                    "text": document["text"],
                    "source": document["source"],
                    "title": document["title"],
                    "section": document["section"],
                    "version": document["version"],
                    "score": round(score, 4),
                    "coverage": round(coverage, 4),
                    "vector_score": 0.0,
                    "bm25_score": round(scores.get(document["id"], 0.0), 4),
                }
            )
        return {"items": items, "backend": "本地关键词检索", "ok": bool(items), "provider": provider}


def search_documents(query: str, limit: int = 3) -> tuple[list[dict], str]:
    """兼容旧调用：返回 (命中文本块, 检索后端)。"""
    result = search_documents_with_meta(query, limit=limit)
    return result["items"], result["backend"]
