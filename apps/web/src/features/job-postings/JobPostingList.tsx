import Link from "next/link";

import type { JobPosting, SourceFile } from "./types";


type JobPostingListProps = {
  jobs: JobPosting[];
  sourceFiles: Record<string, SourceFile>;
  onDelete: (job: JobPosting) => void;
};


const statusLabels: Record<JobPosting["status"], string> = {
  draft: "草稿",
  queued: "等待分析",
  extracting: "正在提取",
  analyzing: "正在分析",
  review_required: "待审核",
  confirmed: "已确认",
  failed: "处理失败",
};

const parseErrorLabels: Record<string, string> = {
  encrypted_document: "文件已加密，无法解析。",
  no_extractable_text: "未检测到可解析文本；扫描版 PDF 暂不支持。",
  pdf_page_limit_exceeded: "PDF 超过 50 页限制。",
  extracted_text_too_large: "提取文本超过 100,000 字限制。",
  storage_unavailable: "文件存储暂时不可用，系统将自动重试。",
  document_parse_failed: "文件解析失败，请检查文件是否完整。",
};


export function JobPostingList({ jobs, sourceFiles, onDelete }: JobPostingListProps) {
  if (jobs.length === 0) {
    return (
      <div className="list-state" role="status">
        <h3>还没有录入岗位</h3>
        <p>粘贴第一条真实 JD，开始建立这个方向的岗位样本。</p>
      </div>
    );
  }

  return (
    <ul className="job-list">
      {jobs.map((job) => (
        <li key={job.id}>
          <article>
            <header className="job-heading">
              <div>
                <p>{[job.city, statusLabels[job.status]].filter(Boolean).join(" · ")}</p>
                <h3>{job.company_name} · {job.job_title}</h3>
              </div>
              <button className="danger-button" type="button" onClick={() => onDelete(job)}>
                删除岗位
              </button>
            </header>
            {job.status !== "extracting" && job.original_text ? (
              <Link className="review-link" href={`/jobs/${job.id}/review`}>审核门槛 →</Link>
            ) : null}
            {job.source_url ? (
              <a className="source-link" href={job.source_url} target="_blank" rel="noreferrer">
                查看招聘来源
              </a>
            ) : null}
            {job.status === "extracting" ? (
              <p className="parse-message" role="status">文件已保存，正在提取文本…</p>
            ) : null}
            {job.status === "failed" && sourceFiles[job.id]?.error_code ? (
              <p className="form-error" role="alert">
                {parseErrorLabels[sourceFiles[job.id].error_code ?? ""] ?? "文件处理失败。"}
              </p>
            ) : null}
            {job.original_text ? (
              <details>
                <summary>查看 JD 原文</summary>
                <pre>{job.original_text}</pre>
              </details>
            ) : null}
          </article>
        </li>
      ))}
    </ul>
  );
}
