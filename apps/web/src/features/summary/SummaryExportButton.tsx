"use client";

import { buildSummaryMarkdown, createSummaryFilename } from "./summaryExport";
import type { TargetRoleSummary } from "./types";


export function SummaryExportButton({
  summary,
  reportName,
}: {
  summary: TargetRoleSummary;
  reportName: string;
}) {
  function handleExport() {
    const now = new Date();
    const date = [now.getFullYear(), now.getMonth() + 1, now.getDate()]
      .map((part, index) => index === 0 ? String(part) : String(part).padStart(2, "0"))
      .join("-");
    const content = buildSummaryMarkdown(summary, reportName, date);
    const url = URL.createObjectURL(new Blob([content], { type: "text/markdown;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = createSummaryFilename(summary.target_role_name, reportName, date);
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <button className="secondary-button export-button" type="button" onClick={handleExport}>
      导出 Markdown
    </button>
  );
}
