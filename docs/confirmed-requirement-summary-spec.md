# 已确认岗位确定性汇总规格

## 目标

让用户在一个目标岗位方向下查看已确认岗位的事实性汇总：哪些标准条件以哪种要求类型出现、覆盖了多少岗位、覆盖率是多少，并能回溯到每条岗位原文。汇总完全由数据库中的已确认数据确定，不调用 AI，也不推导“市场硬门槛”。

## 已确认假设与统计口径

- 只统计 `JobPosting.status=confirmed` 且 `RequirementItem.user_confirmed=true` 的条目。
- 聚合键为 `normalized_name` 的精确文本与 `requirement_type`；大小写或不同文本不做隐式合并。
- 同一岗位、同一聚合键出现多条要求时，`mentioning_job_count` 只计 1；证据条目全部保留。
- `coverage_rate = mentioning_job_count / confirmed_job_count`，四舍五入到 4 位小数；没有已确认岗位时为 `0`。
- 分类筛选只筛选汇总行，不改变已确认岗位分母。
- 页面同时显示全部样本岗位数与已确认岗位数，样本量提示按已确认岗位数生成。
- 汇总结果实时查询，不新增汇总表或缓存，避免审核数据变化后出现陈旧结果。

## API 契约

```text
GET /api/v1/target-roles/{role_id}/summary
GET /api/v1/target-roles/{role_id}/summary?requirement_type=core_competency
```

响应：

```json
{
  "target_role_id": "uuid",
  "target_role_name": "数据分析实习生",
  "sample_job_count": 3,
  "confirmed_job_count": 2,
  "sample_size_notice": "样本量很小，仅供查看录入结果。",
  "items": [
    {
      "normalized_name": "SQL",
      "requirement_type": "core_competency",
      "mentioning_job_count": 2,
      "confirmed_job_count": 2,
      "coverage_rate": 1.0,
      "evidence_count": 3,
      "explicit_evidence_count": 2,
      "evidence": [
        {
          "requirement_id": "uuid",
          "job_id": "uuid",
          "company_name": "示例科技",
          "job_title": "数据分析实习生",
          "original_text": "熟练使用 SQL",
          "explicitness": "explicit"
        }
      ]
    }
  ]
}
```

- 方向不存在返回 `404`；非法分类返回 `422`。
- 行按覆盖率降序、出现岗位数降序、标准名称和类型升序排列。
- 证据按公司、岗位、条目创建时间和 UUID 稳定排序。
- 只使用 SQLAlchemy 参数化表达式；响应不包含未确认要求、分析内部元数据或错误细节。

## 前端行为

- 目标方向详情页增加“查看确认汇总”入口。
- 汇总页展示全部样本数、已确认岗位数及样本量提示。
- 分类筛选提供“全部”和五种要求类型，筛选状态只存在于当前页面。
- 表格/列表显示标准名称、类型、覆盖岗位数、分母和百分比。
- 每行可展开证据，显示公司、岗位、明确程度与原文片段，并链接回该岗位审核页。
- 没有已确认岗位或筛选后无结果时显示明确空状态，不展示误导性百分比图表。
- 所有用户原文通过 React 文本节点渲染，不使用 HTML 注入。

## 命令、结构与代码风格

```text
pnpm lint
pnpm test
pnpm build
pnpm test:api:integration
pnpm audit --audit-level high
```

```text
apps/api/app/schemas/summary.py      汇总响应契约
apps/api/app/services/summary.py     确定性聚合查询与样本提示
apps/api/app/api/v1/summary.py       汇总路由
apps/api/tests/test_summary.py       去重、过滤、证据与边界测试
apps/web/src/features/summary/       汇总 API、类型、页面和组件测试
```

沿用现有 FastAPI 路由 → 服务 → SQLAlchemy 查询结构，以及 React 数据容器与展示组件分离模式；不增加第三方依赖，不修改数据库结构。

## 测试策略

- 后端先用失败测试证明：未确认数据被排除、同岗位重复要求按岗位去重、不同类型不合并、证据不丢失、分类筛选不改变分母、样本量提示边界正确。
- 前端组件测试覆盖加载、空状态、指标、分类筛选、覆盖率和证据回溯链接。
- 真实 PostgreSQL API 验收“两个确认岗位 + 一个未确认岗位 → 汇总 → 修改后自动排除”。
- 完成后运行完整 lint、test、build、依赖审计和迁移漂移检查。

## 安全边界

Always：校验 UUID 和枚举查询参数；ORM 参数化；React 自动转义；只返回当前单用户本地方向内的数据；限制 CORS 为既有配置。

Ask first：增加用户体系、导出/公开分享、缓存、阈值标签或修改聚合口径。

Never：统计未确认结果；按原文出现次数计算覆盖率；静默合并不同名称或类型；从百分比自动断言“硬门槛”；用 HTML 渲染原文。

## 验收标准

- [x] 汇总只包含已确认岗位和已确认要求。
- [x] 同岗位重复项按岗位去重，不同类型分别统计，全部证据保留。
- [x] 覆盖率分母、排序、分类筛选和样本量提示符合规格。
- [x] 未知方向和非法筛选返回正确错误。
- [x] 汇总页展示指标、空状态、分类筛选与可回溯证据。
- [x] 前后端测试、lint、构建、真实数据库验收和依赖审计通过。

## 开放问题

无阻塞问题。能力词典合并、图表、导出和缓存不属于本切片。
