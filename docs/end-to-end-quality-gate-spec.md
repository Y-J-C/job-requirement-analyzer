# 第八阶段规格：自动化端到端测试与质量门禁

## 目标

为现有岗位分析闭环建立可重复、可清理、默认不产生模型费用的浏览器自动化测试。开发者应能通过一条根目录命令启动必要服务，验证 Web、API、Worker、PostgreSQL 和 MinIO 的真实协作，并在失败时获得截图、Trace 和明确日志。

本阶段服务于本地单用户版本的稳定性收口，不新增产品功能。成功意味着后续修改不再依赖人工浏览器冒烟来判断核心流程是否回归。

## 已确认决策与假设

- 使用 Playwright Test，版本与 Node.js 24、当前 Next.js 版本兼容并锁定在 `pnpm-lock.yaml`。
- `pnpm test:e2e` 默认不调用 DeepSeek；完整业务闭环通过手工要求 API 确认，保证确定性和零模型费用。
- 真实 DeepSeek 冒烟作为 `@deepseek` 独立用例，仅在显式设置 `RUN_DEEPSEEK_E2E=1` 且本地已配置密钥时运行。
- 测试使用本地 PostgreSQL 和 MinIO；不引入独立队列、测试专用后门接口或新的数据库结构。
- 测试数据使用唯一 `[E2E:<run-id>]` 前缀，并通过公开 API 删除岗位和目标方向。为补齐资源生命周期，本阶段增加目标方向删除接口；不改变数据库结构。即使断言失败，也执行兜底清理。
- 本阶段不配置 GitHub Actions；先建立本地质量门禁，接入远程 CI 需另行确认。

## 技术栈与命令

- 浏览器自动化：`@playwright/test`，Chromium。
- 服务编排：Playwright `webServer` 加 Windows PowerShell 启动脚本。
- 现有依赖：Next.js、FastAPI、PostgreSQL、MinIO 和持久化 Worker。

```powershell
pnpm test:e2e                 # 启动/检查基础设施并运行确定性 E2E
pnpm test:e2e:deepseek        # 显式运行真实 DeepSeek 冒烟
pnpm verify                   # lint、单元/集成测试、构建和默认 E2E
```

`test:e2e` 应检查 Docker 可用性、启动 PostgreSQL/MinIO、执行 Alembic 迁移，并由 Playwright 启停 Web、API 和 Worker。测试结束后可以保留 Docker 服务，但不得残留本次测试数据。

## 项目结构

```text
playwright.config.ts          Playwright URL、服务、超时和失败产物配置
e2e/
├─ fixtures/                  小型 Markdown 等固定输入
├─ tests/                     浏览器场景，文件名使用 *.spec.ts
└─ support/                   API 轮询、唯一命名和清理辅助函数
scripts/test-e2e.ps1          本地基础设施检查、迁移和测试入口
```

## 代码风格

测试使用语义化定位器，不依赖 CSS 层级或动态元素索引：

```ts
await page.getByRole("radio", { name: "上传文件" }).check();
await page.getByLabel("岗位文件").setInputFiles(markdownFixture);
await expect(page.getByText("解析完成")).toBeVisible();
```

辅助函数使用 `camelCase`，页面可见文案优先使用角色和标签定位。轮询必须有明确超时，不使用固定长时间 `waitForTimeout`。

## 测试策略

默认套件至少覆盖：

1. 创建目标方向，粘贴文本创建岗位，手工新增并编辑要求，确认后查看汇总与原文，再清理数据。
2. 上传 Markdown，观察 `extracting → draft`，核对解析文本，确认要求后进入汇总，并验证删除岗位后关联文件状态不可访问。
3. 拒绝不支持格式和超限文件，页面展示稳定中文错误且不创建岗位。
4. 模拟 API 不可用，页面显示可恢复错误，不泄露内部异常。

`@deepseek` 套件覆盖上传或文本录入、启动真实分析、等待持久化 Worker 完成、审核确认和汇总。若开关或密钥缺失，必须明确跳过而不是失败或静默调用。

失败时保留截图和 Trace；视频仅在失败时保留。默认只运行 Chromium，移动端和跨浏览器矩阵不属于本阶段。

## 边界

Always：使用公开用户/API 流程；唯一命名；在 `finally`/teardown 中清理；为异步状态设置有上限的轮询；失败产物不得包含密钥或完整敏感岗位内容；修改行为时同步维护 E2E。

Ask first：新增测试专用 API；修改数据库或删除策略；接入远程 CI；扩大到 Firefox/WebKit；让默认测试调用收费模型。

Never：提交 `.env`、密钥、Playwright 失败产物或真实用户文件；依赖已有人工数据；使用任意 `sleep` 掩盖竞态；为了稳定测试而降低生产校验。

## 验收标准

- 全新安装浏览器依赖后，`pnpm test:e2e` 可从仓库根目录一条命令运行。
- 默认套件不访问 DeepSeek，核心文本、文件、审核、汇总和删除流程通过。
- `RUN_DEEPSEEK_E2E=1` 时真实模型流程可单独运行，并保存模型错误的可诊断信息。
- 成功或失败后，PostgreSQL 和 MinIO 中均不残留本次 `[E2E:<run-id>]` 数据或对象。
- 失败自动生成截图和 Trace，成功运行不产生需提交的构建产物。
- `pnpm verify` 串联 lint、自动化测试和生产构建并以任一步骤失败为非零退出。
- README 记录首次安装 Playwright 浏览器和全部质量命令。

## 非目标

- 图片/OCR、登录、多用户、部署、监控和恶意文件扫描。
- 性能压测、视觉回归、无障碍专项审计和跨浏览器兼容矩阵。
- 使用真实招聘数据构造测试样本。

## 开放问题

无阻塞问题。远程 CI、跨浏览器矩阵和生产环境冒烟在本阶段完成后单独评估。
