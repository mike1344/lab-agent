"""RAG 固定评估集：Recall@K、MRR、引用准确率、拒答率、分类指标与检索延迟。

用法（在 backend 目录执行）：
    .\\.venv\\Scripts\\python.exe scripts\\eval_rag.py
    .\\.venv\\Scripts\\python.exe scripts\\eval_rag.py --k 3 --min-score 0.2
    .\\.venv\\Scripts\\python.exe scripts\\eval_rag.py --markdown-out docs/rag-eval-latest.md

评估数据：backend/eval/rag_eval.jsonl
字段：question / expected_source / answerable / category；管理员专属用例可加 "admin": true。
脚本调用与线上相同的 search_documents_with_meta，因此指标可直接反映当前配置
（RAG_PROVIDER / RAG_MIN_SCORE / RAG_MIN_COVERAGE / RAG_MIN_VECTOR_SCORE / RAG_HYBRID_ALPHA）。
切换 BGE：先 pip install sentence-transformers，再设 RAG_PROVIDER=bge。
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# 评估只需要知识库检索，不连数据库；CI 没有 backend/.env，这里补最小默认值。
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "rag-eval-only")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.knowledge import embedding_provider, search_documents_with_meta  # noqa: E402
from app.config import settings  # noqa: E402

EVAL_FILE = Path(__file__).resolve().parent.parent / "eval" / "rag_eval.jsonl"


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * ratio))]


def evaluate(k: int, min_score: float) -> dict:
    settings.RAG_MIN_SCORE = min_score
    cases = [json.loads(line) for line in EVAL_FILE.read_text("utf-8").splitlines() if line.strip()]
    answerable = [case for case in cases if case.get("answerable")]
    unanswerable = [case for case in cases if not case.get("answerable")]

    latencies: list[float] = []
    categories: dict[str, dict] = {}

    def bucket(name: str) -> dict:
        return categories.setdefault(
            name,
            {
                "answerable": 0,
                "unanswerable": 0,
                "recall_hits": 0,
                "reciprocal_ranks": [],
                "citation_hits": 0,
                "refused": 0,
            },
        )

    # 预热：BGE 模型加载、Chroma collection 首次同步都是秒级一次性成本，
    # 不应计入单题检索延迟；预热后再开始计时。
    search_documents_with_meta("预热检索", limit=1, is_admin=True)
    latencies.clear()

    def timed_search(question: str, admin: bool = False):
        """统一计一次检索耗时（包含向量化、Chroma/BM25 全链路）。"""
        started = time.perf_counter()
        result = search_documents_with_meta(question, limit=k, is_admin=admin)
        latencies.append((time.perf_counter() - started) * 1000)
        return result

    detail = []
    for case in answerable:
        category = case.get("category", "uncategorized")
        stats = bucket(category)
        result = timed_search(case["question"], admin=bool(case.get("admin", False)))
        sources = [item["source"] for item in result["items"]]
        expected = case["expected_source"]
        rank = sources.index(expected) + 1 if expected in sources else 0
        stats["answerable"] += 1
        stats["recall_hits"] += 1 if rank else 0
        stats["reciprocal_ranks"].append(1 / rank if rank else 0.0)
        if sources and sources[0] == expected:
            stats["citation_hits"] += 1
        detail.append(
            {
                "question": case["question"],
                "category": category,
                "admin": bool(case.get("admin", False)),
                "expected": expected,
                "retrieved": sources,
                "rank": rank,
                "score": round(result["items"][0]["score"], 4) if result["items"] else 0.0,
            }
        )

    for case in unanswerable:
        category = case.get("category", "uncategorized")
        stats = bucket(category)
        result = timed_search(case["question"], admin=bool(case.get("admin", False)))
        stats["unanswerable"] += 1
        if not result["ok"]:
            stats["refused"] += 1
        detail.append(
            {
                "question": case["question"],
                "category": category,
                "expected": "(拒答)",
                "retrieved": [item["source"] for item in result["items"]],
                "refused": not result["ok"],
            }
        )

    recall_hits = sum(stats["recall_hits"] for stats in categories.values())
    reciprocal_ranks = [rank for stats in categories.values() for rank in stats["reciprocal_ranks"]]
    citation_hits = sum(stats["citation_hits"] for stats in categories.values())
    refused = sum(stats["refused"] for stats in categories.values())

    recall_key = f"recall@{k}"
    by_category = {}
    for name, stats in sorted(categories.items()):
        answerable_count = stats["answerable"]
        unanswerable_count = stats["unanswerable"]
        by_category[name] = {
            "answerable": answerable_count,
            "unanswerable": unanswerable_count,
            recall_key: round(stats["recall_hits"] / answerable_count, 4) if answerable_count else None,
            "mrr": round(sum(stats["reciprocal_ranks"]) / answerable_count, 4) if answerable_count else None,
            "citation_accuracy": (round(stats["citation_hits"] / answerable_count, 4) if answerable_count else None),
            "refusal_rate": round(stats["refused"] / unanswerable_count, 4) if unanswerable_count else None,
        }

    return {
        "provider": embedding_provider(),
        "k": k,
        "min_score": min_score,
        "min_coverage": settings.RAG_MIN_COVERAGE,
        "min_vector_score": settings.RAG_MIN_VECTOR_SCORE,
        "cases": len(cases),
        "avg_retrieval_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "p50_retrieval_ms": round(_percentile(latencies, 0.50), 2),
        "p95_retrieval_ms": round(_percentile(latencies, 0.95), 2),
        recall_key: round(recall_hits / len(answerable), 4) if answerable else 0.0,
        "mrr": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4) if reciprocal_ranks else 0.0,
        "citation_accuracy": round(citation_hits / len(answerable), 4) if answerable else 0.0,
        "refusal_rate": round(refused / len(unanswerable), 4) if unanswerable else 0.0,
        "by_category": by_category,
        "detail": detail,
    }


def render_markdown(report: dict) -> str:
    """把评估结果渲染成便于贴进报告的 Markdown。"""
    recall_key = f"recall@{report['k']}"

    def fmt(value):
        return "-" if value is None else value

    lines = [
        "# RAG 评估结果",
        "",
        f"- 向量方案：`{report['provider']}`",
        f"- Top-K：{report['k']}，最低混合分：{report['min_score']}，"
        f"最低覆盖率：{report['min_coverage']}，最低向量分：{report['min_vector_score']}",
        f"- 题目数：{report['cases']}，"
        f"平均检索延迟：{report['avg_retrieval_ms']} ms，"
        f"P50：{report['p50_retrieval_ms']} ms，P95：{report['p95_retrieval_ms']} ms",
        "",
        "| 指标 | 值 |",
        "| --- | --- |",
        f"| Recall@{report['k']} | {report[recall_key]} |",
        f"| MRR | {report['mrr']} |",
        f"| 引用准确率 | {report['citation_accuracy']} |",
        f"| 拒答率 | {report['refusal_rate']} |",
        "",
        "## 分类指标",
        "",
        "| 类别 | 可回答 | 不可回答 | Recall | MRR | 引用准确率 | 拒答率 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, stats in report["by_category"].items():
        lines.append(
            f"| {name} | {stats['answerable']} | {stats['unanswerable']} | "
            f"{fmt(stats[recall_key])} | {fmt(stats['mrr'])} | "
            f"{fmt(stats['citation_accuracy'])} | {fmt(stats['refusal_rate'])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG 固定评估集")
    parser.add_argument("--k", type=int, default=settings.RAG_TOP_K)
    parser.add_argument("--min-score", type=float, default=settings.RAG_MIN_SCORE)
    parser.add_argument("--json", action="store_true", help="输出完整 JSON（含逐题明细）")
    parser.add_argument("--markdown-out", default="", help="把汇总写入 Markdown 文件")
    args = parser.parse_args()

    report = evaluate(args.k, args.min_score)
    summary = {key: value for key, value in report.items() if key != "detail"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
        print(f"\nMarkdown 报告已写入：{args.markdown_out}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("\n逐题明细：")
        for item in report["detail"]:
            print(" -", json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    main()
