"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchJobPosting } from "@/features/job-postings/api";
import type { JobPosting } from "@/features/job-postings/types";

import {
  confirmRequirements,
  createRequirement,
  deleteRequirement,
  fetchAnalysisRun,
  fetchRequirements,
  startAnalysis,
  updateRequirement,
} from "./api";
import { RequirementForm } from "./RequirementForm";
import { RequirementList } from "./RequirementList";
import type { RequirementInput, RequirementItem } from "./types";


export function RequirementReviewDashboard({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<JobPosting | null>(null);
  const [items, setItems] = useState<RequirementItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [analysisMessage, setAnalysisMessage] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const statusLabels: Record<JobPosting["status"], string> = {
    draft: "未开始",
    queued: "等待分析",
    extracting: "正在提取",
    analyzing: "正在分析",
    review_required: "待确认",
    confirmed: "已确认",
    failed: "分析失败",
  };

  useEffect(() => {
    let isCurrent = true;
    Promise.all([fetchJobPosting(jobId), fetchRequirements(jobId)])
      .then(([loadedJob, listing]) => {
        if (isCurrent) {
          setJob({ ...loadedJob, status: listing.job_status });
          setItems(listing.items);
        }
      })
      .catch(() => {
        if (isCurrent) setError("岗位或审核数据加载失败，请返回后重试。");
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });
    return () => {
      isCurrent = false;
    };
  }, [jobId]);

  async function handleCreate(input: RequirementInput) {
    const created = await createRequirement(jobId, input);
    setItems((current) => [...current, created]);
    setJob((current) => current ? { ...current, status: "review_required" } : current);
  }

  async function handleUpdate(item: RequirementItem, input: RequirementInput) {
    const updated = await updateRequirement(item.id, input);
    setItems((current) => current.map((candidate) => (
      candidate.id === item.id ? updated : { ...candidate, user_confirmed: false }
    )));
    setJob((current) => current ? { ...current, status: "review_required" } : current);
  }

  async function handleDelete(item: RequirementItem) {
    if (!window.confirm(`确定删除门槛“${item.normalized_name}”吗？`)) return;
    setActionError(null);
    try {
      await deleteRequirement(item.id);
      setItems((current) => current
        .filter((candidate) => candidate.id !== item.id)
        .map((candidate) => ({ ...candidate, user_confirmed: false })));
      setJob((current) => current ? {
        ...current,
        status: items.length === 1 ? "draft" : "review_required",
      } : current);
    } catch {
      setActionError("门槛删除失败，请重试。");
    }
  }

  async function handleConfirm() {
    if (!window.confirm("确认整份岗位要求吗？确认后这些条目才可进入后续汇总。")) return;
    setActionError(null);
    try {
      const confirmedJob = await confirmRequirements(jobId);
      setJob(confirmedJob);
      setItems((current) => current.map((item) => ({ ...item, user_confirmed: true })));
    } catch {
      setActionError("岗位确认失败；请确认至少存在一条门槛后重试。");
    }
  }

  async function reloadReview() {
    const [loadedJob, listing] = await Promise.all([
      fetchJobPosting(jobId),
      fetchRequirements(jobId),
    ]);
    setJob({ ...loadedJob, status: listing.job_status });
    setItems(listing.items);
  }

  async function handleAnalyze() {
    setActionError(null);
    setAnalysisMessage("DeepSeek 正在提取并核对原文依据…");
    setIsAnalyzing(true);
    setJob((current) => current ? { ...current, status: "queued" } : current);
    try {
      const started = await startAnalysis(jobId);
      let current = started;
      for (let attempt = 0; attempt < 80; attempt += 1) {
        current = await fetchAnalysisRun(started.id);
        if (current.status === "succeeded") {
          await reloadReview();
          setAnalysisMessage("提取完成。请逐条核对后确认整份岗位。");
          return;
        }
        if (current.status === "failed") {
          setJob((value) => value ? { ...value, status: "failed" } : value);
          setActionError("AI 提取失败，未写入不完整结果。请稍后重试。");
          setAnalysisMessage(null);
          return;
        }
        await new Promise((resolve) => window.setTimeout(resolve, 750));
      }
      setActionError("AI 分析仍在运行，请稍后刷新页面查看结果。");
    } catch {
      setJob((value) => value ? { ...value, status: "failed" } : value);
      setActionError("无法启动 AI 分析。请确认服务端已配置 DeepSeek 密钥。");
      setAnalysisMessage(null);
    } finally {
      setIsAnalyzing(false);
    }
  }

  if (isLoading) return <main className="shell"><p aria-busy="true">正在加载审核数据…</p></main>;
  if (error || !job) return <main className="shell"><p role="alert">{error ?? "岗位不存在。"}</p></main>;

  return (
    <main className="shell review-page">
      <Link className="back-link" href={`/target-roles/${job.target_role_id}`}>← 返回岗位方向</Link>
      <header className="detail-header review-header">
        <div>
          <p className="eyebrow">AI 提取与人工审核</p>
          <h1>{job.company_name} · {job.job_title}</h1>
          <p>逐条保留依据，确认后再进入后续汇总。</p>
        </div>
        <span className={`status-badge status-${job.status}`}>
          {statusLabels[job.status]}
        </span>
      </header>

      {actionError ? <p className="form-error" role="alert">{actionError}</p> : null}
      {analysisMessage ? <p className="analysis-message" role="status">{analysisMessage}</p> : null}

      <div className="review-workspace">
        <aside className="source-panel" aria-labelledby="source-heading">
          <h2 id="source-heading">岗位原文</h2>
          <pre>{job.original_text}</pre>
        </aside>

        <div className="review-panel">
          <section className="analysis-action" aria-labelledby="ai-analysis-heading">
            <div>
              <h2 id="ai-analysis-heading">DeepSeek 原子要求提取</h2>
              <p>模型只生成待审核草稿；系统会校验每条依据确实存在于岗位原文。</p>
            </div>
            <button
              type="button"
              className="secondary-button"
              onClick={() => void handleAnalyze()}
              disabled={isAnalyzing || !["draft", "failed"].includes(job.status)}
            >
              {isAnalyzing ? "正在分析…" : "使用 DeepSeek 提取门槛"}
            </button>
          </section>

          <section aria-labelledby="add-requirement-heading">
            <h2 id="add-requirement-heading">新增原子要求</h2>
            <RequirementForm onSubmit={handleCreate} />
          </section>

          <section aria-labelledby="requirement-list-heading">
            <div className="list-heading">
              <h2 id="requirement-list-heading">门槛清单</h2>
              <span>{items.length} 条</span>
            </div>
            <RequirementList items={items} onUpdate={handleUpdate} onDelete={(item) => void handleDelete(item)} />
          </section>

          <div className="confirm-bar">
            <p>任何新增、编辑或删除都会使整份岗位重新进入待确认。</p>
            <button type="button" onClick={() => void handleConfirm()} disabled={items.length === 0 || job.status === "confirmed"}>
              {job.status === "confirmed" ? "整份岗位已确认" : "确认整份岗位"}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
