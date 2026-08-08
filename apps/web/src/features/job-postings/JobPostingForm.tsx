"use client";

import { useState, type FormEvent } from "react";

import { recruitmentStageLabels, type RecruitmentStage } from "@/features/target-roles/types";

import { ApiRequestError } from "./api";
import type { CreateJobPostingInput, UploadJobPostingInput } from "./types";


type JobPostingFormProps = {
  defaultStage: RecruitmentStage;
  onCreate: (input: CreateJobPostingInput) => Promise<void>;
  onUpload: (input: UploadJobPostingInput) => Promise<void>;
};

const uploadErrorLabels: Record<string, string> = {
  file_too_large: "文件超过 10 MiB 限制。",
  unsupported_file_type: "文件格式不支持，请选择 PDF、Markdown 或 DOCX。",
  file_signature_mismatch: "文件内容与扩展名不匹配，请重新选择正确文件。",
  invalid_file_structure: "文件结构无效或已损坏。",
};


export function JobPostingForm({ defaultStage, onCreate, onUpload }: JobPostingFormProps) {
  const [sourceMode, setSourceMode] = useState<"text" | "file">("text");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
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
      const common = {
        company_name: text("company_name"),
        job_title: text("job_title"),
        recruitment_stage: text("recruitment_stage") as RecruitmentStage,
        city: text("city") || null,
        source_url: text("source_url") || null,
      };
      if (sourceMode === "text") {
        await onCreate({ ...common, original_text: text("original_text") });
      } else {
        if (!selectedFile || selectedFile.size === 0) throw new Error("missing file");
        if (selectedFile.size > 10 * 1024 * 1024) throw new ApiRequestError("", "file_too_large");
        await onUpload({ ...common, file: selectedFile });
      }
      form.reset();
      setSourceMode("text");
      setSelectedFile(null);
    } catch (caught) {
      const code = caught instanceof ApiRequestError ? caught.code : null;
      setError(code ? uploadErrorLabels[code] ?? "文件上传失败，请重试。" : "岗位保存失败，请检查输入和 API 状态后重试。");
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
      <fieldset className="source-mode field-wide">
        <legend>JD 来源</legend>
        <label>
          <input
            type="radio"
            name="source_mode"
            value="text"
            checked={sourceMode === "text"}
            onChange={() => setSourceMode("text")}
          />
          粘贴文本
        </label>
        <label>
          <input
            type="radio"
            name="source_mode"
            value="file"
            checked={sourceMode === "file"}
            onChange={() => setSourceMode("file")}
          />
          上传文件
        </label>
      </fieldset>
      {sourceMode === "text" ? (
        <div className="field field-wide">
          <label htmlFor="original-text">JD 原文</label>
          <textarea id="original-text" name="original_text" rows={10} maxLength={100000} required />
        </div>
      ) : (
        <div className="field field-wide">
          <label htmlFor="job-file">岗位文件</label>
          <input
            id="job-file"
            name="file"
            type="file"
            accept=".pdf,.md,.markdown,.docx"
            required
            onChange={(event) => setSelectedFile(event.currentTarget.files?.[0] ?? null)}
          />
          <p className="field-hint">支持 PDF、Markdown、DOCX；最大 10 MiB</p>
        </div>
      )}
      <div className="form-actions field-wide">
        {error ? <p className="form-error" role="alert">{error}</p> : <span />}
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "正在提交…" : sourceMode === "file" ? "上传并提取" : "保存岗位"}
        </button>
      </div>
    </form>
  );
}
