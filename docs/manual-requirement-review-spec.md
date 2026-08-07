# 手工门槛审核纵向切片规格

## 目标

让单用户在不接入 AI 的情况下，为一个招聘岗位手工创建原子要求，编辑其标准名称、分类、明确程度和原文依据，删除误录条目，并确认整份岗位要求。该切片验证未来 AI 输出所需的数据模型与审核交互。

本阶段不实现 AI 提取、能力词典、拆分/合并快捷操作、审计历史和跨岗位汇总。

## 已确认假设

- `RequirementItem` 仍归属于 `AnalysisRun`，以保持与产品基线和未来 AI 版本一致。
- 首次为岗位新增要求时，服务端懒创建唯一的手工 `AnalysisRun`；前端不要求用户理解分析版本。
- 手工版本不记录模型供应商、模型名或置信度，条目默认 `user_modified=true`、`user_confirmed=false`。
- 新增或修改要求后岗位进入 `review_required`；确认整份岗位时所有现存条目一起确认，岗位进入 `confirmed`。
- 已确认岗位发生新增、编辑或删除时，全部现存条目重新变为未确认，岗位回到 `review_required`；最后一条被删除后岗位回到 `draft`。
- 确认空要求集合返回 `409`，避免产生没有任何依据的“已确认”岗位。

## 数据契约

`AnalysisRun`：

| 字段 | 规则 |
|---|---|
| `id` | UUID，服务端生成 |
| `job_posting_id` | 引用存在的 JobPosting，岗位删除时级联删除 |
| `version` | 同一岗位从 1 递增；本切片只创建一个手工版本 |
| `status` | 手工版本固定为 `succeeded` |
| `source` | 本切片固定为 `manual` |
| `created_at` / `updated_at` | 服务端生成的带时区时间 |

`RequirementItem`：

| 字段 | 规则 |
|---|---|
| `id` | UUID，服务端生成 |
| `analysis_run_id` | 引用手工 AnalysisRun，版本删除时级联删除 |
| `original_text` | 必填原文依据，去除首尾空格，1–2000 字符 |
| `normalized_name` | 必填标准条件名称，去除首尾空格，1–200 字符 |
| `requirement_type` | `eligibility`、`core_competency`、`experience`、`preferred`、`uncertain` |
| `explicitness` | `explicit`、`implicit`、`uncertain` |
| `confidence` | 手工条目为 `null` |
| `user_confirmed` | 新增/编辑后为 `false`，确认整份岗位后为 `true` |
| `user_modified` | 手工条目固定为 `true` |
| `created_at` / `updated_at` | 服务端生成的带时区时间 |

`structured_constraint`、`capability_id` 和完整修改审计历史延后实现。

## API

```text
GET    /api/v1/jobs/{job_id}/requirements?offset=0&limit=100
POST   /api/v1/jobs/{job_id}/requirements
PATCH  /api/v1/requirements/{requirement_id}
DELETE /api/v1/requirements/{requirement_id}
POST   /api/v1/jobs/{job_id}/confirm-requirements
```

- 列表返回 `{ items, total, job_status }`，尚未建立手工版本时返回空列表，不因读取而写数据库。
- 创建成功返回 `201`；更新成功返回 `200`；删除成功返回 `204`；确认成功返回更新后的岗位。
- 岗位或要求不存在返回 `404`；空集合确认返回 `409`；输入非法返回 `422`。
- 所有数据库查询使用 SQLAlchemy 参数化表达式，错误响应不暴露内部异常。

## 前端行为

- 每个岗位卡片提供“审核门槛”入口，进入独立岗位审核页。
- 审核页并排或上下展示岗位原文与门槛编辑区，原文始终以纯文本呈现。
- 表单支持新增；每条要求支持编辑、取消编辑和确认删除。
- 分类与明确程度使用带中文解释的稳定枚举选项，不允许自由输入代码。
- 页面显示未确认/已确认状态，并在确认整份岗位前进行浏览器确认。
- 加载、空状态、提交失败和资源不存在均有可理解的反馈；表单控件具备可见标签和键盘可达性。

## 命令与结构

```text
pnpm lint                         # 前后端 lint
pnpm test                         # 前后端测试
pnpm build                        # 前端生产构建与 Python 编译
pnpm test:api:integration         # PostgreSQL 就绪集成测试
pnpm audit --audit-level high     # Node 依赖审计
```

```text
apps/api/app/models/              AnalysisRun、RequirementItem 模型
apps/api/app/schemas/             审核输入输出契约
apps/api/app/services/            手工版本与确认状态转换
apps/api/app/api/v1/              HTTP 路由
apps/api/tests/                   API 行为测试
apps/web/src/features/requirements/  审核 UI、API 客户端和组件测试
```

代码沿用现有同步 SQLAlchemy 服务层、FastAPI Schema 边界和 React 容器/展示组件分离模式，不增加依赖。

## 测试策略

- 后端先用 API 测试覆盖创建、列表、编辑、删除、确认、重新打开审核、404/409/422 和分页边界。
- 迁移在 PostgreSQL 上验证升级、降级和 `alembic check`，SQLite 测试库验证业务行为。
- 前端用 Vitest + Testing Library 覆盖空状态、新增、编辑、取消删除和确认整份岗位。
- 端到端使用真实 API 验证“岗位 → 新增要求 → 编辑 → 确认 → 修改后回到待确认 → 删除”。

## 安全边界

Always：服务端校验所有输入；限制文本长度；ORM 参数化；React 文本转义；删除与整份确认前二次确认；CORS 保持单一配置来源。

Ask first：接入 AI、增加文件上传、引入用户/权限、修改 CORS、增加完整审计历史。

Never：将原文作为 HTML 渲染；从用户原文拼接 SQL；把手工条目伪装成 AI 结果或生成虚假置信度；确认空要求集合。

## 验收标准

- [x] 迁移可升级和降级，外键、唯一版本和级联规则存在。
- [x] 手工要求可创建、分页列出、编辑和删除。
- [x] 分类、明确程度、空白/超长字段和未知资源被正确校验。
- [x] 确认整份岗位后，岗位和全部要求进入确认状态。
- [x] 已确认数据发生变化后自动回到待确认；空集合不能确认。
- [x] 审核页可查看原文、新增、编辑、删除和确认，并覆盖加载/空/错误状态。
- [x] 前后端测试、lint、构建、迁移检查和依赖审计通过。

## 开放问题

无阻塞问题。拆分、合并、能力词典、AI 版本切换与确定性汇总分别放入后续切片。
