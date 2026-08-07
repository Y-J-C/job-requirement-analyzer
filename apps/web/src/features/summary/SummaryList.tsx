import Link from "next/link";

import {
  explicitnessLabels,
  requirementTypeLabels,
} from "@/features/requirements/types";

import type { RequirementSummaryItem } from "./types";


const coverageFormatter = new Intl.NumberFormat("zh-CN", {
  style: "percent",
  maximumFractionDigits: 2,
});


export function SummaryList({ items }: { items: RequirementSummaryItem[] }) {
  return (
    <ol className="summary-list">
      {items.map((item) => (
        <li key={`${item.normalized_name}:${item.requirement_type}`}>
          <article>
            <header className="summary-item-heading">
              <div>
                <p>{requirementTypeLabels[item.requirement_type]}</p>
                <h3>{item.normalized_name}</h3>
              </div>
              <div className="coverage-value">
                <strong>{coverageFormatter.format(item.coverage_rate)}</strong>
                <span>{item.mentioning_job_count} / {item.confirmed_job_count} 个岗位</span>
              </div>
            </header>
            <p className="evidence-meta">
              共 {item.evidence_count} 条证据，其中 {item.explicit_evidence_count} 条为原文明示。
            </p>
            <details>
              <summary>查看 {item.evidence_count} 条原文证据</summary>
              <ul className="evidence-list">
                {item.evidence.map((evidence) => (
                  <li key={evidence.requirement_id}>
                    <div>
                      <Link href={`/jobs/${evidence.job_id}/review`}>
                        {evidence.company_name} · {evidence.job_title}
                      </Link>
                      <span>{explicitnessLabels[evidence.explicitness]}</span>
                    </div>
                    <blockquote>{evidence.original_text}</blockquote>
                  </li>
                ))}
              </ul>
            </details>
          </article>
        </li>
      ))}
    </ol>
  );
}
