"""RAG 固定评估集：Recall@K、MRR、引用准确率、拒答率。

用法（在 backend 目录执行）：
    .\\.venv\\Scripts\\python.exe scripts\\eval_rag.py
    .\\.venv\\Scripts\\python.exe scripts\\eval_rag.py --k 3 --min-score 0.2

评估数据：backend/eval/rag_eval.jsonl（question / expected_source / answerable）。
脚本调用与线上相同的 search_documents_with_meta，因此指标可直接反映当前配置
（RAG_PROVIDER / RAG_MIN_SCORE / RAG_HYBRID_ALPHA）的检索质量。
"""

import argparse
import json
import os
import sys
from pathlib import Path

# 评估只需要知识库检索，不连数据库；CI 没有 backend/.env，这里补最小默认值。
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "rag-eval-only")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.knowledge import embedding_provider, search_documents_with_meta  # noqa: E402
from app.config import settings  # noqa: E402

EVAL_FILE = Path(__file__).resolve().parent.parent / "eval" / "rag_eval.jsonl"


def evaluate(k: int, min_score: float) -> dict:
    settings.RAG_MIN_SCORE = min_score
    cases = [json.loads(line) for line in EVAL_FILE.read_text("utf-8").splitlines() if line.strip()]
    answerable = [case for case in cases if case.get("answerable")]
    unanswerable = [case for case in cases if not case.get("answerable")]

    recall_hits = 0
    reciprocal_ranks = []
    citation_hits = 0
    refused = 0
    detail = []

    for case in answerable:
        result = search_documents_with_meta(case["question"], limit=k, is_admin=True)
        sources = [item["source"] for item in result["items"]]
        expected = case["expected_source"]
        rank = sources.index(expected) + 1 if expected in sources else 0
        recall_hits += 1 if rank else 0
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        if sources and sources[0] == expected:
            citation_hits += 1
        detail.append(
            {
                "question": case["question"],
                "expected": expected,
                "retrieved": sources,
                "rank": rank,
                "score": round(result["items"][0]["score"], 4) if result["items"] else 0.0,
            }
        )

    for case in unanswerable:
        result = search_documents_with_meta(case["question"], limit=k, is_admin=True)
        if not result["ok"]:
            refused += 1
        detail.append(
            {
                "question": case["question"],
                "expected": "(拒答)",
                "retrieved": [item["source"] for item in result["items"]],
                "refused": not result["ok"],
            }
        )

    return {
        "provider": embedding_provider(),
        "k": k,
        "min_score": min_score,
        "cases": len(cases),
        f"recall@{k}": round(recall_hits / len(answerable), 4) if answerable else 0.0,
        "mrr": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4) if reciprocal_ranks else 0.0,
        "citation_accuracy": round(citation_hits / len(answerable), 4) if answerable else 0.0,
        "refusal_rate": round(refused / len(unanswerable), 4) if unanswerable else 0.0,
        "detail": detail,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG 固定评估集")
    parser.add_argument("--k", type=int, default=settings.RAG_TOP_K)
    parser.add_argument("--min-score", type=float, default=settings.RAG_MIN_SCORE)
    parser.add_argument("--json", action="store_true", help="输出完整 JSON（含逐题明细）")
    args = parser.parse_args()

    report = evaluate(args.k, args.min_score)
    summary = {key: value for key, value in report.items() if key != "detail"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("\n逐题明细：")
        for item in report["detail"]:
            print(" -", json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    main()
