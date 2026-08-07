# 阶段一工程基线规格

## 目标

为岗位门槛分析系统建立一个可运行、可测试、可持续扩展的本地开发工程。阶段一只建设工程基础设施和健康检查，不实现岗位、要求、AI、文件上传、登录或多用户业务。

## 已确认假设

- 产品形态：Web 应用。
- 使用模式：第一版为单用户本地版本。
- 前端：Next.js、React、TypeScript。
- 后端：FastAPI、Python 3.12。
- 数据库：PostgreSQL，通过 Docker Compose 启动。
- 包管理：pnpm workspace。
- AI、Redis、对象存储、身份认证：不属于阶段一。

## 命令

在项目根目录执行：

```powershell
pnpm install
pnpm dev
pnpm lint
pnpm test
pnpm build
pnpm db:up
pnpm db:down
pnpm api:migrate
```

后端单独执行：

```powershell
.\.venv\Scripts\python.exe -m pytest apps/api/tests
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps/api --reload
```

## 项目结构

```text
apps/web/          Next.js 前端
apps/api/          FastAPI 后端
packages/          后续共享契约与 UI 包
docs/              产品规格和架构决策
e2e/               后续端到端测试
docker-compose.yml 本地基础设施
```

## 代码规范

- Python 使用 `snake_case`，TypeScript 使用 `camelCase`，React 组件使用 `PascalCase`。
- 外部输入在边界处验证；环境差异通过环境变量表达。
- 路由只处理 HTTP 边界，业务逻辑后续进入 service/domain 层。
- 不为尚未出现的业务场景提前设计抽象。

示例：

```python
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
```

## 测试策略

- 前端：Vitest + Testing Library，阶段一验证健康首页可渲染。
- 后端：pytest，验证存活检查响应；数据库就绪检查使用本地 PostgreSQL 做集成验证。
- 构建：Next.js 生产构建必须成功；Python 模块必须能导入。
- 阶段一不设覆盖率门槛，后续业务逻辑必须增加单元及集成测试。

## 边界

Always：

- 使用 `.env.example` 记录非敏感配置模板。
- 运行与变更相关的 lint、test 和 build。
- 数据库结构变化使用 Alembic 迁移。

Ask first：

- 更换技术栈或包管理器。
- 增加身份认证、AI、Redis、对象存储等基础设施。
- 改变公开 API、数据保留策略或多用户边界。

Never：

- 提交密钥或真实凭据。
- 覆盖岗位原文。
- 把 AI 自由文本直接写成正式结构化数据。
- 为通过检查而删除失败测试。

## 阶段一验收标准

- [x] 根目录存在统一的开发、检查、测试、构建和数据库命令。
- [x] `docker compose up -d` 能启动 PostgreSQL，并通过健康检查。
- [x] FastAPI 提供 `/health` 和 `/health/ready`。
- [x] `/health/ready` 实际执行数据库连接检查。
- [x] Next.js 首页能显示系统名称和前后端健康状态入口。
- [x] 前后端至少各有一项自动化测试。
- [x] 前端 lint、测试和生产构建通过。
- [x] 后端测试通过，Python 应用可导入。
- [x] README 包含从零启动步骤。

## 暂不处理

- TargetRole、JobPosting、RequirementItem 等业务模型。
- AI 分析、异步任务和模型供应商。
- PDF、DOCX、OCR 与对象存储。
- 登录、多用户、计费、部署和 CI。
