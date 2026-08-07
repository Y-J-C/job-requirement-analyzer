# 岗位录入纵向切片规格

## 目标

让用户在一个已存在的目标岗位方向中录入、查看和删除具体招聘岗位，永久保留 JD 原文，形成不依赖 AI 的最小岗位数据闭环。

## 数据规则

`JobPosting`：

| 字段 | 规则 |
|---|---|
| `id` | UUID，服务端生成 |
| `target_role_id` | 必须引用存在的 TargetRole |
| `company_name` | 必填，去除首尾空格，1–100 字符 |
| `job_title` | 必填，去除首尾空格，1–150 字符 |
| `recruitment_stage` | 必填，与 TargetRole 共用枚举 |
| `city` | 可选，最多 100 字符 |
| `source_url` | 可选，仅允许 HTTP/HTTPS，最多 2048 字符；只保存，不发起请求 |
| `original_text` | 必填，去除首尾空格，1–100000 字符，不被分析结果覆盖 |
| `status` | 创建时固定为 `draft` |
| `collected_at` | 服务端生成的带时区时间 |
| `created_at` / `updated_at` | 服务端生成的带时区时间 |

TargetRole 删除后，其岗位最终采用级联删除；本阶段尚不开放 TargetRole 删除接口。

## API

```text
POST   /api/v1/target-roles/{role_id}/jobs
GET    /api/v1/target-roles/{role_id}/jobs?offset=0&limit=50
GET    /api/v1/jobs/{job_id}
DELETE /api/v1/jobs/{job_id}
```

- 父方向不存在时创建和列表均返回 `404`。
- 创建成功返回 `201`，删除成功返回 `204`。
- 输入非法返回 `422`，内部数据库异常不回显。
- TargetRole 列表响应增加真实 `job_count`。

## 前端行为

- 目标方向列表项链接到详情页，并显示真实岗位数。
- 详情页显示方向名称、招聘阶段、岗位列表和新增岗位表单。
- 表单包含公司、岗位名称、招聘阶段、城市、来源 URL、JD 原文。
- 保存期间禁用提交；成功后清空表单并刷新列表。
- 删除岗位必须先经过浏览器确认。
- 原文在页面中以纯文本显示，不使用 HTML 注入。

## 测试与验收

- [x] 迁移升级和降级成功，外键及级联规则存在。
- [x] 合法岗位可创建、列出和单项查询。
- [x] 不存在的父方向、空白必填项、非法 URL、超长原文被拒绝。
- [x] 删除岗位后列表与 `job_count` 同步变化。
- [x] 页面能录入岗位并展示原始 JD。
- [x] 删除前有确认，取消确认不会删除。
- [x] 前后端测试、lint、构建与依赖审计通过。
