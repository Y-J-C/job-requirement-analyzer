# 岗位门槛分析系统

将用户收集的招聘信息转换成可核验、可确认、可汇总的岗位准入条件。

当前支持通过文本、单个 PDF/Markdown/DOCX 文档或 1～10 张 PNG/JPEG/WebP 图片一次录入岗位。扫描版 PDF 会按页使用本地 OCR；所有文件在解析、OCR 和 AI 之前由 ClamAV 扫描。文件由 MinIO 私有保存，独立 Worker 处理后自动排队一次 AI 分析。用户补充并确认公司、岗位和指标后，可以勾选任意已确认岗位或全选，按所选集合查看覆盖率和原文证据。核心流程已有 Playwright 浏览器回归；AI 提取另有匿名 Golden Dataset、离线评分器和显式真实模型质量评测。

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
pnpm exec playwright install chromium
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

如果 `pnpm db:up` 提示无法连接 Docker API，请先启动 Docker Desktop。首次运行需要拉取 PostgreSQL、MinIO 和 ClamAV 镜像，并等待病毒库初始化；建议为 Docker 至少预留 4 GiB 内存。MinIO API 默认使用 `19000`，管理控制台使用 `19001`。ClamAV 仅绑定本机 `127.0.0.1:13310`，不要把该无认证端口暴露到局域网或公网。

### 单实例共享数据

项目没有内置登录，打开 Web 即可使用。每套部署共享一份 PostgreSQL 数据，适合个人或可信小团队在本机、家庭服务器或内网运行。Web 与 API 默认绑定本机；如果需要跨设备访问，应放在可信网络中。不要把无认证 API 直接暴露到公网；公开部署时请在反向代理层配置 HTTPS 和访问控制。

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
pnpm typecheck
pnpm test
pnpm build
pnpm test:e2e
```

### API 契约

FastAPI 生成的 OpenAPI 3.1 是前后端唯一接口契约。错误响应遵循 RFC 9457
`application/problem+json`，前端类型和客户端由 `openapi-typescript`、`openapi-fetch`
提供。修改路由或 Pydantic schema 后执行：

```powershell
pnpm api:contract:generate
pnpm api:contract:check
```

不要手工编辑 `packages/api-contract/openapi.json` 或
`apps/web/src/generated/api-schema.ts`。

PostgreSQL、MinIO 和 ClamAV 运行后，可以执行真实连接、文件管线与恶意文件扫描集成测试：

```powershell
pnpm test:api:integration
pnpm test:api:security-integration
```

运行包含 lint、单元测试、真实 PostgreSQL/MinIO 集成测试、生产构建和默认浏览器测试的完整本地门禁：

```powershell
pnpm verify
```

`pnpm test:e2e` 会检查 Docker、执行迁移，并以 `APP_ENV=e2e` 启动确定性分析器和 OCR。运行前请先完整停止 `pnpm dev`（包括无端口的 Worker）；脚本会拒绝复用已有 Worker，避免它抢占测试任务或误调用真实模型。测试数据使用唯一前缀并在结束时清理；失败截图、视频和 Trace 位于被 Git 忽略的 `test-results/`。默认套件不会调用 DeepSeek。需要显式验证真实模型时，确认本地 `.env` 已配置有效密钥后运行：

```powershell
pnpm test:e2e:deepseek
```

该命令会产生一次最小真实模型调用，可能产生费用。

### AI 提取质量评测

运行数据集结构、评分器、空结果契约和评测入口的离线测试：

```powershell
pnpm test:ai:quality
```

该命令不访问网络，也不读取或使用 DeepSeek 密钥。首批数据集包含 20 条匿名 JD，质量
阈值为：结构成功率与证据可追溯率 100%、无依据和禁止项命中率 0%、精确率至少 90%、
召回率至少 85%、类型准确率至少 90%、明确程度准确率至少 85%。

真实 DeepSeek V4 评测必须同时具备本地密钥和显式开关：

```powershell
$env:RUN_DEEPSEEK_EVAL='1'
pnpm eval:ai:deepseek
```

该命令最多评测 20 条样本，模型对单条非法输出最多重试一次，因此最多产生 40 次请求。
运行会产生费用，未经明确确认不要执行。脱敏报告写入被 Git 忽略的
`.data/ai-evaluation/`，不保存请求头、完整模型响应或岗位原文。

首轮 `deepseek-v4-flash + requirements-v2` 基线的安全与结构指标通过，但精确率 64.29%、
召回率 52.94%，未达到质量门槛。完整脱敏结论见
[docs/ai-quality-baseline-v1.md](./docs/ai-quality-baseline-v1.md)。离线优化现已准备为
`requirements-v3 + ai-quality-v2`：v1 保持不可变，v2 只增加四个经批准的语义等价名称，
提示词加强了原子拆分、资格约束和例外关系。真实 v2 复测的精确率为 72.22%、召回率为
76.47%，虽较 v1 提升但仍未达标；完整结论见
[docs/ai-quality-baseline-v2.md](./docs/ai-quality-baseline-v2.md)。当前运行契约已升级为
`requirements-v4`，用于同时提取岗位元数据；尚未完成对应的真实质量复测，因此不能把 v3
成绩视为 v4 成绩。AI 结果仍必须人工审核。

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
e2e/                      Playwright 浏览器测试、固定样本和测试支持代码
scripts/                  本地测试编排脚本
playwright.config.ts      浏览器、服务生命周期和失败产物配置
docker-compose.yml        PostgreSQL、MinIO 与 ClamAV 本地基础设施
```

## 当前范围

当前已经包含工程基线、单实例共享数据、目标岗位方向、三种来源统一录入、本地图片与扫描版 PDF OCR、上传文件恶意软件扫描、DeepSeek AI 提取、持久化任务 Worker、元数据补充、人工审核、失败重试、分析版本切换、选定岗位汇总和离线 AI 质量评测。MVP 实现证据和剩余差距见 [docs/mvp-acceptance-matrix.md](./docs/mvp-acceptance-matrix.md)。以下内容将在后续里程碑实现：

- 目标岗位方向编辑，以及要求拆分/合并的专用快捷操作。
- `requirements-v4` 的真实模型质量复测与持续优化。
- 生产部署、监控告警和费用限额。

## 参与贡献与安全

贡献流程见 [CONTRIBUTING.md](./CONTRIBUTING.md)。安全问题请按
[SECURITY.md](./SECURITY.md) 私下报告，不要在公开 Issue 中附带密钥、岗位原文或上传文件。

本项目采用 [Apache License 2.0](./LICENSE) 开源许可证。
