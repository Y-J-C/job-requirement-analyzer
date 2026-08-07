# 目标岗位方向纵向切片规格

## 目标

在不接入 AI、文件上传、登录和多用户的前提下，让单用户能够创建并查看目标岗位方向，为后续 JobPosting 录入建立稳定的父资源。

## 已确认假设

- 当前仍是单用户本地版本，不创建 `User` 表，也不实现鉴权。
- 本切片实现 `TargetRole` 的创建、列表和单项查询；修改与删除放在后续切片。
- 招聘阶段使用稳定英文代码，中文仅在界面显示。
- 列表按创建时间倒序，API 使用带总数的分页响应。
- 不限制同名方向；是否需要唯一性约束待出现真实需求后决定。

## 数据契约

`TargetRole`：

| 字段 | 规则 |
|---|---|
| `id` | UUID，服务端生成 |
| `name` | 必填，去除首尾空格，1–100 字符 |
| `recruitment_stage` | 必填，固定枚举 |
| `description` | 可选，最多 2000 字符 |
| `created_at` | 服务端生成的带时区时间 |
| `updated_at` | 服务端生成的带时区时间 |

招聘阶段代码：

- `daily_internship`
- `summer_internship`
- `winter_internship`
- `autumn_recruitment`
- `spring_recruitment`
- `other`

## API

```text
POST /api/v1/target-roles
GET  /api/v1/target-roles?offset=0&limit=50
GET  /api/v1/target-roles/{role_id}
```

- 创建成功返回 `201`。
- 输入不合法返回 `422`，不把无效数据写入数据库。
- 不存在的 UUID 资源返回 `404`。
- 列表返回 `{ items, total }`。

## 前端行为

- 首页显示已有目标方向；空列表显示明确的空状态。
- 用户可填写名称、招聘阶段和可选说明。
- 提交期间禁用按钮，避免重复提交。
- 创建成功后清空表单并把新方向加入列表。
- API 失败时显示可理解的错误信息，不暴露内部异常。
- 所有表单控件具有可见标签并可用键盘操作。

## 代码结构

```text
apps/api/app/models/       SQLAlchemy 模型
apps/api/app/schemas/      API 输入输出 Schema
apps/api/app/services/     领域操作
apps/api/app/api/v1/       HTTP 路由
apps/web/src/features/     目标方向 UI 与 API 客户端
```

## 测试策略

- 后端 API 测试使用进程内 SQLite 测试数据库和 FastAPI 依赖覆盖，不写入开发数据库。
- Alembic 迁移在本地 PostgreSQL 上实际执行。
- 前端用 Vitest + Testing Library 验证加载、空状态、校验和创建流程。
- 完成后运行根目录 lint、test、build 和依赖审计。

## 安全边界

Always：

- 所有 HTTP 输入经 Pydantic 校验。
- 所有数据库操作通过 SQLAlchemy 参数化表达式完成。
- React 只以文本形式渲染用户输入。
- CORS 继续限制为配置中的单一 Web Origin。

Ask first：

- 增加用户体系或资源归属字段。
- 改变招聘阶段分类。
- 增加批量导入、公开分享或外部抓取。

Never：

- 把用户输入拼接进 SQL。
- 在错误响应中返回堆栈或数据库异常。
- 为当前单用户需求提前加入多租户抽象。

## 验收标准

- [x] 数据库迁移可升级和降级。
- [x] 合法目标方向可创建并持久化。
- [x] 空白名称、超长文本和非法招聘阶段被拒绝。
- [x] 目标方向可以分页列出并按创建时间倒序。
- [x] 单项查询对不存在资源返回 404。
- [x] 首页能加载、创建并展示目标方向。
- [x] 前后端测试、lint、构建和依赖审计通过。
