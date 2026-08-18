# MVP 验收证据矩阵

## 状态说明

- **已实现**：存在可运行代码及自动化测试证据。
- **部分实现**：主路径已存在，但质量基线、快捷操作或完整需求仍有缺口。
- **未实现**：当前代码没有对应用户能力。

## 产品闭环

| 验收项 | 状态 | 主要证据 |
|---|---|---|
| 创建并查看目标岗位方向 | 已实现 | `target_roles.py`、`TargetRoleDashboard.test.tsx`、E2E 文本主流程 |
| 在方向中添加多个岗位 | 已实现 | `jobs.py`、`test_job_postings.py` |
| 粘贴文本并永久保留原文 | 已实现 | `JobPostingForm.tsx`、`job_posting.py` |
| 上传 PDF、Markdown、DOCX | 已实现 | `source_file.py`、`test_document_parsers.py`、E2E 文件主流程 |
| 扫描版 PDF 按页 OCR | 已实现 | `pdf_ocr.py`、Worker 扫描版 PDF 测试、Playwright OCR 流程 |
| 上传 1～10 张图片并按序 OCR | 已实现 | `ocr.py`、`test_image_ocr.py`、E2E 图片自动录入 |
| 一次提交后自动分析且无重复运行 | 已实现 | `job_intake.py`、`test_job_intake.py`、E2E 图片自动录入 |
| 触发异步 AI 分析并查看状态 | 已实现 | `analysis.py`、`test_analysis_worker.py`、DeepSeek E2E 冒烟 |
| 将复合句拆成原子要求 | 部分实现 | `requirements-v3` 已复测；v4 增加元数据提取但尚未真实复测 |
| 保存分类、名称、明确程度、置信度和原文 | 已实现 | `contracts.py`、`requirement_item.py`、`test_ai_analysis.py` |
| 修改、新增、删除和确认要求 | 已实现 | `requirements.py`、`RequirementReviewDashboard.test.tsx` |
| 拆分、合并要求的专用快捷操作 | 未实现 | 当前可通过“编辑 + 新增/删除”完成，但没有专用交互 |
| 未确认数据不进入汇总 | 已实现 | `summary.py`、`test_summary.py` |
| 查看单岗位门槛和原文 | 已实现 | 岗位审核页及 `RequirementReviewDashboard.test.tsx` |
| 查看跨岗位去重汇总和覆盖率 | 已实现 | `summary.py`、`SummaryDashboard.test.tsx` |
| 选择或全选指定岗位进行综合分析 | 已实现 | `SelectedSummaryPanel.tsx`、`test_summary.py`、E2E 选中岗位汇总 |
| 从汇总回溯岗位原文 | 已实现 | 汇总证据链接及 E2E 文本主流程 |
| 删除岗位、分析结果和源文件 | 已实现 | `job_posting.py`、`test_source_file_upload.py` |
| 修改岗位元数据 | 已实现 | 岗位 PATCH、`JobMetadataForm.tsx`、`test_job_postings.py` |
| 修改目标方向 | 未实现 | 当前目标方向 API 没有对应 PATCH 路径 |

## 可靠性与安全

| 验收项 | 状态 | 主要证据 |
|---|---|---|
| AI 输出通过严格 Schema 校验 | 已实现 | `contracts.py`、`test_deepseek_analyzer.py` |
| 无原文依据的输出被拒绝 | 已实现 | `deepseek.py`、无依据重试测试 |
| 零条有效要求不会触发编造 | 已实现 | `requirements-v4`、空结果后端和前端测试 |
| 模型失败不写入半成品 | 已实现 | `test_ai_analysis.py` |
| 重新分析创建版本且不静默覆盖 | 已实现 | `durable-analysis-worker-spec.md`、Worker 测试 |
| 聚合按岗位去重且有自动化测试 | 已实现 | `test_summary.py` |
| 核心闭环有浏览器测试 | 已实现 | `e2e/tests/`、`pnpm test:e2e` |
| AI 语义质量达到确认阈值 | 部分实现 | v2 精确率 72.22%、召回率 76.47%，较 v1 提升但仍未达标 |
| 上传格式、大小、页数和文件头校验 | 已实现 | `validation.py`、`test_upload_validation.py` |
| 图片数量、字节、像素和损坏结构校验 | 已实现 | `validation.py`、`test_upload_validation.py` |
| 上传文件恶意软件扫描 | 已实现 | ClamAV 1.4 LTS、`malware.py`、EICAR 真实集成测试 |
| 单实例共享数据、无需登录 | 已实现 | 内置认证不属于本地开源部署边界 |

## 范围控制

系统当前未实现简历分析、个人能力匹配、学习建议、Offer 概率预测或自动投递。AI 适配器
只接收岗位文本，不具备执行岗位文本中指令或调用外部工具的权限。

## 当前结论

本地单实例岗位分析主闭环已经成立。第九阶段 `requirements-v3 + ai-quality-v2` 复测仍未
达到语义质量门槛；当前运行契约已升级为 `requirements-v4`，但尚未完成对应真实复测，
必须继续保留人工审核。下一产品功能缺口是目标方向编辑与要求拆分、合并快捷操作；
公网部署前还需在反向代理层增加访问控制，并补齐监控和费用限制。
