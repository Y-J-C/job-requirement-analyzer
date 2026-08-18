import { describe, expect, it } from "vitest";

import { buildSummaryMarkdown, createSummaryFilename } from "./summaryExport";
import type { TargetRoleSummary } from "./types";


const summary: TargetRoleSummary = {
  target_role_id: "role-1",
  target_role_name: "数据分析实习生",
  sample_job_count: 3,
  confirmed_job_count: 2,
  sample_size_notice: "样本量很小，仅供查看录入结果。",
  selected_job_ids: ["job-1", "job-2"],
  items: [{
    normalized_name: "SQL | 查询",
    requirement_type: "core_competency",
    mentioning_job_count: 2,
    confirmed_job_count: 2,
    coverage_rate: 1,
    evidence_count: 1,
    explicit_evidence_count: 1,
    evidence: [{
      requirement_id: "requirement-1",
      job_id: "job-1",
      company_name: "示例科技",
      job_title: "数据分析实习生",
      original_text: "熟练使用 SQL\n并能编写复杂查询",
      explicitness: "explicit",
    }],
  }],
};


describe("summary export", () => {
  it("builds a traceable Markdown report with metrics and evidence", () => {
    const markdown = buildSummaryMarkdown(summary, "选中岗位综合分析", "2026-08-09");

    expect(markdown).toContain("# 数据分析实习生 · 选中岗位综合分析");
    expect(markdown).toContain("- 全部样本：3 个");
    expect(markdown).toContain("| SQL \\| 查询 | 核心能力 | 100% | 2 / 2 |");
    expect(markdown).toContain("> 熟练使用 SQL  \n> 并能编写复杂查询");
    expect(markdown).toContain("示例科技 · 数据分析实习生");
  });

  it("creates a filesystem-safe Chinese filename", () => {
    expect(createSummaryFilename("数据/分析：实习生", "确认汇总", "2026-08-09"))
      .toBe("数据-分析-实习生-确认汇总-2026-08-09.md");
  });
});
