import Link from "next/link";

import type { JobPosting, SourceFile } from "./types";


type JobPostingListProps = {
  jobs: JobPosting[];
  sourceFiles: Record<string, SourceFile>;
  selectedJobIds: Set<string>;
  onSelectionChange: (jobId: string, selected: boolean) => void;
  onRetry: (job: JobPosting) => void;
  onDelete: (job: JobPosting) => void;
};

const statusLabels: Record<JobPosting["status"], string> = {
  draft: "草稿",
  queued: "等待分析",
  extracting: "正在提取文字",
  analyzing: "AI 正在分析",
  review_required: "待人工审核",
  confirmed: "已确认，可汇总",
  failed: "处理失败",
};

const parseErrorLabels: Record<string, string> = {
  encrypted_document: "文件已加密，无法解析。",
  no_extractable_text: "未检测到可解析文本，请换用更清晰的图片或文件。",
  pdf_page_limit_exceeded: "PDF 超过 50 页限制。",
  extracted_text_too_large: "提取文本超过 100,000 字限制。",
  storage_unavailable: "文件存储暂时不可用，可稍后重试。",
  document_parse_failed: "文件解析失败，请检查文件是否完整。",
  image_ocr_failed: "图片文字识别失败，请换用更清晰的图片后重试。",
};


export function JobPostingList({
  jobs,
  sourceFiles,
  selectedJobIds,
  onSelectionChange,
  onRetry,
  onDelete,
}: JobPostingListProps) {
  if (jobs.length === 0) {
    return <p className="list-state" role="status">暂无岗位</p>;
  }

  return (
    <ul className="job-list">
      {jobs.map((job) => {
        const canSelect = job.status === "confirmed" && job.active_analysis_run_id !== null;
        const displayName = `${job.company_name ?? "待补充公司"} · ${job.job_title ?? "待补充岗位"}`;
        return (
          <li key={job.id}>
            <article>
              <header className="job-heading">
                <label className="job-selection">
                  <input
                    type="checkbox"
                    checked={selectedJobIds.has(job.id)}
                    disabled={!canSelect}
                    onChange={(event) => onSelectionChange(job.id, event.currentTarget.checked)}
                  />
                  <span className="visually-hidden">选择 {displayName}</span>
                </label>
                <div className="job-title-block">
                  <p className="job-meta">
                    <span>{job.city ?? "城市待补充"}</span>
                    <span className={`status-label status-${job.status}`}>{statusLabels[job.status]}</span>
                  </p>
                  <h3>{displayName}</h3>
                  {!canSelect ? <span className="selection-note">人工确认后可参与综合分析</span> : null}
                </div>
                <button className="danger-button" type="button" onClick={() => onDelete(job)}>
                  删除岗位
                </button>
              </header>
              {job.status === "review_required" || job.status === "confirmed" ? (
                <Link className="review-link" href={`/jobs/${job.id}/review`}>审核指标与元数据 →</Link>
              ) : null}
              {job.source_url ? (
                <a className="source-link" href={job.source_url} target="_blank" rel="noreferrer">
                  查看招聘来源
                </a>
              ) : null}
              {job.status === "extracting" ? (
                <p className="parse-message" role="status">来源已保存，正在提取文字…</p>
              ) : null}
              {job.status === "queued" || job.status === "analyzing" ? (
                <p className="parse-message" role="status">文字已准备，正在生成待审核指标…</p>
              ) : null}
              {job.status === "failed" ? (
                <div className="retry-row">
                  <p className="form-error" role="alert">
                    {parseErrorLabels[sourceFiles[job.id]?.error_code ?? ""] ?? "处理失败，未保存半成品。"}
                  </p>
                  <button className="secondary-button" type="button" onClick={() => onRetry(job)}>
                    重试处理
                  </button>
                </div>
              ) : null}
              {job.original_text ? (
                <details>
                  <summary>查看岗位原文</summary>
                  <pre>{job.original_text}</pre>
                </details>
              ) : null}
            </article>
          </li>
        );
      })}
    </ul>
  );
}
