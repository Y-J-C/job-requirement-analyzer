# ADR-0001：阶段一工程技术基线

- 状态：已接受
- 日期：2026-08-06

## 决策

采用 pnpm workspace 管理项目；前端使用 Next.js + TypeScript，后端使用 FastAPI + Python 3.12，数据持久化使用 PostgreSQL，本地基础设施使用 Docker Compose。

阶段一不引入 Redis、对象存储、AI SDK、身份认证和多租户。

## 原因

该组合与产品需求基线一致，前后端职责清晰，也能为后续文档解析、异步 AI 分析、审核和聚合查询保留扩展空间。将非必要基础设施延后，可以先验证工程链路和核心数据模型。

## 后果

- 开发环境需要 Node.js、pnpm、Python 3.12 和 Docker。
- 前后端使用 HTTP API 通信，共享契约后续放入 `packages/contracts`。
- 引入新的基础设施前需要单独记录决策并确认范围。
