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

- 知识库：`backend/app/knowledge/`，当前 **10 个 Markdown 文档、35 个块**，覆盖预约规则、设备、安全、审批、常见问题、隐私、采购、课程、AI 说明和内部运维。
- 评估集：**40 题**，其中 32 题可回答（标注期望来源），8 题不可回答（越界 6 题、敏感 2 题）；支持按 `category` 分类统计，管理员专属题用 `"admin": true` 单独走管理员检索。
- 指标定义：
  - **Recall@4**：期望来源是否出现在 Top-4 中；
  - **MRR**：期望来源排名的倒数均值；
  - **引用准确率**：Top-1 来源是否等于期望来源；
  - **拒答率**：不可回答的问题被判定为证据不足（`ok=False`）的比例；
  - **检索延迟**：单次 `search_documents_with_meta` 全链路耗时，预热后统计。

> 说明：知识库和评估集仍然不大，以下指标用于**回归对比和方案验证**，不应包装成通用 benchmark。

## 3. 评估结果

| 向量方案 | Recall@4 | MRR | 引用准确率 | 拒答率 | 平均检索延迟 | P50 | P95 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `local`（默认，离线哈希） | 1.0 | 0.9688 | 0.9375 | 0.75 | 18.90 ms | 17.84 ms | 25.71 ms |
| `bge`（bge-small-zh-v1.5） | 1.0 | **0.9844** | **0.9688** | **1.0** | 32.72 ms | 31.99 ms | 39.66 ms |

### 3.1 分类观察

- `local` 的短板集中在语义/多来源问题：
  - `faq` 引用准确率 0.6667、`approval` 0.75：多个文档都提到相似规则，纯词面容易把相邻主题排到第一；
  - `out_of_domain` 拒答率 0.8333、`sensitive` 0.5：「实验室可以养猫吗」「实验室门禁密码」与知识库共享部分词面，词面阈值无法判断语义无关。
- `bge` 把整体拒答率提升到 1.0，`out_of_domain` 和 `sensitive` 都达到 1.0；MRR/引用准确率也略升。
- 仍然存在的 1 个引用错误是 `approval` 类别中的“单级审核由哪些角色处理”：`approval_workflow.md` 和 `reservation_faq.md` 都包含答案，评估集只标注了前者，属于标签口径问题，不是检索完全失败。后续可以把评估集改成允许多个期望来源。

### 3.2 阈值校准

`RAG_MIN_VECTOR_SCORE=0.54` 是按 BGE + 40 题校准的：

- 可回答题目的 Top-1 向量分最低约 **0.55**；
- 不可回答题目的最高约 **0.53**；
- 0.54 取在两者之间。换 Embedding 模型、知识库或评估集后必须重新校准，不能把这个数字当成通用阈值。

### 3.3 延迟口径

- 表中延迟**不含**首次模型加载和首次 Chroma collection 同步（一次性成本，BGE 首次可达秒级）。
- 评估脚本在正式计时前执行一次“预热检索”，避免把冷启动算进单题延迟。
- BGE 的稳态检索约为 local 的 2 倍，但仍保持几十毫秒级；是否值得取决于语义拒答/排序准确率的业务价值。
- 本机是开发环境，数值用于横向对比，不代表生产容量。

## 4. 复现方式

```powershell
cd backend

# local（默认）
.\.venv\Scripts\python.exe scripts\eval_rag.py --markdown-out docs/rag-eval-local.md

# BGE（可选依赖 + 模型）
.\.venv\Scripts\python.exe -m pip install sentence-transformers
$env:RAG_PROVIDER="bge"
$env:HF_ENDPOINT="https://hf-mirror.com"   # 国内网络可选
.\.venv\Scripts\python.exe scripts\eval_rag.py --markdown-out docs/rag-eval-bge.md
```

输出 JSON（含逐题明细和分类指标）：

```powershell
.\.venv\Scripts\python.exe scripts\eval_rag.py --json
```

## 5. 局限与后续

- **没有生成侧 faithfulness 评估**：当前只有检索指标，没有判断“模型答案是否被引用证据支持”。本机网关 chat 模型返回 429（需实名认证/更高 RPM），无法运行 LLM-as-judge；不伪造指标。可用模型恢复后补 `question + answer + cited chunks` 的 judge 流程。
- **评估集仍偏小**：40 题、10 篇文档，指标用于回归和方案对比，不能说明开放域泛化能力。真实上线应扩到上百题，并加入多来源、多跳和权限边界样本。
- **`local` 不适合语义检索**：默认保留它是为了离线零依赖；对外表述 RAG 能力时应明确使用 BGE/API 向量，并引用本报告的对照结果。
- **BGE 未进入默认依赖**：`sentence-transformers` 体积大，未写入 `requirements.txt`，避免 CI/Docker 膨胀；生产要单独决定是否安装或改用 Embedding API。