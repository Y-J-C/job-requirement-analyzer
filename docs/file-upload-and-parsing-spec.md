# 第七阶段规格：岗位文件上传与异步文本解析

## 目标

在保留“直接粘贴 JD 文本”工作流的同时，允许用户通过 PDF、Markdown 或 DOCX 创建岗位。文件先经过安全校验和持久化异步解析，解析出的纯文本统一写入 `JobPosting.original_text`，之后继续使用现有的 DeepSeek 分析、人工审核、版本切换和汇总链路。

成功标准：用户可以在同一个岗位表单中二选一地粘贴文本或上传文件；关闭或刷新页面不会中断解析；解析失败不会产生 AI 费用，并能显示可理解的失败原因。

## 已确认决策与假设

- 内容入口分开、下游数据统一：表单提供“粘贴文本”和“上传文件”两个互斥来源。
- 第七阶段支持 `.pdf`、`.md`、`.markdown`、`.docx`；图片和 OCR 延后。
- 扫描版或没有文本层的 PDF 返回“未检测到可解析文本”，不调用 OCR。
- 文件使用 S3 兼容接口存储；本地 Docker Compose 增加 MinIO，生产可替换为其他 S3 服务。
- 文件上传后自动进入持久化解析队列；解析成功后由用户手动启动 DeepSeek，避免自动产生费用。
- 保留现有 JSON 文本录入 API 和用户工作流，不改变已录入岗位。
- 每个新岗位本阶段只接收一个源文件，不实现重新上传、多个文件合并或原文件下载。
- 原文件随岗位保存；通过岗位删除接口删除岗位时，同步删除对象存储中的原文件。

## 技术栈

- API：FastAPI、同步 SQLAlchemy、PostgreSQL、Alembic。
- 队列：复用 PostgreSQL 持久化任务和独立 Worker，不增加 Redis/Celery。
- 对象存储：S3 兼容适配器，本地 MinIO。
- 解析器：PDF 使用 `pypdf`，DOCX 使用 `python-docx`，Markdown 使用严格 UTF-8 纯文本解析。
- 上传：FastAPI `UploadFile` 和 `python-multipart`，分块计算大小与 SHA-256，不把整个文件一次性读入内存。

实现前根据官方来源选择并锁定与 Python 3.12 兼容的依赖版本，不使用未经维护的解析包。

## 用户工作流

### 直接粘贴文本

沿用当前流程：填写岗位元数据和 JD 文本，保存后岗位为 `draft`，用户手动点击 DeepSeek 分析。

### 上传文件

1. 用户填写公司、岗位名称、招聘阶段等元数据，选择一个允许的文件。
2. API 分块校验文件大小、扩展名、声明 MIME、文件头和容器结构，计算 SHA-256，并以随机对象键写入 MinIO。
3. API 创建 `JobPosting(status=extracting, original_text="")` 和 `SourceFile(parse_status=pending)`。
4. 独立 Worker 使用租约领取解析任务，从对象存储读取文件并提取纯文本。
5. 解析成功后，在同一数据库事务中写入 `JobPosting.original_text`，将岗位设为 `draft`、文件设为 `succeeded`。
6. 页面轮询岗位和文件状态；成功后提示用户检查原文并手动启动 DeepSeek。
7. 解析失败时岗位设为 `failed`，保留稳定错误码和安全的中文提示，不创建分析任务。

```text
浏览器上传
  → API 安全校验与对象存储
  → PostgreSQL 解析任务
  → Worker 领取并解析
  → original_text
  → 用户手动启动 DeepSeek
```

## 数据模型

新增 `source_files`：

- `id`：UUID 主键。
- `job_posting_id`：岗位外键并加唯一约束，本阶段一岗一文件。
- `object_key`：服务端生成的随机对象键，不包含原文件名。
- `original_filename`：仅作为显示元数据，不参与路径拼接。
- `declared_mime_type`、`detected_media_type`。
- `size_bytes`、`sha256`。
- `parse_status`：`pending | running | succeeded | failed`。
- `parser_version`、`error_code`。
- `attempt_count`、`max_attempts`、`available_at`、`lease_expires_at`、`worker_id`。
- `started_at`、`completed_at`、`created_at`、`updated_at`。

同一岗位最多一个 `pending` 或 `running` 文件解析任务。`job_postings.original_text` 保持非空数据库列；解析期间使用空字符串，文件解析失败后也可保持空字符串，因此数据库约束只允许 `extracting` 或 `failed` 状态的岗位为空。现有 JSON 创建接口仍要求非空文本，AI 入队前再次要求非空文本。

## API

保留：

```text
POST /api/v1/target-roles/{role_id}/jobs
```

新增：

```text
POST /api/v1/target-roles/{role_id}/jobs/upload
GET  /api/v1/jobs/{job_id}/source-file
```

上传接口使用 `multipart/form-data`：

- `company_name`
- `job_title`
- `recruitment_stage`
- `city`，可选
- `source_url`，可选
- `file`

响应返回岗位和源文件状态。超限、类型不符和文件结构不合法使用稳定的 4xx 错误；存储不可用返回通用 503，不暴露对象存储内部信息。

`POST /jobs/{id}/analyze` 只允许 `original_text` 非空且文件解析成功的岗位进入 AI 队列。

## 文件安全与威胁模型

信任边界包括浏览器上传、Multipart 元数据、文件字节、对象存储、解析器输出和送入 LLM 的文本。

主要滥用场景及控制：

- 伪造扩展名/MIME：同时检查小写扩展名、声明 MIME、魔数和容器内部结构。
- 超大文件/资源耗尽：上传上限 10 MiB；PDF 上限 50 页；提取文本上限 100,000 字符。
- ZIP 炸弹 DOCX：限制 ZIP 条目数、累计解压大小和压缩比，校验 `[Content_Types].xml` 与 `word/document.xml`。
- 路径穿越：对象键只使用服务端 UUID；原文件名只存储去路径后的显示名。
- 恶意 Markdown/HTML：只按 UTF-8 纯文本读取，不渲染 Markdown HTML，不执行脚本或外部引用。
- 加密/损坏文件：拒绝并记录稳定错误码，不尝试绕过保护。
- 提示注入：解析文本继续作为不可信数据传给现有 DeepSeek 适配器；模型输出继续经过 Schema 和证据校验。
- 信息泄露：日志不记录完整文件内容、密钥、对象存储凭证或解析堆栈；API 只返回允许的元数据和稳定错误码。
- 恶意软件：本地单用户阶段不引入扫描引擎；生产部署前恶意文件扫描是上线阻塞项。

允许范围：

| 格式 | 扩展名 | 可接受声明 MIME | 必要结构校验 |
|---|---|---|---|
| PDF | `.pdf` | `application/pdf`、`application/octet-stream` | `%PDF-` 文件头、页数、未加密 |
| Markdown | `.md`、`.markdown` | `text/markdown`、`text/plain`、`application/octet-stream` | UTF-8、无 NUL 字节 |
| DOCX | `.docx` | Office Open XML MIME、`application/octet-stream` | ZIP 文件头、必要 OOXML 条目、解压限制 |

## 解析规则

- PDF：按页提取文本并用空行分隔；不保留页面脚本、附件或外部链接；无文本层则失败。
- Markdown：保留原始 Markdown 字符作为纯文本，统一换行符，不转换为 HTML。
- DOCX：提取正文段落和表格单元格文本；不执行宏、不拉取外部资源；`.docm` 不允许。
- 所有格式：清理 NUL、统一换行并去除首尾空白；禁止解析器补写文件中不存在的内容。

## Worker 与失败恢复

- Worker 每轮优先领取文件解析任务，再领取 AI 分析任务，防止解析任务依赖 API 进程。
- 使用 `FOR UPDATE SKIP LOCKED`、租约和最多 3 次尝试，保持与现有任务模型一致。
- 对象存储短暂不可用可重试；格式不支持、文件损坏、页数超限、无文本层等确定性错误直接失败。
- Worker 崩溃后租约到期任务可恢复；过期任务不会重复提交 AI。
- 解析成功的文本写入与状态切换在一个事务中完成。

稳定错误码至少包括：

- `file_too_large`
- `unsupported_file_type`
- `file_signature_mismatch`
- `invalid_file_structure`
- `pdf_page_limit_exceeded`
- `encrypted_document`
- `no_extractable_text`
- `extracted_text_too_large`
- `storage_unavailable`
- `document_parse_failed`

## 前端

- 岗位表单增加来源方式选择，默认“粘贴文本”。
- 选择文件时隐藏 JD 文本框，显示允许格式、10 MiB 和 PDF 50 页限制。
- 上传完成后岗位卡片显示“正在提取”；页面轮询直到 `draft` 或 `failed`。
- 解析成功后用户进入审核页查看提取原文，再手动点击 DeepSeek。
- 解析失败显示按稳定错误码映射的中文提示，不展示内部异常。
- 上传期间和解析期间禁止重复提交同一表单。

## 项目结构

```text
apps/api/app/
├─ storage/                 S3 协议、MinIO/S3 适配器与依赖构造
├─ parsing/                 解析协议、格式探测和 PDF/Markdown/DOCX 解析器
├─ models/source_file.py    文件元数据与持久化解析任务
├─ services/source_file.py  上传、领取、解析完成/失败和对象删除
└─ api/v1/source_files.py   上传与状态 HTTP 边界

apps/api/tests/
├─ fixtures/documents/      小型、匿名、可审计的解析样本
├─ test_document_parsers.py
├─ test_source_file_upload.py
└─ test_source_file_worker.py

apps/web/src/features/job-postings/
├─ JobPostingForm.tsx       文本/文件互斥表单
├─ api.ts                   JSON 与 multipart 请求
└─ *.test.tsx               上传和状态展示测试
```

## 代码风格

格式解析通过统一协议隔离，业务服务不根据扩展名直接导入第三方解析包：

```python
class DocumentParser(Protocol):
    media_type: str

    def parse(self, content: BinaryIO) -> str: ...
```

路由只处理 HTTP 边界，存储键生成、文件校验、状态机和补偿删除放入服务层。解析器只返回纯文本或稳定领域错误，不直接修改数据库。

## 测试策略

- 单元测试：每种格式成功解析；扩展名/MIME/文件头不一致；UTF-8 失败；PDF 无文本、加密、超页；DOCX ZIP 炸弹边界；文本长度上限。
- 服务测试：分块大小限制、SHA-256、随机对象键、存储失败补偿、岗位状态、确定性失败不重试、瞬时失败重试、租约恢复。
- API 测试：multipart 校验、未知岗位方向、解析中禁止 AI、稳定错误响应、删除岗位触发对象删除。
- 前端测试：来源方式互斥、文件限制提示、multipart 提交、状态轮询和中文失败提示。
- 集成测试：真实 PostgreSQL 迁移、真实 MinIO 上传/读取/删除、PDF/Markdown/DOCX 完整解析。
- 端到端冒烟：网页上传 Markdown，等待解析，人工启动 DeepSeek，确认要求并进入汇总。

## 命令

```powershell
docker compose up -d postgres minio
.\.venv\Scripts\python.exe -m alembic -c apps/api/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m pytest apps/api/tests
$env:RUN_DATABASE_TESTS='1'; .\.venv\Scripts\python.exe -m pytest apps/api/tests/integration
corepack pnpm --dir apps/web test
corepack pnpm --dir apps/web lint
corepack pnpm --dir apps/web build
```

## 边界

Always：服务端校验所有文件属性和字节；使用随机对象键；限制资源消耗；错误码稳定且不泄露内部信息；保留原始文件哈希；所有解析文本按不可信数据处理；修改后运行相关测试。

Ask first：改变 10 MiB/50 页限制；增加图片/OCR；开放文件下载；允许重新上传或多文件合并；引入生产恶意文件扫描服务；改变自动调用 AI 的费用策略。

Never：使用原始文件名拼接路径；只信任浏览器 MIME；把 Markdown 当 HTML 渲染；执行文档宏、脚本或外部引用；把对象存储凭证提交到 Git；解析失败后仍自动调用 AI。

## 验收标准

- 文本粘贴工作流保持兼容。
- PDF、Markdown、DOCX 可以通过网页上传，任务在 API/页面重启后仍可恢复。
- 三种格式的有效样本解析为可检查的 `original_text`，之后可手动启动 DeepSeek。
- 类型伪造、超限、损坏、加密、无文本层和危险 DOCX 被安全拒绝并显示可理解提示。
- 文件对象键不包含原始文件名；数据库保存大小、SHA-256、解析状态和稳定错误码。
- 同一文件解析任务不会被并发 Worker 重复领取；瞬时失败有限重试，租约过期可恢复。
- 删除岗位会删除数据库记录和 MinIO 对象；删除失败有明确记录，不静默遗留。
- PostgreSQL、MinIO 集成测试、后端测试、前端测试、lint 和生产构建全部通过。

## 非目标

- 图片、OCR、扫描 PDF 识别。
- 简历上传或个人能力分析。
- 多文件合并、重新上传、在线预览和原文件下载。
- 自动抓取来源 URL。
- 登录、多用户权限、生产部署和恶意软件扫描服务。

## 待确认

无。若你希望 PDF、Markdown、DOCX 分批交付，或希望解析成功后自动调用 DeepSeek，需要在实施前调整本规格。
