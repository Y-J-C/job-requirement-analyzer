# 岗位门槛分析系统

将用户收集的招聘信息转换成可核验、可确认、可汇总的岗位准入条件。

当前已完成第七阶段：可以创建目标岗位方向，通过粘贴文本或上传 PDF、Markdown、DOCX 录入岗位；文件由 MinIO 保存并通过独立 Worker 持久化解析。解析完成后可手动启动 DeepSeek 提取、人工审核确认，并按岗位去重查看覆盖率、分类筛选和回溯原文证据。

完整产品边界见 [README-岗位门槛分析系统.md](./README-岗位门槛分析系统.md)。AI 契约见 [docs/deepseek-analysis-slice-spec.md](./docs/deepseek-analysis-slice-spec.md)，持久化任务与版本切换见 [docs/durable-analysis-worker-spec.md](./docs/durable-analysis-worker-spec.md)，其他已完成切片规格位于 [docs](./docs)。

## 环境要求

- Node.js 24（最低版本以 Next.js 要求为准）
- pnpm 11
- Python 3.12
- Docker Desktop

## 首次安装（Windows PowerShell）

```powershell
Copy-Item .env.example .env
pnpm install
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\apps\api[dev]"
pnpm db:up
pnpm api:migrate
```

### 配置 DeepSeek

先在 DeepSeek 控制台创建一枚未暴露的新密钥，再只把它写入本地 `.env`（该文件已被 Git 忽略）：

```dotenv
DEEPSEEK_API_KEY=替换为新密钥
```

不要把真实密钥写入 `.env.example`、源码、提交记录或聊天消息。默认使用官方 `https://api.deepseek.com` 和 `deepseek-v4-flash`；如需更高质量，可在 `.env` 中改为 `deepseek-v4-pro`。结构化提取会显式关闭 V4 默认思考模式，其余超时、输出长度与有限重试参数可参考 `.env.example`。

如果 `pnpm db:up` 提示无法连接 Docker API，请先启动 Docker Desktop。首次运行需要拉取 PostgreSQL 和 MinIO 镜像。MinIO API 默认使用 `19000`，管理控制台使用 `19001`。

## 本地开发

```powershell
pnpm dev
```

默认入口：

- Web：http://localhost:3001
- API 存活检查：http://localhost:8000/health
- API 数据库就绪检查：http://localhost:8000/health/ready
- OpenAPI 文档：http://localhost:8000/docs

也可以分别启动：

```powershell
pnpm dev:web
pnpm dev:api
pnpm dev:worker
```

## 验证命令

```powershell
pnpm lint
pnpm test
pnpm build
```

PostgreSQL 和 MinIO 运行后，可以执行真实连接与文件管线集成测试：

```powershell
pnpm test:api:integration
```

常用数据库命令：

```powershell
pnpm db:up
pnpm db:logs
pnpm db:down
pnpm api:migrate
```

## 项目结构

```text
apps/
├─ web/                   Next.js 前端
└─ api/                   FastAPI 后端、测试和 Alembic
packages/                 后续共享契约与 UI 包
docs/                     工程规格和架构决策
e2e/                      后续端到端测试
docker-compose.yml        PostgreSQL 与 MinIO 本地基础设施
```

## 当前范围

当前已经包含工程基线、目标岗位方向、文本与文件录入、PDF/Markdown/DOCX 异步解析、DeepSeek AI 提取、持久化任务 Worker、人工审核、分析版本切换和已确认岗位汇总。以下内容将在后续里程碑实现：

- 图片、OCR、扫描版 PDF 识别和恶意文件扫描服务。
- 登录和多用户能力。
