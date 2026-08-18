import {
  explicitnessLabels,
  requirementTypeLabels,
} from "@/features/requirements/types";

import type { TargetRoleSummary } from "./types";


const coverageFormatter = new Intl.NumberFormat("zh-CN", {
  style: "percent",
  maximumFractionDigits: 2,
});


function escapeTableCell(value: string) {
  return value.replaceAll("|", "\\|").replaceAll("\n", " ");
}


function quoteMarkdown(value: string) {
  return value.split(/\r?\n/).map((line) => `> ${line}`).join("  \n");
}


export function createSummaryFilename(roleName: string, reportName: string, date: string) {
  const safeName = `${roleName}-${reportName}-${date}`
    .replace(/[<>:"/\\|?*：\u0000-\u001f]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  return `${safeName}.md`;
}


export function buildSummaryMarkdown(
  summary: TargetRoleSummary,
  reportName: string,
  date: string,
) {
  const lines = [
    `# ${summary.target_role_name} · ${reportName}`,
    "",
    `生成日期：${date}`,
    "",
    "## 样本口径",
    "",
    `- 全部样本：${summary.sample_job_count} 个`,
    `- 已确认岗位：${summary.confirmed_job_count} 个`,
    `- 说明：${summary.sample_size_notice}`,
    "",
    "## 要求覆盖率",
    "",
    "| 要求 | 类型 | 覆盖率 | 提及岗位 |",
    "| --- | --- | ---: | ---: |",
    ...summary.items.map((item) => (
      `| ${escapeTableCell(item.normalized_name)} | ${requirementTypeLabels[item.requirement_type]} | ${coverageFormatter.format(item.coverage_rate)} | ${item.mentioning_job_count} / ${item.confirmed_job_count} |`
    )),
  ];

  for (const item of summary.items) {
    lines.push("", `## ${item.normalized_name}`, "");
    lines.push(`覆盖 ${item.mentioning_job_count} / ${item.confirmed_job_count} 个岗位，共 ${item.evidence_count} 条证据。`);
    for (const evidence of item.evidence) {
      lines.push(
        "",
        `### ${evidence.company_name} · ${evidence.job_title}`,
        "",
        `明确程度：${explicitnessLabels[evidence.explicitness]}`,
        "",
        quoteMarkdown(evidence.original_text),
      );
    }
  }

  return `${lines.join("\n")}\n`;
}
