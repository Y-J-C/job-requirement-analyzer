"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { fetchTargetRole } from "@/features/target-roles/api";
import { recruitmentStageLabels, type TargetRole } from "@/features/target-roles/types";

import { createJobPosting, deleteJobPosting, fetchJobPostings } from "./api";
import { JobPostingForm } from "./JobPostingForm";
import { JobPostingList } from "./JobPostingList";
import type { CreateJobPostingInput, JobPosting } from "./types";


export function JobPostingDashboard({ roleId }: { roleId: string }) {
  const [role, setRole] = useState<TargetRole | null>(null);
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;
    Promise.all([fetchTargetRole(roleId), fetchJobPostings(roleId)])
      .then(([targetRole, listing]) => {
        if (isCurrent) {
          setRole(targetRole);
          setJobs(listing.items);
        }
      })
      .catch(() => {
        if (isCurrent) setError("目标方向或岗位加载失败，请返回后重试。");
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });
    return () => {
      isCurrent = false;
    };
  }, [roleId]);

  async function handleCreate(input: CreateJobPostingInput) {
    const created = await createJobPosting(roleId, input);
    setJobs((current) => [created, ...current]);
  }

  async function handleDelete(job: JobPosting) {
    if (!window.confirm(`确定删除“${job.company_name} · ${job.job_title}”及其原文吗？`)) return;
    try {
      await deleteJobPosting(job.id);
      setJobs((current) => current.filter((item) => item.id !== job.id));
    } catch {
      setError("岗位删除失败，请重试。");
    }
  }

  if (isLoading) return <main className="shell"><p aria-busy="true">正在加载岗位方向…</p></main>;
  if (error || !role) return <main className="shell"><p role="alert">{error ?? "目标方向不存在。"}</p></main>;

  return (
    <main className="shell role-detail">
      <Link className="back-link" href="/">← 返回目标方向</Link>
      <header className="detail-header">
        <p className="eyebrow">{recruitmentStageLabels[role.recruitment_stage]}</p>
        <h1>{role.name}</h1>
        <p>{role.description || "在这里收集同类岗位，并保留每条 JD 的原始依据。"}</p>
        <Link className="summary-link" href={`/target-roles/${roleId}/summary`}>查看确认汇总 →</Link>
      </header>

      <section aria-labelledby="add-job-heading">
        <h2 id="add-job-heading">添加招聘岗位</h2>
        <JobPostingForm defaultStage={role.recruitment_stage} onCreate={handleCreate} />
      </section>

      <section className="job-section" aria-labelledby="job-list-heading">
        <div className="list-heading">
          <h2 id="job-list-heading">岗位样本</h2>
          <span>{jobs.length} 个</span>
        </div>
        <JobPostingList jobs={jobs} onDelete={(job) => void handleDelete(job)} />
      </section>
    </main>
  );
}
