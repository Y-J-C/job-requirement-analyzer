# 贡献指南

感谢你参与岗位门槛分析系统。提交改动前，请先阅读 `README.md`、根目录 `AGENTS.md`，以及所修改目录中的附加说明。

## 本地环境

项目需要 Node.js 24、pnpm 11、Python 3.12 和 Docker Desktop。首次安装：

```powershell
Copy-Item .env.example .env
pnpm install --frozen-lockfile
pnpm exec playwright install chromium
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\apps\api[dev]"
pnpm db:up
pnpm api:migrate
```

使用 `pnpm dev` 启动 Web（`:3001`）、API（`:8000`）和 Worker。不要把真实密钥、岗位文件或本地 `.env` 提交到仓库。

## 修改约定

- TypeScript 使用两空格缩进，Python 使用四空格；遵循 ESLint 与 Ruff。
- React 组件使用 `PascalCase`，TypeScript 变量使用 `camelCase`，Python 使用 `snake_case`。
- 数据库变更必须新增 Alembic 迁移，不要修改已应用迁移。
- API 以 FastAPI OpenAPI 3.1 为唯一契约；修改路由或 Schema 后运行 `pnpm api:contract:generate`。
- 行为变化先增加回归测试。不要在同一改动中顺带重构或升级无关依赖。

## 提交前验证

先运行与改动直接相关的测试，再运行：

```powershell
pnpm verify
```

默认门禁不会调用 DeepSeek。真实模型测试会产生费用，不应在普通贡献或 CI 中运行。

## 提交与 Pull Request

提交标题应简短、聚焦结果，优先使用中文，例如 `修复文件解析失败后的重试状态`。一个提交只处理一个主题。Pull Request 应说明用户可见变化、实现范围、迁移或配置影响、准确执行过的验证命令，并关联对应 Issue 或规格；界面变化请附截图。未运行或有意跳过的检查必须明确说明。

提交贡献即表示你同意按 Apache License 2.0 提供该贡献。
