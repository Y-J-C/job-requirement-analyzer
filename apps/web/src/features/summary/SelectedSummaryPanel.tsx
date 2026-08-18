import { SummaryList } from "./SummaryList";
import { SummaryExportButton } from "./SummaryExportButton";
import type { TargetRoleSummary } from "./types";


export function SelectedSummaryPanel({ summary }: { summary: TargetRoleSummary }) {
  return (
    <section className="selected-summary" aria-labelledby="selected-summary-heading">
      <div className="list-heading">
        <h2 id="selected-summary-heading">选中岗位综合分析</h2>
        <div className="summary-heading-actions">
          <span>{summary.confirmed_job_count} 个岗位</span>
          <SummaryExportButton summary={summary} reportName="选中岗位综合分析" />
        </div>
      </div>
      <p className="sample-notice">{summary.sample_size_notice}</p>
      {summary.items.length > 0 ? (
        <SummaryList items={summary.items} />
      ) : (
        <div className="list-state" role="status">选中岗位尚无已确认指标。</div>
      )}
    </section>
  );
}
