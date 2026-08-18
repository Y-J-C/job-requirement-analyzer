# 岗位管理与结果导出规格

## Objective

让岗位样本增多后仍能快速定位、选择和比较，并将已确认汇总保存为可阅读、可追溯的 Markdown 报告。

## Scope

- 岗位方向页支持按公司、岗位名称和城市搜索。
- 支持“全部、处理中、待审核、已确认、失败”状态筛选。
- 支持按最新录入、最早录入、公司名称排序。
- 全选仅作用于当前可见且可汇总的岗位；筛选和排序不清除已有选择。
- 全部确认汇总与选中岗位综合分析均可导出 Markdown。
- 无匹配项时显示可恢复空状态，可一键清除筛选。

## Commands

- 测试：`pnpm --filter web test`
- 检查：`pnpm lint:web`
- 构建：`pnpm build:web`
- 浏览器回归：`pnpm test:e2e`

## Project Structure & Style

- 岗位筛选逻辑与控件位于 `apps/web/src/features/job-postings/`。
- 汇总序列化与导出控件位于 `apps/web/src/features/summary/`。
- 使用现有 TypeScript、React、Vitest 和编辑部式视觉系统，不增加依赖。
- 纯数据转换保持无副作用；下载文件名使用目标方向名称和当前日期。

## Testing Strategy

- 单元测试覆盖搜索、状态组合、排序和 Markdown 转换。
- 组件测试覆盖筛选结果、清除筛选、当前结果全选和下载入口。
- Playwright 验证真实页面的筛选、选择和下载。

## Boundaries

- 始终：保留隐藏项的选择；导出只包含当前汇总响应中的数据。
- 需另行规划：服务端分页、保存筛选条件、PDF/Word 导出。
- 不做：修改数据库、API 合约或已确认数据。

## Success Criteria

- 100 个以内的已加载岗位可即时筛选和排序。
- 无匹配结果时用户能明确恢复全部结果。
- Markdown 包含样本数、覆盖率、要求分类和逐条原文证据。
- 桌面与 390px 移动端均无横向溢出，键盘可操作。
