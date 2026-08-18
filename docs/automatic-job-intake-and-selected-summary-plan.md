# 岗位自动录入与选定岗位综合分析实施计划

## 概览

本计划实现已批准的
[岗位自动录入与选定岗位综合分析规格](./automatic-job-intake-and-selected-summary-spec.md)。
实施采用“先验证 OCR 与数据迁移，再贯通后端流水线，最后交付前端选择和 E2E”的顺序。
旧录入、旧单文件和全部已确认岗位汇总接口保持兼容；默认测试不会调用 DeepSeek。

## 架构决策

- OCR 采用 `rapidocr>=3.9,<4`、`onnxruntime>=1.20,<2` CPU 和 Pillow。RapidOCR 默认中英文、
  ONNX 跨平台、模型随 wheel 提供且为 Apache-2.0；先在当前 Python 3.12/Windows 环境做
  小规模验证，若安装、许可证或中文识别不满足要求则停止，不自动换引擎。
- 图片安全限制初始设为：1～10 张、每张不超过 10 MiB、单次合计不超过 50 MiB、每张不
  超过 40 MP、合计不超过 120 MP。限制集中配置，修改前需重新确认。
- `SourceFile` 改为岗位一对多并保存 `sequence_index`、`extracted_text`。各文件独立租约处理；
  最后一项成功时在行锁保护下按序合并原文并只创建一个初始分析运行。
- AI 契约升级为 `requirements-v4`，同一结构化响应返回可空公司、岗位、城市和指标列表。
  岗位已有的非空人工值优先，重新分析不覆盖已有元数据。
- 统一 intake 是新主入口；旧文字/单文件接口继续可用。旧接口不改变响应格式，避免破坏
  现有 E2E 和外部调用。
- 选定岗位汇总使用 `POST summary` 和请求体 UUID 列表；原 `GET summary` 保持全部已确认
  岗位语义。后端严格拒绝重复、跨方向、未确认或不存在的岗位。
- 页面分批加载全部岗位，选择状态只保存在 React 内存。综合结果在岗位方向页内展示，
  复用现有 `SummaryList`，不增加选择记录表或 URL 中的大量 UUID。

## 依赖关系

```text
OCR 可行性 ─┬─ 图片验证 ─┐
             └─ 数据迁移 ─┴─ 多源文件 Worker ── 统一 intake
AI v4 契约 ────────────────┘              └─ 元数据编辑/重试
选定集合汇总 API ────────────────────────── 前端选择与结果
全部后端与前端切片 ───────────────────────── E2E 与完整门禁
```

## 第一阶段：高风险基础

### 任务 1：验证并封装本地 OCR

**说明：** 先安装受约束依赖，用三个匿名固定图片验证中文、英文、数字、旋转方向和空图错误，
记录冷启动、热执行时间及包体积；业务代码只依赖 `ImageOcr` 协议。

**验收条件：**

- [x] Python 3.12/Windows 可重复安装并通过 `rapidocr check`。
- [x] 固定样本输出顺序稳定，空图返回稳定错误码，不访问网络 OCR 服务。
- [x] OCR 协议可用 Fake 实现，Worker 单元测试不加载真实模型。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_image_ocr.py -q`
- [x] `.\.venv\Scripts\rapidocr.exe check`

**依赖：** 无。失败则停止并修订计划。

**预计文件：** `apps/api/pyproject.toml`、`apps/api/app/parsing/contracts.py`、
`apps/api/app/parsing/ocr.py`、`apps/api/tests/test_image_ocr.py`、匿名图片 fixtures。

**规模：** 中。

**可行性记录（2026-08-08）：** Python 3.12.4 上安装 RapidOCR 3.9.2、ONNX Runtime
1.28.0、Pillow 12.3.0 成功，`pip check` 无冲突。匿名内存样本正确识别中文、英文数字及
180° 旋转文字；引擎初始化约 924 ms，单张约 1.3～1.9 秒，空图返回
`no_extractable_text`。主要运行时目录合计约 235 MiB。RapidOCR/OpenCV 为 Apache-2.0，
ONNX Runtime 为 MIT，Pillow 为 MIT-CMU；当前本地桌面部署接受该成本。

### 任务 2：建立图片上传安全边界

**说明：** 用失败测试定义 PNG/JPEG/WebP 文件头、数量、单项/合计字节、单项/合计像素、
损坏文件及 EXIF 方向处理，不依赖浏览器 MIME 声明。

**验收条件：**

- [x] 合法图片保留提交顺序；混合文档、伪扩展名、解压炸弹和超限请求均在存储前拒绝。
- [x] 错误码稳定且不包含本地路径或文件内容。
- [x] PDF、Markdown、DOCX 既有验证不回归。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_upload_validation.py -q`
- [x] `.\.venv\Scripts\python.exe -m ruff check apps/api/app/parsing apps/api/tests/test_upload_validation.py`

**依赖：** 任务 1。

**预计文件：** `apps/api/app/core/config.py`、`apps/api/app/parsing/validation.py`、
`apps/api/tests/test_upload_validation.py`、`.env.example`。

**规模：** 中。

### 任务 3：迁移为多源文件和可空元数据

**说明：** 新增 Alembic 迁移，解除 `SourceFile.job_posting_id` 唯一约束，增加顺序和提取文本，
并允许处理期间公司/岗位为空。现有记录顺序迁移为 0，已有成功文件不要求回填提取文本。

**验收条件：**

- [x] 迁移前已有岗位、分析和对象键在升级后完整保留。
- [x] 同岗位顺序唯一；不同岗位可各自使用顺序 0。
- [x] 已确认岗位仍必须具备非空公司和岗位名称，由服务层确认规则保证。

**验证：**

- [x] `pnpm api:migrate`
- [x] `pnpm test:api:integration`

**依赖：** 无，可与任务 1 的调查并行，实际合并顺序在任务 1 之后。

**预计文件：** 新 Alembic migration、`models/job_posting.py`、`models/source_file.py`、
`tests/test_source_file_model.py`、迁移集成测试。

**规模：** 中。

## 检查点一：基础可行性

- [x] OCR 在目标环境可安装、可离线运行且资源开销已记录。
- [x] 图片安全边界在写入 MinIO 前生效。
- [x] 迁移在真实 PostgreSQL 上通过且现有数据无损。
- [x] `pnpm lint:api && pnpm test:api` 通过。

## 第二阶段：一次提交、一次分析

### 任务 4：定义 AI 元数据与指标联合契约 v4

**说明：** 先扩展 MockTransport 失败测试，再让一次 JSON 响应返回可空元数据及现有指标。
提示词要求无依据时返回 null，保留注入防护、证据校验、空指标和有限重试。

**验收条件：**

- [x] `PROMPT_VERSION == "requirements-v4"`，请求参数和模型名称不变。
- [x] 公司、岗位和城市没有证据时为 null；指标证据继续逐字可追溯。
- [x] v1/v2 质量数据集和评分阈值不被修改。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_deepseek_analyzer.py apps/api/tests/test_ai_evaluation.py -q`

**依赖：** 检查点一。

**预计文件：** `apps/api/app/ai/contracts.py`、`apps/api/app/ai/deepseek.py`、
`apps/api/tests/test_deepseek_analyzer.py`、匿名元数据 fixture。

**规模：** 中。

### 任务 5：原子保存 AI 元数据和指标

**说明：** Worker 在模型响应完整通过后一次事务写入元数据和 RequirementItem；已有非空值
不被模型覆盖，失败继续保持无半成品语义。

**验收条件：**

- [x] 一次成功运行同时保存可用元数据和全部指标。
- [x] 用户已有值优先；模型 null 不覆盖；失败不写入元数据或指标。
- [x] 元数据缺失的岗位进入待审核但不能整份确认。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_ai_analysis.py apps/api/tests/test_requirement_review.py -q`

**依赖：** 任务 4。

**预计文件：** `apps/api/app/services/analysis.py`、`apps/api/app/services/requirement_review.py`、
`apps/api/tests/test_ai_analysis.py`、`apps/api/tests/test_requirement_review.py`。

**规模：** 中。

### 任务 6：实现多文件解析/OCR汇合与自动排队

**说明：** 每个源文件独立解析并保存文本；最后一个文件完成时锁定岗位和文件集合，按
`sequence_index` 合并并创建唯一初始分析运行。任一最终失败使岗位失败且不分析。

**验收条件：**

- [x] 1～10 张图片乱序完成时仍按上传顺序合并。
- [x] 并发完成、Worker 重启和租约恢复不会创建重复分析运行。
- [x] 文档解析成功后同样自动排队；删除岗位清理全部对象。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_source_file_worker.py apps/api/tests/test_analysis_worker.py -q`
- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/integration/test_document_pipeline.py -q`

**依赖：** 任务 1、3、4。

**预计文件：** `apps/api/app/services/source_file.py`、`apps/api/app/worker.py`、
`apps/api/tests/test_source_file_worker.py`、`apps/api/tests/test_analysis_worker.py`、集成测试。

**规模：** 中。

### 任务 7：交付统一 intake API

**说明：** 新服务以一个事务创建岗位和有序源文件，存储部分失败时回滚数据库并清理已上传
对象；文字来源直接建立一次分析运行。旧创建和上传路由保持原行为。

**验收条件：**

- [x] 三种互斥来源的合法请求均返回岗位、源文件列表和排队状态。
- [x] 可选人工公司/岗位值保留；文件批量失败无孤立对象或半成品岗位。
- [x] 一次提交最多产生一个岗位和一个初始分析运行。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_job_intake.py -q`
- [x] `pnpm test:api:integration`

**依赖：** 任务 2、3、6。

**预计文件：** `apps/api/app/schemas/job_intake.py`、`apps/api/app/services/job_intake.py`、
`apps/api/app/api/v1/jobs.py`、`apps/api/tests/test_job_intake.py`。

**规模：** 中。

### 任务 8：增加元数据修改和失败重试

**说明：** PATCH 只更新允许的元数据；统一重试入口根据失败阶段重新排队源文件或分析，
不能覆盖已确认结果或同时创建多个任务。

**验收条件：**

- [x] 合法元数据可修改，空公司/岗位不能完成确认。
- [x] 可重试失败恢复到正确队列；运行中或已确认请求返回冲突。
- [x] 原文、源文件和指标不能经 PATCH 被覆盖。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_job_postings.py apps/api/tests/test_job_retry.py -q`

**依赖：** 任务 5、7。

**预计文件：** `apps/api/app/schemas/job_posting.py`、`apps/api/app/services/job_posting.py`、
`apps/api/app/api/v1/jobs.py`、相关两组测试。

**规模：** 中。

## 检查点二：后端主流程

- [x] 文字、文档和多图片均能一次提交后自动进入待审核。
- [x] 每个岗位只有一个初始分析运行，错误路径没有半成品或孤立对象。
- [x] 旧 API、Worker 租约、删除生命周期和默认 AI 质量测试不回归。
- [x] `pnpm lint:api && pnpm test:api && pnpm test:api:integration` 通过。

## 第三阶段：选定岗位综合分析

### 任务 9：实现选定集合汇总 API

**说明：** 在现有确定性聚合服务上增加显式岗位集合过滤，覆盖率分母固定为选中数量；保留
原 GET 行为并复用同一聚合核心。

**验收条件：**

- [x] 选择第 1/3 个岗位时，第 2 个岗位的指标和证据完全不出现。
- [x] 重复、跨方向、不存在、未确认、少于 2 或超过 500 个 ID 明确拒绝。
- [x] 响应选中数量/ID、覆盖率和证据分母一致，GET 旧测试不变。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_summary.py -q`

**依赖：** 检查点二。

**预计文件：** `apps/api/app/schemas/summary.py`、`apps/api/app/services/summary.py`、
`apps/api/app/api/v1/summary.py`、`apps/api/tests/test_summary.py`。

**规模：** 中。

### 任务 10：改造三种来源录入界面

**说明：** 表单以来源为主，公司/岗位变为可选提示；图片支持有序多选和提交前限制。前端
调用统一 intake，不删除旧客户端函数。

**验收条件：**

- [x] 文字、文档和图片入口清晰互斥；图片数量、顺序和错误提示准确。
- [x] 提交成功立即出现岗位占位卡和处理状态，不需要“开始分析”。
- [x] multipart 字段与后端契约一致，浏览器自行设置 boundary。

**验证：**

- [x] `pnpm --dir apps/web test -- JobPostingDashboard.test.tsx`
- [x] `pnpm --dir apps/web lint`

**依赖：** 任务 7。

**预计文件：** `features/job-postings/types.ts`、`api.ts`、`JobPostingForm.tsx`、
`JobPostingDashboard.tsx`、对应测试。

**规模：** 中。

### 任务 11：交付状态、元数据编辑和全部岗位加载

**说明：** 页面分批取回全部岗位，轮询解析/分析状态；待审核页提供元数据编辑，失败卡提供
重试。状态文案不把 OCR、解析和 AI 失败混为一类。

**验收条件：**

- [x] 超过一页的岗位仍全部可达且顺序稳定。
- [x] 元数据待补充、处理进度、失败原因和重试动作均可访问。
- [x] 修改元数据不会重新分析或覆盖已审核指标。

**验证：**

- [x] `pnpm --dir apps/web test -- JobPostingDashboard.test.tsx RequirementReviewDashboard.test.tsx`

**依赖：** 任务 8、10。

**预计文件：** `features/job-postings/api.ts`、`JobPostingDashboard.tsx`、`JobPostingList.tsx`、
`features/requirements/RequirementReviewDashboard.tsx`、对应测试。

**规模：** 中。

### 任务 12：交付岗位选择、全选和选中结果

**说明：** 岗位卡增加受控复选框；全选只包含可汇总岗位，按钮提交显式 ID 并在同页渲染
结果。结果复用现有汇总列表，选择变化后旧结果标记为过期或清空。

**验收条件：**

- [x] 单选、全选、取消全选和禁用原因符合规格，选择数量实时显示。
- [x] 少于 2 个时不能提交；服务端错误可恢复且不丢失选择。
- [x] 页面只展示本次选中集合的数量、覆盖率和证据。

**验证：**

- [x] `pnpm --dir apps/web test -- JobPostingDashboard.test.tsx SummaryDashboard.test.tsx`

**依赖：** 任务 9、11。

**预计文件：** `features/job-postings/JobPostingList.tsx`、`JobPostingDashboard.tsx`、
`features/summary/api.ts`、`SelectedSummaryPanel.tsx`、对应测试。

**规模：** 中。

## 检查点三：用户主流程

- [x] 页面能录入、观察处理、修正、确认、选择并汇总，不需要隐藏操作。
- [x] “全选”与后端实际样本分母完全一致。
- [x] 旧确认汇总页面继续工作。
- [x] `pnpm lint && pnpm test && pnpm build` 通过。

## 第四阶段：端到端与交付

### 任务 13：增加真实基础设施 E2E

**说明：** 用假 Analyzer/Fake OCR 的确定性环境覆盖文字自动分析、多图片按序合并，以及录入
三个岗位后只选择第一个和第三个汇总；上传对象和测试数据在结束时清理。

**验收条件：**

- [x] 三条浏览器主流程通过且能发现重复分析、顺序错误或选择泄漏。
- [x] 失败路径覆盖伪图片、未确认岗位不可选和重试提示。
- [x] 默认 E2E 不访问 DeepSeek，不保留上传文件或数据库记录。

**验证：**

- [x] `pnpm test:e2e`

**依赖：** 检查点三。

**预计文件：** `e2e/tests/job-auto-intake.spec.ts`、`e2e/tests/selected-summary.spec.ts`、
匿名图片 fixtures、必要的 E2E helper。

**规模：** 中。

### 任务 14：完整回归、审查和文档收口

**说明：** 更新 README、验收矩阵和运行说明，执行全门禁与五轴代码审查；检查迁移、依赖、
密钥、上传文件和 OCR 模型的版本库边界。

**验收条件：**

- [x] `pnpm verify` 通过，真实 DeepSeek 用例仍默认跳过。
- [x] 依赖许可证、模型来源、OCR 资源开销和已知准确率限制有记录。
- [x] Git 不包含密钥、真实岗位、上传文件、运行报告或临时 OCR 输出。

**验证：**

- [x] `pnpm verify`
- [x] `git diff --check`、候选文件密钥扫描、上传对象清理检查。

**依赖：** 任务 13。

**预计文件：** `README.md`、`docs/mvp-acceptance-matrix.md`、本计划及必要运维文档。

**规模：** 小。

## 最终检查点

- [x] 规格全部成功标准具有自动化或浏览器证据。
- [x] 旧数据和公开接口兼容，数据库迁移可重复执行。
- [x] 自动分析不绕过人工确认，选定汇总不混入未选岗位。
- [x] OCR 和 DeepSeek 失败均可诊断、可恢复且不会产生半成品。
- [x] 完整验证和代码审查无阻塞问题。

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| OCR 依赖安装或包体积不可接受 | 阻塞图片能力 | 第一任务先验证，失败停止，不污染后续架构 |
| 多文件并发完成创建重复分析 | 重复费用和数据版本 | 行锁、状态 CAS、分析运行唯一活动约束和并发测试 |
| 大体积或高像素图片导致内存压力 | Worker 不稳定 | 单项、合计字节与像素双限制，存储前拒绝 |
| OCR 顺序变化导致证据错位 | 指标不可追溯 | 持久化顺序、固定分隔符、乱序完成测试 |
| AI 元数据覆盖用户修改 | 数据丢失 | 非空已有值优先，PATCH 与分析事务测试 |
| 全选与实际汇总集合不一致 | 覆盖率误导 | 提交显式 ID、服务端全量校验、响应回显 ID |
| 大范围改动与第九阶段未提交变更混合 | 审查困难 | 逐任务最小 diff，检查点验证，不覆盖现有改动 |

## 开放问题

无产品阻塞问题。批准本计划同时表示批准安装受约束的 RapidOCR、ONNX Runtime、Pillow
及其必要传递依赖；若第一检查点发现包体、许可证或兼容性超出上述判断，将停止并重新报告。
