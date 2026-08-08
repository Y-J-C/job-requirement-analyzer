# 第七阶段实施计划：岗位文件上传与异步文本解析

## 概览

本计划实现已批准的 [文件上传与解析规格](./file-upload-and-parsing-spec.md)。按依赖顺序先建立 MinIO 与安全解析基础，再建立 `SourceFile` 持久化队列，随后贯通上传 API、Worker、删除生命周期和前端双入口，最后以真实 PostgreSQL、MinIO 和三种格式做集成验证。

实现采用小步纵向切片。每个任务先写行为测试，再写最小实现；每个检查点保持文本粘贴和现有 DeepSeek 链路可用。

## 架构决策

- 表单入口分为文本和文件，但解析成功后统一写入 `JobPosting.original_text`，不建立两套 AI 流程。
- `ObjectStore` 协议隔离 S3 实现；业务层不直接依赖 boto3 客户端。
- MinIO 容器内部使用 9000/9001，宿主机使用 19000/19001，避免与用户曾运行的 namenode 9000 端口冲突。
- 上传校验采用分块读取、临时文件和 SHA-256；在校验完成前不创建岗位或对象。
- 文件格式检测与文本解析分层：上传时只做廉价结构校验，Worker 执行页数、解压和正文提取。
- `SourceFile` 自身携带队列租约和重试字段；解析任务优先于 AI 任务，但每轮只处理一项，保持 Worker 简单。
- 对象存储和数据库不能共享事务：创建失败时执行对象补偿删除；删除岗位时先删除对象，存储失败则保留数据库记录并返回可重试错误。
- 不开放原文件下载，不渲染 Markdown，不自动调用 DeepSeek。

## 依赖关系

```text
MinIO/配置
  ├─ ObjectStore 适配器
  └─ 安全文件检测
          └─ 格式解析器
                  └─ SourceFile 模型/迁移
                          ├─ 上传 API
                          ├─ 解析 Worker
                          └─ 删除生命周期
                                  └─ 前端双入口与状态恢复
                                          └─ 真实集成与冒烟验证
```

## 任务清单

### 任务 1：建立 MinIO 与受校验的存储配置

**说明：** 增加本地 MinIO 服务、S3 配置和必要 Python 依赖，不接业务路径。

**验收标准：**

- [ ] Docker Compose 可在 19000/19001 启动健康 MinIO，PostgreSQL 配置不受影响。
- [ ] S3 endpoint、bucket、region、access key、secret key 和文件限制来自环境配置，密钥不进入版本库。
- [ ] 配置拒绝非 HTTP(S) endpoint、空 bucket 和越界限制。

**验证：**

- [ ] `docker compose config`
- [ ] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_storage_config.py`
- [ ] `.\.venv\Scripts\python.exe -m pip check`

**依赖：** 无。

**可能修改：** `docker-compose.yml`、`.env.example`、`apps/api/pyproject.toml`、`apps/api/app/core/config.py`、`apps/api/tests/test_storage_config.py`。

**规模：** 中。

### 任务 2：实现 S3 对象存储适配器

**说明：** 定义最小 `ObjectStore` 协议，实现上传、读取和删除，并用内存假实现隔离业务测试。

**验收标准：**

- [ ] 业务层只依赖 `ObjectStore`，不导入 boto3 类型。
- [ ] S3 适配器可幂等创建 bucket，并映射为稳定的存储错误。
- [ ] 对象键由调用方生成，适配器不会使用或拼接原始文件名。

**验证：**

- [ ] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_object_storage.py`
- [ ] `.\.venv\Scripts\python.exe -m ruff check apps/api/app/storage apps/api/tests/test_object_storage.py`

**依赖：** 任务 1。

**可能修改：** `apps/api/app/storage/contracts.py`、`apps/api/app/storage/s3.py`、`apps/api/app/storage/dependencies.py`、`apps/api/tests/test_object_storage.py`。

**规模：** 中。

### 任务 3：实现上传字节的安全检测

**说明：** 分块限制大小、计算 SHA-256、清理显示文件名，并交叉校验扩展名、MIME、魔数和 DOCX 容器结构。

**验收标准：**

- [ ] PDF、Markdown、DOCX 的合法输入得到检测类型、大小和哈希。
- [ ] 类型伪造、NUL Markdown、危险 ZIP 结构和超过 10 MiB 的输入在写入对象存储前被拒绝。
- [ ] 原文件名不能影响对象键或逃逸路径。

**验证：**

- [ ] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_upload_validation.py`
- [ ] 边界样本包括扩展名/MIME/魔数三者不一致和 ZIP 解压限制。

**依赖：** 任务 1。

**可能修改：** `apps/api/app/parsing/errors.py`、`apps/api/app/parsing/validation.py`、`apps/api/tests/test_upload_validation.py`。

**规模：** 中。

### 任务 4：实现 PDF、Markdown、DOCX 纯文本解析器

**说明：** 通过统一协议选择解析器，输出经过长度和换行规范化的纯文本。

**验收标准：**

- [ ] 三种格式的有效样本能提取预期文本，Markdown 不转换 HTML。
- [ ] PDF 加密、超过 50 页、无文本层及损坏文档返回稳定领域错误。
- [ ] DOCX 提取段落和表格文本，不访问外部资源，输出不超过 100,000 字符。

**验证：**

- [ ] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_document_parsers.py`
- [ ] 固定样本内容匿名、最小且可人工审计。

**依赖：** 任务 3。

**可能修改：** `apps/api/app/parsing/contracts.py`、`apps/api/app/parsing/parsers.py`、`apps/api/app/parsing/registry.py`、`apps/api/tests/test_document_parsers.py`、`apps/api/tests/fixtures/documents/`。

**规模：** 中。

## 检查点 A：安全解析基础

- [ ] 任务 1–4 的测试通过。
- [ ] MinIO 健康，PostgreSQL 仍健康。
- [ ] 新依赖通过 `pip check` 和已知漏洞检查。
- [ ] 没有业务 API 行为变化，现有测试仍通过。

### 任务 5：建立 SourceFile 模型与迁移

**说明：** 添加文件元数据、解析状态和持久化租约字段，并约束解析中/失败岗位允许空原文。

**验收标准：**

- [ ] `source_files` 字段、枚举、唯一约束、检查约束和索引与规格一致。
- [ ] 迁移从当前 `2f9c3a6b7d10` 升级且不改变已有岗位数据。
- [ ] ORM `create_all` 测试和真实 PostgreSQL migration 均可用。

**验证：**

- [ ] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_source_file_model.py`
- [ ] `.\.venv\Scripts\python.exe -m alembic -c apps/api/alembic.ini upgrade head`
- [ ] `$env:RUN_DATABASE_TESTS='1'; .\.venv\Scripts\python.exe -m pytest apps/api/tests/integration`

**依赖：** 任务 3、4。

**可能修改：** `apps/api/app/models/source_file.py`、`apps/api/app/models/__init__.py`、`apps/api/app/models/job_posting.py`、`apps/api/migrations/versions/*_add_source_files.py`、`apps/api/tests/test_source_file_model.py`。

**规模：** 中。

### 任务 6：贯通安全上传 API

**说明：** 新增 multipart 创建岗位接口和源文件状态查询，在对象存储与数据库之间执行补偿逻辑。

**验收标准：**

- [ ] 上传合法文件返回 `201`、岗位 `extracting`、文件 `pending`，对象键不含原文件名。
- [ ] 非法输入返回稳定 4xx，存储失败返回 503，任何失败都不留下半成品岗位或对象。
- [ ] 文本 JSON 创建接口保持兼容，解析中或空原文岗位不能启动 AI。

**验证：**

- [ ] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_source_file_upload.py apps/api/tests/test_ai_analysis.py`

**依赖：** 任务 2、3、5。

**可能修改：** `apps/api/app/schemas/source_file.py`、`apps/api/app/services/source_file.py`、`apps/api/app/api/v1/jobs.py`、`apps/api/app/api/v1/__init__.py`、`apps/api/tests/test_source_file_upload.py`。

**规模：** 中。

### 任务 7：贯通持久化解析 Worker

**说明：** Worker 优先领取 SourceFile 任务，调用对象存储和解析器，并可靠切换岗位与文件状态。

**验收标准：**

- [ ] 解析成功写入原文并将岗位变为 `draft`；确定性错误直接失败且不创建 AI 任务。
- [ ] 存储瞬时失败有限重试；租约过期可恢复；并发领取不重复处理同一文件。
- [ ] 现有 AI `run_once` 测试兼容，文件队列不会破坏 DeepSeek 任务执行。

**验证：**

- [ ] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_source_file_worker.py apps/api/tests/test_analysis_worker.py`

**依赖：** 任务 2、4、5、6。

**可能修改：** `apps/api/app/services/source_file.py`、`apps/api/app/worker.py`、`apps/api/app/parsing/dependencies.py`、`apps/api/tests/test_source_file_worker.py`。

**规模：** 中。

### 任务 8：完成对象删除生命周期与状态诊断

**说明：** 删除文件岗位前清理对象；失败时保留数据库资源供重试，并让文件状态接口返回安全中文可映射信息。

**验收标准：**

- [ ] 删除文本岗位行为不变；删除文件岗位会删除 MinIO 对象和数据库记录。
- [ ] 对象删除失败返回 503 且数据库记录仍存在，不静默产生孤儿对象。
- [ ] 文件状态接口只暴露允许的元数据、状态和稳定错误码。

**验证：**

- [ ] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_source_file_lifecycle.py`

**依赖：** 任务 2、5、6。

**可能修改：** `apps/api/app/services/job_posting.py`、`apps/api/app/api/v1/jobs.py`、`apps/api/app/schemas/source_file.py`、`apps/api/tests/test_source_file_lifecycle.py`。

**规模：** 中。

## 检查点 B：后端完整链路

- [ ] 后端全量测试、ruff、compileall、pip check 通过。
- [ ] PostgreSQL 迁移位于 head，真实 MinIO 上传/解析/删除通过。
- [ ] 文本录入、AI 分析、确认和汇总回归通过。
- [ ] API/Worker 重启后待解析任务可恢复。

### 任务 9：实现前端文本/文件双入口

**说明：** 在同一岗位表单中提供互斥来源方式，并分别发送 JSON 或 multipart 请求。

**验收标准：**

- [ ] 默认文本模式保持原表单行为；文件模式只允许单文件并显示格式与限制。
- [ ] 客户端不手工设置 multipart `Content-Type`，由浏览器生成 boundary。
- [ ] 上传成功的 `extracting` 岗位立即进入列表，重复提交被禁用。

**验证：**

- [ ] `corepack pnpm --dir apps/web test -- JobPostingDashboard.test.tsx`
- [ ] `corepack pnpm --dir apps/web lint`

**依赖：** 任务 6。

**可能修改：** `apps/web/src/features/job-postings/types.ts`、`apps/web/src/features/job-postings/api.ts`、`apps/web/src/features/job-postings/JobPostingForm.tsx`、`apps/web/src/features/job-postings/JobPostingDashboard.tsx`、`apps/web/src/features/job-postings/JobPostingDashboard.test.tsx`。

**规模：** 中。

### 任务 10：实现解析状态恢复与错误展示

**说明：** 页面轮询 `extracting` 岗位，刷新后恢复；岗位卡片和审核页显示文件名、解析结果或中文错误。

**验收标准：**

- [ ] 上传后和页面刷新后都能从 `extracting` 自动更新为 `draft` 或 `failed`。
- [ ] 解析中不显示可用的 AI 分析动作；失败原因按稳定错误码显示中文，不展示内部堆栈。
- [ ] 解析成功后显示统一 `original_text`，用户可手动启动 DeepSeek。

**验证：**

- [ ] `corepack pnpm --dir apps/web test`
- [ ] `corepack pnpm --dir apps/web lint`
- [ ] `corepack pnpm --dir apps/web build`

**依赖：** 任务 6、7、9。

**可能修改：** `apps/web/src/features/job-postings/JobPostingDashboard.tsx`、`apps/web/src/features/job-postings/JobPostingList.tsx`、`apps/web/src/features/requirements/RequirementReviewDashboard.tsx`、相关前端测试。

**规模：** 中。

### 任务 11：真实基础设施与端到端验收

**说明：** 在 Docker PostgreSQL/MinIO 上完成三种格式集成测试和一次 Markdown 网页冒烟，并更新运行文档。

**验收标准：**

- [ ] PDF、Markdown、DOCX 在真实对象存储中完成上传、读取、解析和删除。
- [ ] 网页上传 Markdown 后可刷新恢复、检查文本、手动调用 DeepSeek、确认并进入汇总。
- [ ] README 包含 MinIO、端口、启动、限制、错误处理和图片/OCR 非目标。

**验证：**

- [ ] `docker compose ps`
- [ ] 后端、前端和集成测试全量通过。
- [ ] `git diff --check`、依赖漏洞检查和密钥扫描通过。

**依赖：** 任务 1–10。

**可能修改：** `apps/api/tests/integration/test_object_storage.py`、`apps/api/tests/integration/test_document_pipeline.py`、`README.md`、必要测试样本。

**规模：** 中。

## 检查点 C：第七阶段完成

- [ ] 规格中的全部验收标准有测试或真实验证证据。
- [ ] 代码审查覆盖正确性、可读性、架构、安全和性能。
- [ ] 所有阻塞发现已修复；非阻塞限制写入 README。
- [ ] 未经用户明确要求不执行 commit、push 或生产部署。

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| S3 写入成功但数据库创建失败 | 孤儿对象 | 捕获数据库失败并补偿删除；测试补偿路径 |
| 对象删除成功后数据库提交失败 | 岗位记录暂时指向缺失对象 | 删除接口仅用于本地单用户；记录通用失败并允许再次删除，生产前升级为 outbox/延迟删除 |
| PDF/DOCX 触发解析器高资源消耗 | Worker 阻塞或内存耗尽 | 上传大小、PDF 页数、ZIP 解压量/比例、文本长度和租约上限 |
| Worker 优先解析造成 AI 饥饿 | AI 延迟 | 每轮最多处理一个解析任务，下轮重新公平判断；如出现积压再引入配额，不预先复杂化 |
| MinIO 与其他本地容器端口冲突 | 无法启动 | 固定映射 19000/19001，endpoint 完全配置化 |
| 浏览器 MIME 不稳定 | 合法文件被误拒 | 对已知浏览器允许 octet-stream，但必须通过扩展名和文件结构校验 |
| Markdown 含 HTML/提示注入 | XSS 或模型操控 | 只作纯文本展示；React 自动转义；现有 LLM 提示注入与证据校验继续生效 |

## 开放问题

无。实现中若需要改变批准的格式、限制、存储方式、AI 触发策略或公开 API，将暂停并请求确认。
