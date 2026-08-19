"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { PageState } from "@/components/PageState";
import { createSelectedSummary } from "@/features/summary/api";
import { SelectedSummaryPanel } from "@/features/summary/SelectedSummaryPanel";
import type { TargetRoleSummary } from "@/features/summary/types";
import { fetchTargetRole } from "@/features/target-roles/api";
import { recruitmentStageLabels, type TargetRole } from "@/features/target-roles/types";

import {
  deleteJobPosting,
  fetchAllJobPostings,
  fetchJobPosting,
  fetchSourceFile,
  intakeJobPosting,
  retryJob,
} from "./api";
import { JobPostingForm } from "./JobPostingForm";
import { JobPostingList } from "./JobPostingList";
import { JobListControls } from "./JobListControls";
import {
  filterAndSortJobs,
  type JobSortOption,
  type JobStatusFilter,
} from "./jobPostingView";
import type { JobIntakeInput, JobPosting, SourceFile } from "./types";


export function JobPostingDashboard({ roleId }: { roleId: string }) {
  const [role, setRole] = useState<TargetRole | null>(null);
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [sourceFiles, setSourceFiles] = useState<Record<string, SourceFile>>({});
  const [selectedJobIds, setSelectedJobIds] = useState<Set<string>>(new Set());
  const [summary, setSummary] = useState<TargetRoleSummary | null>(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [jobQuery, setJobQuery] = useState("");
  const [jobStatus, setJobStatus] = useState<JobStatusFilter>("all");
  const [jobSort, setJobSort] = useState<JobSortOption>("newest");
  const activeJobIds = useMemo(
    () => jobs.filter((job) => ["extracting", "queued", "analyzing"].includes(job.status))
      .map((job) => job.id),
    [jobs],
  );
  const activeKey = activeJobIds.join(",");
  const sourceInfoKey = jobs
    .filter((job) => (job.status === "extracting" || (job.status === "failed" && !job.original_text))
      && !sourceFiles[job.id])
    .map((job) => job.id)
    .join(",");
  const selectableJobIds = jobs
    .filter((job) => job.status === "confirmed" && job.active_analysis_run_id !== null)
    .map((job) => job.id);
  const selectableKey = selectableJobIds.join(",");
  const selectableSet = new Set(selectableJobIds);
  const effectiveSelectedJobIds = new Set(
    Array.from(selectedJobIds).filter((jobId) => selectableSet.has(jobId)),
  );
  const visibleJobs = useMemo(
    () => filterAndSortJobs(jobs, { query: jobQuery, status: jobStatus, sort: jobSort }),
    [jobQuery, jobSort, jobStatus, jobs],
  );
  const visibleSelectableJobIds = visibleJobs
    .filter((job) => selectableSet.has(job.id))
    .map((job) => job.id);

  useEffect(() => {
    let isCurrent = true;
    Promise.all([fetchTargetRole(roleId), fetchAllJobPostings(roleId)])
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
    return () => { isCurrent = false; };
  }, [roleId]);

  useEffect(() => {
    if (!activeKey) return;
    const ids = activeKey.split(",");
    let isCurrent = true;
    async function refresh() {
      try {
        const refreshedJobs = await Promise.all(ids.map(fetchJobPosting));
        if (!isCurrent) return;
        const byId = new Map(refreshedJobs.map((job) => [job.id, job]));
        setJobs((current) => current.map((job) => byId.get(job.id) ?? job));
        const sourceResults = await Promise.all(refreshedJobs
          .filter((job) => job.status === "extracting" || (job.status === "failed" && !job.original_text))
          .map(async (job) => {
            try { return await fetchSourceFile(job.id); } catch { return null; }
          }));
        if (isCurrent) {
          setSourceFiles((current) => ({
            ...current,
            ...Object.fromEntries(sourceResults.filter((item): item is SourceFile => item !== null)
              .map((item) => [item.job_posting_id, item])),
          }));
        }
      } catch {
        // A later poll can recover from a temporary API failure.
      }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 1500);
    return () => { isCurrent = false; window.clearInterval(timer); };
  }, [activeKey]);

  useEffect(() => {
    if (!sourceInfoKey) return;
    let isCurrent = true;
    Promise.all(sourceInfoKey.split(",").map(async (jobId) => {
      try { return await fetchSourceFile(jobId); } catch { return null; }
    })).then((results) => {
      if (!isCurrent) return;
      setSourceFiles((current) => ({
        ...current,
        ...Object.fromEntries(results.filter((item): item is SourceFile => item !== null)
          .map((item) => [item.job_posting_id, item])),
      }));
    });
    return () => { isCurrent = false; };
  }, [sourceInfoKey]);

  async function handleIntake(input: JobIntakeInput) {
    const created = await intakeJobPosting(roleId, input);
    setJobs((current) => [created.job, ...current]);
    if (created.source_files[0]) {
      setSourceFiles((current) => ({ ...current, [created.job.id]: created.source_files[0] }));
    }
  }

  async function handleRetry(job: JobPosting) {
    setError(null);
    try {
      const retried = await retryJob(job.id);
      setJobs((current) => current.map((item) => item.id === job.id ? retried.job : item));
      if (retried.source_files[0]) {
        setSourceFiles((current) => ({ ...current, [job.id]: retried.source_files[0] }));
      }
    } catch {
      setError("岗位重试失败，请刷新状态后再试。");
    }
  }

  async function handleDelete(job: JobPosting) {
    const name = `${job.company_name ?? "待补充公司"} · ${job.job_title ?? "待补充岗位"}`;
    if (!window.confirm(`确定删除“${name}”及其原文吗？`)) return;
    try {
      await deleteJobPosting(job.id);
      setJobs((current) => current.filter((item) => item.id !== job.id));
      setSelectedJobIds((current) => {
        const next = new Set(current); next.delete(job.id); return next;
      });
      setSummary(null);
    } catch {
      setError("岗位删除失败，请重试。");
    }
  }

  function updateSelection(jobId: string, selected: boolean) {
    setSelectedJobIds((current) => {
      const allowed = new Set(selectableKey ? selectableKey.split(",") : []);
      const next = new Set(Array.from(current).filter((id) => allowed.has(id)));
      if (selected) next.add(jobId); else next.delete(jobId);
      return next;
    });
    setSummary(null);
  }

  async function handleSummarize() {
    setIsSummarizing(true);
    setError(null);
    try {
      setSummary(await createSelectedSummary(roleId, Array.from(effectiveSelectedJobIds)));
    } catch {
      setError("选中岗位综合分析失败，选择已保留，请重试。");
    } finally {
      setIsSummarizing(false);
    }
  }

  if (isLoading) return <PageState title="正在加载岗位方向" message="正在整理岗位记录与分析状态…" />;
  if (error && !role) return <PageState kind="error" title="岗位方向加载失败" message={error} />;
  if (!role) return <PageState kind="error" title="找不到目标方向" message="该方向可能已被删除，请返回工作台查看。" />;

  const allVisibleSelected = visibleSelectableJobIds.length > 0
    && visibleSelectableJobIds.every((jobId) => effectiveSelectedJobIds.has(jobId));
  return (
    <main className="shell role-detail">
      <nav className="page-nav" aria-label="页面导航">
        <Link className="back-link" href="/">返回方向</Link>
        <Link className="summary-link" href={`/target-roles/${roleId}/summary`}>查看汇总</Link>
      </nav>
      <header className="detail-header">
        <p className="eyebrow">{recruitmentStageLabels[role.recruitment_stage]}</p>
        <h1>{role.name}</h1>
        <p>{role.description || "一次提交岗位来源，自动提取指标；人工确认后再参与综合分析。"}</p>
      </header>

      {error ? <p className="form-error" role="alert">{error}</p> : null}
      <div className="role-workspace">
        <section className="intake-section" aria-labelledby="add-job-heading">
          <h2 id="add-job-heading">添加岗位来源</h2>
          <p className="section-intro">公司与岗位名可留空，系统会尝试从原文中识别。</p>
          <details className="intake-disclosure" open>
            <summary>录入岗位</summary>
            <JobPostingForm defaultStage={role.recruitment_stage} onIntake={handleIntake} />
          </details>
        </section>

        <section className="job-section" aria-labelledby="job-list-heading">
          <div className="list-heading">
            <div>
              <h2 id="job-list-heading">选择样本并分析</h2>
            </div>
            <span>{jobs.length} 个岗位</span>
          </div>
          <JobListControls
            query={jobQuery}
            status={jobStatus}
            sort={jobSort}
            resultCount={visibleJobs.length}
            totalCount={jobs.length}
            onQueryChange={setJobQuery}
            onStatusChange={setJobStatus}
            onSortChange={setJobSort}
            onReset={() => {
              setJobQuery("");
              setJobStatus("all");
              setJobSort("newest");
            }}
          />
          <div className="selection-toolbar">
            <label>
              <input
                type="checkbox"
                checked={allVisibleSelected}
                disabled={visibleSelectableJobIds.length === 0}
                onChange={(event) => {
                  const shouldSelect = event.currentTarget.checked;
                  setSelectedJobIds((current) => {
                    const next = new Set(current);
                    visibleSelectableJobIds.forEach((jobId) => {
                      if (shouldSelect) next.add(jobId);
                      else next.delete(jobId);
                    });
                    return next;
                  });
                  setSummary(null);
                }}
              />
              全选当前可汇总岗位
            </label>
            <span>已选 {effectiveSelectedJobIds.size} / {selectableJobIds.length}</span>
            <button
              type="button"
              onClick={() => void handleSummarize()}
              disabled={effectiveSelectedJobIds.size < 2 || isSummarizing}
            >
              {isSummarizing ? "正在综合…" : "综合分析选中岗位"}
            </button>
          </div>
          {visibleJobs.length === 0 && jobs.length > 0 ? (
            <div className="list-state" role="status">
              <h3>没有匹配的岗位</h3>
              <p>尝试更换关键词或状态，已勾选岗位不会被清除。</p>
              <button className="secondary-button" type="button" onClick={() => {
                setJobQuery("");
                setJobStatus("all");
                setJobSort("newest");
              }}>清除筛选</button>
            </div>
          ) : (
            <JobPostingList
              jobs={visibleJobs}
              sourceFiles={sourceFiles}
              selectedJobIds={effectiveSelectedJobIds}
              onSelectionChange={updateSelection}
              onRetry={(job) => void handleRetry(job)}
              onDelete={(job) => void handleDelete(job)}
            />
          )}
        </section>
      </div>
      {summary ? <SelectedSummaryPanel summary={summary} /> : null}
    </main>
  );
}
