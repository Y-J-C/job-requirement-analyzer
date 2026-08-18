# 开源发布前收尾报告

日期：2026-08-18
结论：**本地质量门禁通过，仓库已达到可提交并触发首次 GitHub CI 的状态。** 尚未执行提交、推送、Release 或部署；云端 CI 只能在首次推送后确认。

## 完成交付

- 增加 Apache License 2.0 标准许可证，规范化内容与 Apache 官方原文 SHA-256 一致。
- 增加 `CONTRIBUTING.md` 和 `SECURITY.md`，明确本地开发、贡献流程、漏洞报告和无内置认证的部署边界。
- 更新入口 README、历史需求基线和 MVP 证据矩阵，区分 `requirements-v3` 的真实复测成绩与当前尚未真实复测的 `requirements-v4`。
- 增加 `.github/workflows/ci.yml`：Windows 执行契约、检查、单测和构建；Ubuntu 执行 PostgreSQL、MinIO、ClamAV 集成测试。
- 将受 GHSA-2v37-7h3g-55p8 影响的传递依赖 `nanoid@3.3.17` 覆盖至修复版本 `3.3.18`。

## 审查结论

对当前后端、迁移、上传解析、AI/Worker、前端契约和 E2E 差异进行了发布前审查。未发现尚未处理的阻塞级或高优先级代码问题。

- 已确认运行时代码、OpenAPI、Compose 和前端不存在已移除的 OIDC/Keycloak/资源归属机制。
- Alembic 迁移只有一个 Head；新增归属再移除归属的历史迁移保持可顺序升级与降级。
- 上传边界覆盖文件名、类型、文件头、字节、图片像素、PDF 页数、DOCX 解压限制、ClamAV 和失败清理。
- LLM 输出经过严格 Schema 与原文证据校验；默认测试和 CI 不读取密钥、不调用真实 DeepSeek。
- 选定岗位汇总验证岗位存在、属于当前方向、已确认且 ID 唯一。
- 工作树和 Git 历史的密钥特征扫描只发现配置占位引用，没有发现真实密钥或私钥文件。

## 验证结果

`pnpm verify` 完整通过：

- OpenAPI 契约生成与差异检查：通过。
- ESLint、Ruff、TypeScript：通过。
- Vitest：10 个文件、27 项通过。
- pytest 默认套件：146 项通过，6 项基础设施测试按标记跳过；随后单独启用并通过。
- PostgreSQL/MinIO 文件管线：1 项通过。
- ClamAV 干净文件与 EICAR：2 项通过。
- Next.js 生产构建与 Python 编译检查：通过。
- Playwright：11 项通过，1 项真实 DeepSeek 测试按设计跳过。

其他验证：

- pnpm 11.16 冻结锁文件检查：通过。
- GitHub Actions YAML 解析：通过；云端运行待首次推送。
- `pnpm audit`：没有已知漏洞。
- `pip-audit --local`：没有已知漏洞；本地可编辑项目本身不在 PyPI，按工具规则跳过。
- `git diff --check`：无空白错误；仅有 Windows `core.autocrlf` 的行尾提示。

## 已知限制

- `requirements-v4` 尚未执行真实 DeepSeek 质量复测；v3 的精确率 72.22%、召回率 76.47%，仍低于 90%/85% 门槛，必须保留人工审核。
- 尚无目标岗位方向编辑，以及要求拆分/合并的专用快捷操作。
- 应用没有内置认证、速率限制、生产监控或费用限额，只适合本机或可信网络；公网访问必须由反向代理补充 HTTPS 和访问控制。
- 云端 GitHub Actions 尚未实际运行，不能表述为已通过。

## Git 边界

本阶段没有执行 `commit`、`push`、创建 GitHub 仓库、Release 或部署。下一步建议先用一个聚焦的中文提交保存当前阶段成果，再推送到 GitHub 验证首次 CI；这两项都需要用户明确指令。

当前工作树包含此前多个阶段累计的 84 个已修改文件和 75 个未跟踪文件，尚无暂存内容。
提交前应把它们作为同一版本里程碑整体核对，不能只提交本阶段新增文档而遗漏其所描述的实现。
