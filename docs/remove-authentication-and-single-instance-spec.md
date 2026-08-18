# 规格：移除登录与用户数据隔离

## 目标

项目改为无需账号的单实例应用，适合个人或小团队在可信本地环境部署。访问网页即可使用全部功能，所有访问者共享同一数据库中的方向、岗位、审核与汇总数据。

## 技术范围

- Web 移除 `AuthProvider`、`keycloak-js`、登录初始化、退出入口和 Bearer 请求封装；保留统一产品页头。
- API 移除 OIDC/JWT 验证、OpenAPI Bearer 安全声明及基于身份的资源过滤。
- 数据库新增 Alembic 迁移，删除 `target_roles.owner_subject` 及其索引；既有业务数据不得丢失。
- Docker Compose、环境示例和根脚本移除 Keycloak 服务、配置及真实登录测试。
- README 与工程指南改为说明单实例共享数据模型及公网暴露风险。
- 重新导出 OpenAPI，并生成前端 API 类型。

## 命令

- 迁移：`pnpm api:migrate`
- 契约：`pnpm api:contract:generate`
- 静态检查：`pnpm lint && pnpm typecheck`
- 单元测试：`pnpm test`
- 构建：`pnpm build`
- 完整验证：`pnpm verify`

## 项目结构与风格

- Web 变更位于 `apps/web/src/app/`、`apps/web/src/lib/`；删除废弃的 `src/auth/`。
- API 路由和服务位于 `apps/api/app/api/v1/`、`apps/api/app/services/`；删除废弃的 `app/auth/` 与 `services/ownership.py`。
- 新迁移位于 `apps/api/migrations/versions/`，不得编辑已应用迁移。
- TypeScript 使用两空格，Python 使用四空格；保持现有公开业务响应格式不变。

## 测试策略

- 先修改测试，证明 API 无 Authorization 头可访问且不同请求共享数据。
- 删除仅验证 Keycloak、JWT、IDOR 隔离的测试；保留并调整业务、OpenAPI、前端 API 客户端测试。
- 运行单元、集成、构建和 Playwright 主流程；真实 DeepSeek 测试仍按显式开关执行。

## 边界

- 必须：保留全部业务数据；保持业务 URL、请求体和响应体兼容；更新文档和契约。
- 需要额外确认：未来重新引入多用户、云端托管或公开互联网部署。
- 禁止：编辑旧迁移、提交密钥、把无认证 API 描述成可安全直接暴露公网。

## 验收标准

1. 打开 `http://localhost:3001` 不发生登录跳转，界面没有用户或退出控件。
2. API 请求不带 Bearer Token 可完成方向、岗位、审核和汇总全流程。
3. 数据模型、数据库、配置、依赖、Docker 和 OpenAPI 中不再包含用户归属或 OIDC/Keycloak 机制。
4. 既有方向和岗位在迁移后仍可读取。
5. `pnpm verify` 除明确需要真实 DeepSeek 的用例外全部通过。

## 开放问题

无。当前按单实例、可信网络部署处理；公网访问控制明确留给部署层。
