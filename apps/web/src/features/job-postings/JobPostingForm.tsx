"use client";

import { useState, type FormEvent } from "react";

import { recruitmentStageLabels, type RecruitmentStage } from "@/features/target-roles/types";

import type { CreateJobPostingInput } from "./types";


type JobPostingFormProps = {
  defaultStage: RecruitmentStage;
  onCreate: (input: CreateJobPostingInput) => Promise<void>;
};


export function JobPostingForm({ defaultStage, onCreate }: JobPostingFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const text = (name: string) => String(data.get(name) ?? "").trim();

    setError(null);
    setIsSubmitting(true);
    try {
      await onCreate({
        company_name: text("company_name"),
        job_title: text("job_title"),
        recruitment_stage: text("recruitment_stage") as RecruitmentStage,
        city: text("city") || null,
        source_url: text("source_url") || null,
        original_text: text("original_text"),
      });
      form.reset();
    } catch {
      setError("岗位保存失败，请检查输入和 API 状态后重试。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="job-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="company-name">公司名称</label>
        <input id="company-name" name="company_name" maxLength={100} required />
      </div>
      <div className="field">
        <label htmlFor="job-title">岗位名称</label>
        <input id="job-title" name="job_title" maxLength={150} required />
      </div>
      <div className="field">
        <label htmlFor="job-stage">招聘阶段</label>
        <select id="job-stage" name="recruitment_stage" defaultValue={defaultStage}>
          {Object.entries(recruitmentStageLabels).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="job-city">城市（可选）</label>
        <input id="job-city" name="city" maxLength={100} />
      </div>
      <div className="field field-wide">
        <label htmlFor="source-url">来源 URL（可选）</label>
        <input id="source-url" name="source_url" type="url" maxLength={2048} />
      </div>
      <div className="field field-wide">
        <label htmlFor="original-text">JD 原文</label>
        <textarea id="original-text" name="original_text" rows={10} maxLength={100000} required />
      </div>
      <div className="form-actions field-wide">
        {error ? <p className="form-error" role="alert">{error}</p> : <span />}
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "正在保存…" : "保存岗位"}
        </button>
      </div>
    </form>
  );
}

