# 第九阶段实施计划：AI 提取质量评测与 MVP 验收收口

## 概览

本计划实现已批准的 `docs/ai-quality-evaluation-spec.md`。实施顺序为“数据契约 → 确定性
评分 → 空结果业务闭环 → 真实模型评测入口 → MVP 证据收口”。默认开发和验证全程离线；
只有最终真实 DeepSeek V4 基线需要用户再次授权费用。

## 架构决策

- Golden Dataset 采用仓库内版本化 JSON，Pydantic 负责加载与结构校验，不引入评测框架。
- 评分器是纯函数，只依赖期望项与预测项；真实模型适配器只负责产生预测结果。
- 匹配采用“可接受规范名称 + 原文片段关系”的确定性一对一规则，不使用另一个模型裁判。
- 空数组契约将提示词从 `requirements-v1` 升为 `requirements-v2`；这是一次明确的契约变更，
  不包含基于评测分数的提示词调优。
- 真实评测 CLI 直接调用现有适配器，并通过受控 HTTP 客户端记录耗时和响应 `usage`；不把
  评测元数据加入生产数据库或公开 API。
- `.data/ai-evaluation/` 保存本地报告并继续由 Git 忽略；版本库只保存匿名样本和评测代码。

## 任务列表

### 任务 1：定义数据集契约并建立首批样本（已完成）

**说明：** 为评测样本、期望要求、禁止名称和场景标签建立严格模型，编写至少 20 条匿名
JD，先确保标注自身合法、完整且可追溯。

**验收条件：**

- [x] 样本 ID 唯一，至少 20 条，覆盖规格要求的 10 类场景。
- [x] 每条期望证据可在对应原文中定位，可接受规范名称非空，枚举值合法。
- [x] 包含至少一个零要求样本和至少两个提示注入样本。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_ai_evaluation.py -k dataset`
- [x] 人工抽查复合要求、结构化门槛、模糊表述和提示注入样本。

**依赖：** 无。

**预计文件：**

- `apps/api/app/ai/evaluation.py`
- `apps/api/tests/fixtures/ai-quality-v1.json`
- `apps/api/tests/test_ai_evaluation.py`

**规模：** 中。

### 任务 2：实现确定性匹配、计分和阈值判断（已完成）

**说明：** 使用纯函数实现规范化、一对一匹配、微平均指标、禁止项检查及阈值结果，避免
评分器本身成为不可验证的黑盒。

**验收条件：**

- [x] 完全匹配、同义名称、片段证据、漏提、误报、错分和一对一消费规则结果正确。
- [x] 零期望/零预测、零期望/有预测等空分母场景不会除零或虚报通过。
- [x] 阈值失败返回具体指标与失败样本 ID，不包含完整原文。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_ai_evaluation.py -k "scoring or threshold"`
- [x] `pnpm lint:api`

**依赖：** 任务 1。

**预计文件：**

- `apps/api/app/ai/evaluation.py`
- `apps/api/tests/test_ai_evaluation.py`

**规模：** 中。

## 检查点一：离线评测内核

- [x] 数据集结构和场景覆盖稳定通过。
- [x] 评分器全部分支由离线测试证明。
- [x] 测试期间没有网络请求或密钥读取。

### 任务 3：允许空要求分析在后端成功完成（已完成）

**说明：** 先增加失败测试，再放宽结果契约、更新 DeepSeek 提示词和版本，证明 Worker 对
空数组执行成功事务且不会生成虚假 RequirementItem。

**验收条件：**

- [x] `AnalyzeJobResult.requirements` 接受 0–100 条，非空结果契约保持兼容。
- [x] `requirements-v2` 明确要求无候选人准入条件时返回空数组且不得编造。
- [x] 空结果使 run 为 `succeeded`、岗位为 `review_required`、要求列表为空；直接确认仍为
  `409`。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_deepseek_analyzer.py apps/api/tests/test_ai_analysis.py apps/api/tests/test_requirement_review.py`
- [x] `pnpm lint:api`

**依赖：** 任务 1。

**预计文件：**

- `apps/api/app/ai/contracts.py`
- `apps/api/app/ai/deepseek.py`
- `apps/api/tests/test_deepseek_analyzer.py`
- `apps/api/tests/test_ai_analysis.py`

**规模：** 中。

### 任务 4：完成空结果的前端人工补充引导（已完成）

**说明：** 分析成功但返回零条时展示稳定提示，保留新增要求表单，并确保失败提示和正常
非空结果不受影响。

**验收条件：**

- [x] 页面显示“未提取到明确要求，请核对原文并手工新增”。
- [x] 页面不显示“AI 提取失败”，确认按钮保持禁用，手工新增入口可用。
- [x] 刷新后加载 `review_required + 0 items` 仍能恢复相同状态。

**验证：**

- [x] `pnpm --dir apps/web test -- RequirementReviewDashboard.test.tsx`
- [x] `pnpm lint:web`

**依赖：** 任务 3。

**预计文件：**

- `apps/web/src/features/requirements/RequirementReviewDashboard.tsx`
- `apps/web/src/features/requirements/RequirementReviewDashboard.test.tsx`

**规模：** 小。

## 检查点二：零要求业务闭环

- [x] 后端、Worker 和前端对空结果的语义一致。
- [x] 现有非空分析、人工编辑、确认和汇总测试不回归。
- [x] 不修改数据库结构或公开 HTTP 路径。

### 任务 5：实现受控的真实 DeepSeek 评测命令（已完成）

**说明：** 增加 CLI，加载数据集并逐条调用现有 DeepSeek 适配器，汇总评分、耗时和 Token
用量。缺少双重条件时在创建 HTTP 请求前拒绝运行。

**验收条件：**

- [x] 只有 `RUN_DEEPSEEK_EVAL=1` 且本地密钥非空时才允许真实请求。
- [x] 每次最多评测 20 条；单样本沿用既有超时和最多一次输出重试，不自动重跑全量。
- [x] 报告只包含版本、指标、阈值、耗时、Token 汇总、稳定错误和失败样本 ID，并根据
  阈值返回退出码。

**验证：**

- [x] 无开关、无密钥测试证明请求数为 0。
- [x] MockTransport 测试证明 20 条上限、usage 汇总、脱敏报告和失败退出码。
- [x] 本任务不执行真实模型评测。

**依赖：** 任务 2、任务 3。

**预计文件：**

- `apps/api/app/ai/evaluate_deepseek.py`
- `apps/api/tests/test_ai_evaluation_cli.py`
- `package.json`

**规模：** 中。

### 任务 6：接入离线质量命令并建立 MVP 证据矩阵（已完成）

**说明：** 增加根目录命令和文档，将产品基线中的验收项映射到具体页面、API 和测试，
明确标记已实现、部分实现与未实现，修复当前基线文档状态滞后问题。

**验收条件：**

- [x] `pnpm test:ai:quality` 只运行离线质量套件，断网环境可通过。
- [x] README 说明两个命令、费用边界、报告位置和质量阈值。
- [x] MVP 矩阵每项包含状态和证据，未实现项不得被标为完成。

**验证：**

- [x] `pnpm test:ai:quality`
- [x] `git diff --check`
- [x] 搜索仓库确认无密钥和本地评测报告。

**依赖：** 任务 1、任务 2、任务 5。

**预计文件：**

- `package.json`
- `README.md`
- `docs/mvp-acceptance-matrix.md`

**规模：** 中。

## 检查点三：离线交付完成

- [x] `pnpm lint`、`pnpm test`、`pnpm build`、`pnpm test:ai:quality` 通过。
- [x] `pnpm verify` 和默认 E2E 仍不请求 DeepSeek。
- [x] 真实评测命令的拒绝路径与 MockTransport 路径通过。
- [x] 向用户报告预计最多 20 个样本、最多 40 次请求的费用边界，并等待授权。

### 任务 7：经授权建立首轮 DeepSeek V4 基线（已完成，质量未达标）

**说明：** 用户再次明确授权后运行一次真实评测，检查报告脱敏、阈值和失败样本。该任务
只记录事实，不在同一任务中调整提示词、阈值或模型。

**验收条件：**

- [x] 运行使用当前 `.env` 模型且不输出密钥或请求头。
- [x] 报告包含 20 条样本的完整聚合指标、Token、耗时和失败样本 ID。
- [x] 达标则记录基线；未达标则保留原报告并提出独立优化方案。

**验证：**

- [x] `$env:RUN_DEEPSEEK_EVAL='1'; pnpm eval:ai:deepseek`
- [x] 确认 `.data/ai-evaluation/` 报告未进入 Git 状态。
- [x] 真实运行后再次执行密钥扫描和 `git diff --check`。

**依赖：** 检查点三、用户费用授权。

**预计文件：** 无版本控制文件；报告写入 `.data/ai-evaluation/`。

**规模：** 小。

## 最终检查点

- [x] 规格中的全部离线验收条件有自动化证据。
- [x] 真实评测已获授权并如实报告，或明确记录尚未运行的原因。
- [x] 现有测试数量不减少，默认质量门禁不产生模型费用。
- [x] 工作区不包含密钥、真实用户 JD、完整模型响应或本地评测报告。

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| Golden 标注本身错误 | 指标失真 | 证据定位自动校验，复杂样本人工复核，数据集版本化 |
| 合理同义词被判错 | 精确率虚低 | 每个期望项允许多个明确列出的规范名称，不做开放语义匹配 |
| 证据片段粒度不同 | 合理结果漏配 | 允许双方连续片段包含关系，名称仍须命中 |
| 真实模型具有波动 | 基线偶发变化 | temperature=0、固定提示/数据版本，真实评测不进入默认门禁 |
| 评测产生意外费用 | 费用扩大 | 显式开关、20 条上限、有限重试、运行前再次授权 |
| 报告泄露文本或密钥 | 安全风险 | 只记录匿名失败 ID和规范名称，报告目录忽略，完成后扫描 |
| 空结果被误当系统故障 | 用户无法继续 | Worker 明确成功状态，前端稳定提示并保留手工新增入口 |

## 开放问题

无阻塞问题。任务 7 的真实调用需要在离线实现完成后由用户再次明确授权。
