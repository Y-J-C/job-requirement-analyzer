import Link from "next/link";

import type { JobPosting } from "./types";


type JobPostingListProps = {
  jobs: JobPosting[];
  onDelete: (job: JobPosting) => void;
};


export function JobPostingList({ jobs, onDelete }: JobPostingListProps) {
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
                <p>{[job.city, job.status === "draft" ? "草稿" : job.status].filter(Boolean).join(" · ")}</p>
                <h3>{job.company_name} · {job.job_title}</h3>
              </div>
              <button className="danger-button" type="button" onClick={() => onDelete(job)}>
                删除岗位
              </button>
            </header>
            <Link className="review-link" href={`/jobs/${job.id}/review`}>审核门槛 →</Link>
            {job.source_url ? (
              <a className="source-link" href={job.source_url} target="_blank" rel="noreferrer">
                查看招聘来源
              </a>
            ) : null}
            <details>
              <summary>查看 JD 原文</summary>
              <pre>{job.original_text}</pre>
            </details>
          </article>
        </li>
      ))}
    </ul>
  );
}
