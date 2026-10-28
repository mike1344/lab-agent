"""探测当前 OpenAI 兼容网关是否支持 Embedding，以及可用的模型名。

用法（在 backend 目录执行）：
    .\\.venv\\Scripts\\python.exe scripts\\probe_embedding.py

只发送一个极短文本（"测试"），用于确认能力，不写入数据库、不暴露密钥。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from openai import OpenAI  # noqa: E402


def main() -> None:
    if not settings.OPENAI_API_KEY:
        raise SystemExit("未配置 OPENAI_API_KEY，跳过探测")
    print(f"网关：{settings.OPENAI_BASE_URL or '官方默认'}")
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        timeout=20,
    )

    candidates = ["text-embedding-3-small", "text-embedding-ada-002", "embedding-3-small"]
    try:
        models = [item.id for item in client.models.list().data]
        print("网关模型列表（前 20 个）：", ", ".join(models[:20]))
        candidates = [name for name in models if "embed" in name.lower()] + candidates
    except Exception as exc:  # noqa: BLE001 - 一些网关不开放 /models
        print(f"[WARN] 无法读取模型列表：{type(exc).__name__}: {str(exc)[:100]}")

    tried = set()
    for model in candidates:
        if model in tried:
            continue
        tried.add(model)
        try:
            response = client.embeddings.create(model=model, input="测试")
            vector = response.data[0].embedding
            print(f"[OK] {model} 可用，维度 {len(vector)}，前 3 维 {vector[:3]}")
            print(f"建议：RAG_PROVIDER=api，RAG_EMBEDDING_MODEL={model}")
        except Exception as exc:  # noqa: BLE001 - 探测失败是预期分支
            print(f"[FAIL] {model}: {type(exc).__name__}: {str(exc)[:100]}")


if __name__ == "__main__":
    main()
