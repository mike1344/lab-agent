# RAG 检索评估报告

> 生成时间：2026-10-28  
> 评估对象：`backend/app/ai/knowledge.py` 的混合检索链路  
> 固定评估集：`backend/eval/rag_eval.jsonl`

## 1. 评估环境

| 项目 | 配置 |
| --- | --- |
| 操作系统 | Windows 11 家庭版 |
| CPU | 12th Gen Intel Core i7-12650H（10 核 16 线程） |
| Python | 3.14.6 |
| 数据库 | 本地 MySQL 8.4（检索评估不依赖数据库） |
| 向量后端 | ChromaDB（本地持久化） |
| 评估脚本 | `backend/scripts/eval_rag.py` |

## 2. 数据与指标

- 知识库：`backend/app/knowledge/`，当前 2 个 Markdown 文档、2 个块（`lab_rules.md`、`equipment_guide.md`），平均块长约 142 字符。
- 评估集：8 题，其中 5 题可回答（标注期望来源），3 题不可回答。
- 指标定义：
  - **Recall@4**：期望来源是否出现在 Top-4 中；
  - **MRR**：期望来源排名的倒数均值；
  - **引用准确率**：Top-1 来源是否等于期望来源；
  - **拒答率**：不可回答的问题被判定为证据不足（`ok=False`）的比例；
  - **检索延迟**：单次 `search_documents_with_meta` 全链路耗时（包含文档加载、Chroma/BM25、向量化），预热后统计。

> 说明：知识库和评估集都很小，以下指标用于**回归对比和方案验证**，不应包装成通用 benchmark。

## 3. 评估结果

| 向量方案 | Recall@4 | MRR | 引用准确率 | 拒答率 | 平均检索延迟 | P95 延迟 |
| --- | --- | --- | --- | --- | --- | --- |
| `local`（默认，离线哈希） | 1.0 | 1.0 | 1.0 | 0.667 | 14.37 ms | 20.07 ms |
| `bge`（bge-small-zh-v1.5） | 1.0 | 1.0 | 1.0 | **1.0** | 26.73 ms | 30.73 ms |

### 3.1 结论

1. 两种方案的检索排序在固定集上都正确（Recall/MRR/引用准确率 1.0）。
2. `local` 的拒答率只有 0.667：`实验室可以养猫吗` 与知识库共享「实验室/可以」等词面，纯词面向量无法判断语义无关，这是文档中已说明的已知取舍。
3. 切换到 BGE 后，`RAG_MIN_VECTOR_SCORE=0.45` 过滤掉语义不相关结果，拒答率达到 1.0；代价是平均检索延迟从约 14 ms 增加到约 27 ms（模型已加载、索引已同步的稳态）。
4. BGE 的阈值校准依据：可回答问题的 Top-1 向量分最低约 0.61，不可回答问题的最高约 0.42，0.45 取中间值。换模型或改评估集后必须重新校准。

### 3.2 延迟口径

- 表中延迟**不含**首次模型加载和首次 Chroma collection 同步（这两个是一次性成本，BGE 首次可达秒级）。
- 评估脚本在正式计时前执行一次“预热检索”，避免把冷启动算进单题延迟。
- 本机是开发环境，数值用于横向对比，不代表生产容量。

## 4. 复现方式

```powershell
cd backend

# local（默认）
.\.venv\Scripts\python.exe scripts\eval_rag.py

# BGE（可选依赖 + 模型）
.\.venv\Scripts\python.exe -m pip install sentence-transformers
$env:RAG_PROVIDER="bge"
$env:HF_ENDPOINT="https://hf-mirror.com"   # 国内网络可选
.\.venv\Scripts\python.exe scripts\eval_rag.py
```

输出 JSON（含逐题明细）：

```powershell
.\.venv\Scripts\python.exe scripts\eval_rag.py --json
```

## 5. 局限与后续

- **没有生成侧 faithfulness 评估**：当前只有检索指标，没有判断“模型答案是否被引用证据支持”。本机网关 chat 模型返回 429（需实名认证/更高 RPM），无法运行 LLM-as-judge；不伪造指标。可用模型恢复后补 `question + answer + cited chunks` 的 judge 流程。
- **评估集小**：8 题、2 个文档，指标接近 1.0 更多说明“链路正确”，不能说明泛化能力。真实上线应扩充到几十份文档和上百题。
- **`local` 不适合语义检索**：默认保留它是为了离线零依赖；对外表述 RAG 能力时应明确使用 BGE/API 向量，并引用本报告的对照结果。
- **BGE 未进入默认依赖**：`sentence-transformers` 体积大，未写入 `requirements.txt`，避免 CI/Docker 膨胀；生产要单独决定是否安装或改用 Embedding API。