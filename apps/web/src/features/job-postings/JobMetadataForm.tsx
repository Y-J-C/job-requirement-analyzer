"use client";

import { useState, type FormEvent } from "react";

import type { JobMetadataUpdate, JobPosting } from "./types";


export function JobMetadataForm({
  job,
  onSave,
}: {
  job: JobPosting;
  onSave: (input: JobMetadataUpdate) => Promise<void>;
}) {
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const value = (name: string) => String(data.get(name) ?? "").trim() || null;
    setIsSaving(true);
    setError(null);
    try {
      await onSave({
        company_name: value("company_name"),
        job_title: value("job_title"),
        city: value("city"),
        source_url: value("source_url"),
      });
    } catch {
      setError("元数据保存失败，请检查内容后重试。");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form className="metadata-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="review-company">公司名称</label>
        <input id="review-company" name="company_name" defaultValue={job.company_name ?? ""} maxLength={100} required />
      </div>
      <div className="field">
        <label htmlFor="review-title">岗位名称</label>
        <input id="review-title" name="job_title" defaultValue={job.job_title ?? ""} maxLength={150} required />
      </div>
      <div className="field">
        <label htmlFor="review-city">城市（可选）</label>
        <input id="review-city" name="city" defaultValue={job.city ?? ""} maxLength={100} />
      </div>
      <div className="field">
        <label htmlFor="review-source-url">来源 URL（可选）</label>
        <input id="review-source-url" name="source_url" type="url" defaultValue={job.source_url ?? ""} maxLength={2048} />
      </div>
      {error ? <p className="form-error" role="alert">{error}</p> : <span />}
      <button className="secondary-button" type="submit" disabled={isSaving}>
        {isSaving ? "正在保存…" : "保存岗位信息"}
      </button>
    </form>
  );
}
