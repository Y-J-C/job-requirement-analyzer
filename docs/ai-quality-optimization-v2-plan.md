# 第九阶段质量优化实施计划：原子化与规范名称 v2

## 概览

本计划实现已批准的 `docs/ai-quality-optimization-v2-spec.md`。先冻结首轮基线输入，再以
自动差异守卫建立数据集 v2，随后用测试驱动升级 `requirements-v3`。所有离线验证完成后
才请求一次真实评测授权；不修改模型、阈值、评分算法、数据库或公开 API。

## 架构决策

- 对 `ai-quality-v1.json` 记录固定 SHA-256，防止优化时无意改写首轮基线。
- v1/v2 使用逐字段差异测试；只有四组明确批准的可接受名称可以新增。
- 提示词规则保持单一系统提示，不引入动态 Golden 答案、模板引擎或第三方依赖。
- 提示词示例使用与数据集不同的技术和数值，只演示拆分规则，不泄露测试答案。
- 评测 CLI 默认数据集从 v1 切换为 v2，并由测试断言报告版本，避免复测错用旧口径。
- 真实复测只执行一次；无论成功或失败都生成独立 v2 基线文档并停止本轮。

## 任务列表

### 任务 1：冻结 v1 并建立数据集差异守卫

**说明：** 先为现有 v1 文件固定摘要，再编写失败测试，规定 v2 必须保持同一批样本、同一
期望要求和同一安全边界。

**验收条件：**

- [x] v1 文件 SHA-256 与首轮基线固定值一致。
- [x] 差异测试逐案例比较元数据、原文、期望项数量、证据、类型、明确程度和禁止项。
- [x] 测试拒绝删除名称、修改答案、增加案例或改变顺序。

**验证：**

- [x] 先运行测试并确认因 v2 不存在而失败。
- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_ai_evaluation.py -k "immutable or dataset_v2"`

**依赖：** 无。

**预计文件：**

- `apps/api/tests/test_ai_evaluation.py`
- `apps/api/tests/fixtures/ai-quality-v1.json`（只读）

**规模：** 小。

### 任务 2：建立仅扩充合法别名的数据集 v2

**说明：** 复制 v1 为版本化 v2，只加入规格批准的四组语义等价名称，不接受合并条件或
丢失例外语义的名称。

**验收条件：**

- [x] v2 版本号为 `ai-quality-v2`，仍为相同 20 条样本。
- [x] 只有四个指定期望项的名称集合扩大，其余字段逐值相同。
- [x] 禁止名称没有出现在任何 `accepted_normalized_names` 中。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_ai_evaluation.py -k "dataset or alias"`
- [x] `pnpm lint:api`

**依赖：** 任务 1。

**预计文件：**

- `apps/api/tests/fixtures/ai-quality-v2.json`
- `apps/api/tests/test_ai_evaluation.py`

**规模：** 中。

## 检查点一：标注治理

- [x] v1 摘要稳定且文件无修改。
- [x] v2 差异自动验证，不依赖人工浏览大段 JSON。
- [x] 质量阈值、评分算法和困难样本没有变化。

### 任务 3：用契约测试定义 requirements-v3

**说明：** 在修改提示词前增加失败测试，检查版本号及原子化、资格约束、职责排除、冲突
语义、空结果和注入防护规则，同时限制示例不得复用完整 Golden 文本。

**验收条件：**

- [x] 测试证明 `PROMPT_VERSION == "requirements-v3"`。
- [x] 系统提示包含规格中的六类规则和两个非 Golden 短示例。
- [x] 现有模型参数、JSON 模式、禁用思考和有限重试保持不变。

**验证：**

- [x] 先运行测试并确认仍为 v2 时失败。
- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_deepseek_analyzer.py`

**依赖：** 检查点一。

**预计文件：**

- `apps/api/tests/test_deepseek_analyzer.py`

**规模：** 小。

### 任务 4：实现最小提示词 v3

**说明：** 只修改提示词常量和版本，明确一项条件一个输出、可替代工具例外、资格约束拆分、
稳定规范名称、职责排除和冲突保留，不改请求协议或结果 Schema。

**验收条件：**

- [x] v3 契约测试通过，提示词没有拼入数据集或基线差异。
- [x] 空要求、无依据拒绝和提示注入边界继续有效。
- [x] 新提示词长度保持有界，不增加模型调用次数或重试次数。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_deepseek_analyzer.py apps/api/tests/test_ai_analysis.py`
- [x] `pnpm lint:api`

**依赖：** 任务 3。

**预计文件：**

- `apps/api/app/ai/deepseek.py`
- `apps/api/tests/test_deepseek_analyzer.py`

**规模：** 小。

## 检查点二：提示词契约

- [x] `requirements-v3` 只改变提示词语义，不改变 API、Schema 或持久化状态机。
- [x] MockTransport 全程离线，未访问 DeepSeek。
- [x] v1/v2 数据集差异测试继续通过。

### 任务 5：将真实评测入口切换到 v2

**说明：** 调整 CLI 默认固定数据集并增加报告版本回归测试，确保下一次授权运行使用 v2
标注和 v3 提示词。

**验收条件：**

- [x] 默认路径指向 `ai-quality-v2.json`，报告记录 `ai-quality-v2` 和 `requirements-v3`。
- [x] 无开关或无密钥仍在创建请求前退出，MockTransport 请求上限仍为 20 条。
- [x] 报告继续不包含请求头、完整响应或原文。

**验证：**

- [x] `.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_ai_evaluation_cli.py`
- [x] 移除开关后运行 `pnpm eval:ai:deepseek`，验证退出码为 2。

**依赖：** 任务 2、任务 4。

**预计文件：**

- `apps/api/app/ai/evaluate_deepseek.py`
- `apps/api/tests/test_ai_evaluation_cli.py`

**规模：** 小。

### 任务 6：完成离线回归和文档准备

**说明：** 运行质量命令与完整门禁，更新 README 的当前提示词/数据集说明，但不提前写入
未发生的 v2 指标。

**验收条件：**

- [x] `pnpm test:ai:quality` 全部离线通过。
- [x] `pnpm verify` 通过且真实 DeepSeek 用例仍默认跳过。
- [x] README 明确 v1 未达标、v2 优化待复测，未声称质量已经改善。

**验证：**

- [x] `pnpm test:ai:quality`
- [x] `pnpm verify`
- [x] `git diff --check`、密钥扫描和评测报告忽略检查。

**依赖：** 任务 5。

**预计文件：**

- `README.md`
- `docs/ai-quality-optimization-v2-plan.md`
- 相关测试与实现文件。

**规模：** 小。

## 检查点三：等待费用授权

- [x] 代码审查无阻塞问题。
- [x] 默认命令和测试零外部模型请求。
- [x] 向用户说明复测固定为 20 样本、单条最多一次输出重试，并再次请求授权。

### 任务 7：经授权运行一次 v2 真实复测

**说明：** 获得明确授权后运行一次 DeepSeek 评测，读取脱敏报告并与 v1 对照。不得根据
中间结果再次运行或在同轮修改提示词、别名、评分算法和阈值。

**验收条件：**

- [x] 报告使用 `deepseek-v4-flash + requirements-v3 + ai-quality-v2`。
- [x] 记录全部指标、Token、耗时、失败样本和相对 v1 的变化。
- [x] 达标则记录通过基线；未达标则记录失败基线和下一决策，不继续试跑。

**验证：**

- [x] `$env:RUN_DEEPSEEK_EVAL='1'; pnpm eval:ai:deepseek`
- [x] 报告原始文件保持 Git 忽略，版本库只新增脱敏 `docs/ai-quality-baseline-v2.md`。
- [x] 运行后再次执行密钥扫描和 `git diff --check`。

**依赖：** 检查点三、用户费用授权。

**预计文件：**

- `docs/ai-quality-baseline-v2.md`
- `README.md`
- `docs/mvp-acceptance-matrix.md`

**规模：** 小。

## 最终检查点

- [x] v1 不可变，v2 标注变化可解释且有自动守卫。
- [x] 提示词、数据集、模型和阈值版本均记录准确。
- [x] 真实复测只运行一次并如实报告。
- [x] 所有安全硬指标保持通过；语义指标是否达标有明确结论。
- [x] 工作区不包含密钥、本地报告、完整响应或真实用户数据。

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 为模型输出扩充别名造成过拟合 | 指标虚高 | 只允许四组已批准等价名称，差异测试锁定其他字段 |
| 提示词示例泄露测试答案 | 评测失真 | 使用不同技术和数值，测试禁止完整 Golden 文本进入提示词 |
| 原子化过度拆分可替代工具 | 误报增加 | 明确“独立技能拆分、同一条件中的替代工具保留” |
| 地点条件与岗位职责混淆 | 漏提或误提 | 只把明确限制候选人的地点/办公方式列为资格门槛 |
| v1 被无意覆盖 | 无法复现基线 | 固定文件摘要并保留独立 v2 文件 |
| 真实评测重复产生费用 | 费用与选择偏差 | 单次授权、单次运行，报告后停止 |

## 开放问题

无阻塞问题。任务 7 必须在离线实现和审查完成后再次获得用户明确授权。
