import hashlib
import logging
import math
from pathlib import Path


KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
CHROMA_DIR = Path(__file__).resolve().parent.parent.parent / "chroma_db"
logger = logging.getLogger(__name__)


def load_documents() -> list[dict[str, str]]:
    """读取本地 Markdown 知识，按段落分块，每块 200-400 字。"""
    raw_docs = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        raw_docs.append({"id": path.stem, "source": path.name, "text": path.read_text("utf-8")})

    # 分块：按空行分段，累积到 200 字以上就切一块
    chunks = []
    for doc in raw_docs:
        paragraphs = [p.strip() for p in doc["text"].split("\n\n") if p.strip()]
        current = ""
        for i, para in enumerate(paragraphs):
            current += para + "\n\n"
            if len(current) >= 200 or i == len(paragraphs) - 1:
                chunks.append({
                    "id": f"{doc['id']}_chunk{len([c for c in chunks if c['id'].startswith(doc['id'])])}",
                    "source": doc["source"],
                    "text": current.strip(),
                })
                current = ""
    return chunks


def simple_search(query: str, limit: int = 3) -> list[dict[str, str]]:
    """无 ChromaDB 时使用字符命中数排序，保证项目仍可独立运行。"""
    keywords = {char for char in query.lower() if char.strip()}
    scored = []
    for document in load_documents():
        score = sum(document["text"].lower().count(keyword) for keyword in keywords)
        scored.append((score, document))
    return [item[1] for item in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def build_local_embedding(text: str, dimensions: int = 128) -> list[float]:
    """把文本转换成可复现的轻量向量，避免首次运行再下载额外模型。

    ChromaDB 默认会下载一个英文嵌入模型。在网络较慢、没有模型缓存的环境里，
    第一次检索可能长时间卡住。这里使用“字符 + 相邻双字符”的哈希向量：它不依赖
    网络，适合本项目规模较小的中文知识库。以后接入正式嵌入模型时，只需替换这个
    函数，下面的 ChromaDB 存储和查询逻辑都不需要修改。
    """
    normalized_text = "".join(text.lower().split())
    if not normalized_text:
        return [0.0] * dimensions

    # 单字符能覆盖关键词；相邻双字符能保留一部分中文词语信息。
    tokens = list(normalized_text)
    tokens.extend(normalized_text[index : index + 2] for index in range(len(normalized_text) - 1))

    vector = [0.0] * dimensions
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
        vector_index = int.from_bytes(digest[:2], "big") % dimensions
        direction = 1.0 if digest[2] % 2 else -1.0
        vector[vector_index] += direction

    # L2 归一化后，ChromaDB 的距离比较不会被文档长度主导。
    vector_length = math.sqrt(sum(value * value for value in vector))
    return [value / vector_length for value in vector] if vector_length else vector


def build_content_hash(text: str) -> str:
    """计算文档内容指纹，用来判断 Markdown 是否真正发生了修改。

    不直接使用文件修改时间，因为复制、解压等操作会改变时间却不改变内容，
    SHA-256 可以避免这类无意义的重复向量化。
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sync_collection(collection, documents: list[dict[str, str]]) -> None:
    """把本地 Markdown 的新增、修改和删除同步到 ChromaDB。

    同步规则：
    1. 本地新增文件：通过 ``upsert`` 写入；
    2. 内容指纹或文件名变化：重新计算向量并更新；
    3. 本地已删除文件：从 collection 中删除对应记录。

    每次 upsert 都显式传入 ``embeddings``，因此 ChromaDB 不会调用默认
    嵌入函数，也不会在首次运行时联网下载模型。
    """
    indexed = collection.get(include=["metadatas"])
    indexed_ids = indexed.get("ids") or []
    indexed_metadatas = indexed.get("metadatas") or []

    # 旧版索引可能没有 content_hash，此时会被视为需要更新，
    # 从而自动完成索引格式迁移，不需要手动删除 chroma_db。
    indexed_metadata_by_id = {
        document_id: (metadata or {})
        for document_id, metadata in zip(indexed_ids, indexed_metadatas)
    }
    local_document_by_id = {document["id"]: document for document in documents}

    deleted_ids = sorted(set(indexed_ids) - set(local_document_by_id))
    if deleted_ids:
        collection.delete(ids=deleted_ids)

    changed_documents = []
    for document in documents:
        old_metadata = indexed_metadata_by_id.get(document["id"], {})
        current_hash = build_content_hash(document["text"])
        if (
            old_metadata.get("content_hash") != current_hash
            or old_metadata.get("source") != document["source"]
        ):
            changed_documents.append((document, current_hash))

    if changed_documents:
        collection.upsert(
            ids=[document["id"] for document, _ in changed_documents],
            documents=[document["text"] for document, _ in changed_documents],
            metadatas=[
                {"source": document["source"], "content_hash": content_hash}
                for document, content_hash in changed_documents
            ],
            # 使用项目内的确定性向量，保证离线可运行。
            embeddings=[build_local_embedding(document["text"]) for document, _ in changed_documents],
        )


def search_documents(query: str, limit: int = 3) -> tuple[list[dict[str, str]], str]:
    """优先使用 ChromaDB 向量检索，依赖不可用时自动切换到本地检索。"""
    try:
        import chromadb

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_or_create_collection(name="lab_knowledge")
        documents = load_documents()
        # 检索前做一次轻量增量同步，知识库文件修改后无需重启服务。
        sync_collection(collection, documents)

        # 空知识库时直接返回，避免对空 collection 执行 n_results=1。
        document_count = collection.count()
        if document_count == 0 or limit <= 0:
            return [], "ChromaDB"

        result = collection.query(
            query_embeddings=[build_local_embedding(query)],
            n_results=min(limit, document_count),
        )
        items = []
        for text, metadata in zip(result.get("documents", [[]])[0], result.get("metadatas", [[]])[0]):
            items.append({"text": text, "source": metadata.get("source", "knowledge")})
        return items, "ChromaDB"
    except Exception as exc:
        # RAG 不是登录、预约等核心业务的硬依赖：向日志记录真实原因，再安全降级，
        # 这样用户仍能使用 AI 页面，开发者也能从后端终端快速定位依赖问题。
        logger.warning("ChromaDB 检索失败，已切换到本地关键词检索：%s", exc)
        return simple_search(query, limit), "本地关键词检索"
