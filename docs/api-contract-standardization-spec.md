# API 契约标准化规格

## 目标

将 FastAPI 自动生成的 OpenAPI 3.1 文档确立为前后端唯一接口契约，消除前端重复手写响应类型和分散的错误处理。所有 HTTP 错误使用 RFC 9457 Problem Details；前端通过成熟的 `openapi-typescript` 与 `openapi-fetch` 消费契约。

## 技术选型

- 契约：FastAPI 原生 OpenAPI 3.1，不维护第二份 YAML。
- 错误：RFC 9457 `application/problem+json`，基础字段为 `type`、`title`、`status`、`detail`、`instance`。
- 业务错误码：使用 RFC 9457 扩展成员 `code`；请求校验错误使用 `errors` 数组和 JSON Pointer。
- TypeScript：`openapi-typescript` 生成类型，`openapi-fetch` 提供类型安全的 Fetch 客户端。

## 命令与结构

```powershell
pnpm api:contract:generate  # 从 FastAPI 应用导出契约并生成 TypeScript
pnpm test:api              # 验证 Problem Details 与 OpenAPI
pnpm test:web              # 验证共享客户端错误解析及现有界面
pnpm lint
pnpm build
```

- `apps/api/app/core/problems.py`：Problem Details 模型与异常处理器。
- `apps/api/scripts/export_openapi.py`：调用 `app.openapi()` 导出契约。
- `apps/web/src/generated/api-schema.ts`：自动生成，禁止手改。
- `apps/web/src/lib/api-client.ts`：共享客户端及标准错误类型。

## 兼容边界

- 保持现有 URL、HTTP 方法、成功状态码和成功响应结构。
- 上传错误码从旧的 `detail.code` 迁移为标准扩展字段 `code`，前端同步迁移。
- 本阶段不加入认证、不更改数据库、不新增业务功能。
- 生成结果必须可重复；密钥、上传内容和内部异常不得进入错误响应或契约。

## 测试策略与完成标准

- API 测试覆盖 HTTP 异常、请求校验异常和业务错误码，断言媒体类型与字段。
- 契约测试断言 OpenAPI 版本、Problem Details schema 和错误响应媒体类型。
- 前端测试覆盖标准错误解析；所有现有测试、Lint 和构建通过。
- 至少迁移现有四个 API 模块到共享的类型安全客户端，不保留重复 `fetch` 包装器。
