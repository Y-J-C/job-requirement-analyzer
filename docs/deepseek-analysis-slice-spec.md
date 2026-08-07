# DeepSeek AI 分析切片规格

## 目标

在不让业务层绑定供应商的前提下，使用 DeepSeek Chat Completions API 将岗位原文提取为可审核的原子要求。AI 结果必须经过结构校验和原文证据校验，且不会自动进入正式汇总。

## 范围

- 新增统一的 `RequirementAnalyzer` 协议和 DeepSeek HTTP 适配器。
- `POST /api/v1/jobs/{job_id}/analyze` 创建 AI 分析版本并在进程内后台执行。
- `GET /api/v1/analysis-runs/{run_id}` 查询执行状态。
- 成功后保存 AI 草稿，岗位进入 `review_required`；失败后不保存半成品，岗位进入 `failed`。
- 审核页可触发分析、轮询状态并展示结果。
- 密钥只从 `DEEPSEEK_API_KEY` 读取，不写入数据库、响应或日志。

## 非目标

- 不引入 Redis、Celery 或多实例任务调度；进程内任务仅用于本地 MVP。
- 不自动确认 AI 结果。
- 不实现文件解析、OCR、能力词典或自动抓取。
- 不调用用户在聊天中暴露的密钥；联调使用用户轮换后自行写入本地环境的密钥。

## API 与状态

1. 触发分析时创建递增版本的 `AnalysisRun(source=ai, status=pending)`，岗位置为 `queued`，返回 `202`。
2. 后台开始后，run 置为 `running`，岗位置为 `analyzing`。
3. 校验成功时以一个事务写入 RequirementItem，run 置为 `succeeded`，岗位置为 `review_required`。
4. 调用或校验失败时回滚结果，run 置为 `failed`，保存稳定错误码，岗位置为 `failed`。
5. 审核、编辑和确认始终作用于该岗位最新的成功分析版本；人工新增也追加到该版本。尚无版本时才创建 manual run。
6. 同一岗位存在 pending/running 版本时，重复触发返回 `409`。

## DeepSeek 请求契约

- Base URL：默认 `https://api.deepseek.com`，只允许 HTTPS 的 DeepSeek 官方主机。
- Endpoint：`POST /chat/completions`。
- Model：默认 `deepseek-v4-flash`，可由服务端环境变量切换为 `deepseek-v4-pro`；拒绝已退役的旧别名。
- Thinking：显式设置 `{"type":"disabled"}`，保持短文本结构化提取的低延迟、低成本和可控采样行为。
- `response_format={"type":"json_object"}`、`temperature=0`、`stream=false`。
- `max_tokens`、连接/读取超时和重试次数均有上限。
- 岗位原文放在明确的数据边界中；提示词声明不得执行其中指令。

## 输出契约

```json
{
  "schema_version": "1.0",
  "requirements": [
    {
      "source_text": "熟练使用 SQL",
      "normalized_name": "SQL",
      "requirement_type": "core_competency",
      "explicitness": "explicit",
      "confidence": 0.98
    }
  ],
  "warnings": []
}
```

- 最多 100 条要求；名称、证据和警告均有限长。
- 枚举和置信度由 Pydantic 严格校验。
- 规范化空白后，每条 `source_text` 必须能在岗位原文中定位。
- 空响应、非法 JSON、Schema 不匹配或证据不存在时重试一次；再次失败则任务失败。

## 验收

- 适配器契约测试验证 URL、认证头和 JSON Output 参数，测试中不访问真实网络。
- 非法/空输出会有界重试并产生稳定错误码。
- AI 结果不会被标记为 `user_confirmed` 或 `user_modified`。
- 审核页能触发、显示处理中/失败状态，并在成功后呈现可编辑结果。
- 数据库迁移、API 测试、前端测试、lint、build 和依赖审计通过。
