"use client";

import { useState, type FormEvent } from "react";

import { recruitmentStageLabels, type RecruitmentStage } from "@/features/target-roles/types";

import { ApiRequestError } from "./api";
import type { JobIntakeInput, JobSourceType } from "./types";


type JobPostingFormProps = {
  defaultStage: RecruitmentStage;
  onIntake: (input: JobIntakeInput) => Promise<void>;
};

const uploadErrorLabels: Record<string, string> = {
  file_too_large: "单个文件超过 10 MiB 限制。",
  upload_total_too_large: "图片合计超过 50 MiB 限制。",
  image_count_limit_exceeded: "请选择 1～10 张图片。",
  image_pixel_limit_exceeded: "单张图片像素过高。",
  image_total_pixel_limit_exceeded: "图片合计像素过高。",
  unsupported_file_type: "来源格式不支持，请核对所选类型。",
  file_signature_mismatch: "文件内容与扩展名不匹配，请重新选择正确文件。",
  invalid_file_structure: "文件结构无效或已损坏。",
};


export function JobPostingForm({ defaultStage, onIntake }: JobPostingFormProps) {
  const [sourceMode, setSourceMode] = useState<JobSourceType>("text");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function changeMode(mode: JobSourceType) {
    setSourceMode(mode);
    setSelectedFiles([]);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const text = (name: string) => String(data.get(name) ?? "").trim();

    setError(null);
    setIsSubmitting(true);
    try {
      if (sourceMode !== "text" && selectedFiles.length === 0) {
        throw new Error("missing file");
      }
      if (sourceMode === "images") {
        if (selectedFiles.length > 10) {
          throw new ApiRequestError("", 422, "image_count_limit_exceeded");
        }
        if (selectedFiles.some((file) => file.size > 10 * 1024 * 1024)) {
          throw new ApiRequestError("", 422, "file_too_large");
        }
        if (selectedFiles.reduce((total, file) => total + file.size, 0) > 50 * 1024 * 1024) {
          throw new ApiRequestError("", 422, "upload_total_too_large");
        }
      }
      await onIntake({
        source_type: sourceMode,
        company_name: text("company_name") || null,
        job_title: text("job_title") || null,
        recruitment_stage: text("recruitment_stage") as RecruitmentStage,
        city: text("city") || null,
        source_url: text("source_url") || null,
        text: sourceMode === "text" ? text("original_text") : null,
        files: selectedFiles,
      });
      form.reset();
      setSourceMode("text");
      setSelectedFiles([]);
    } catch (caught) {
      const code = caught instanceof ApiRequestError ? caught.code : null;
      setError(
        code
          ? uploadErrorLabels[code] ?? "来源提交失败，请重试。"
          : "岗位提交失败，请检查输入和 API 状态后重试。",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="job-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="company-name">公司名称（可选提示）</label>
        <input id="company-name" name="company_name" maxLength={100} placeholder="可由系统识别" />
      </div>
      <div className="field">
        <label htmlFor="job-title">岗位名称（可选提示）</label>
        <input id="job-title" name="job_title" maxLength={150} placeholder="可由系统识别" />
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
        <input id="job-city" name="city" maxLength={100} placeholder="例如：上海" />
      </div>
      <div className="field field-wide">
        <label htmlFor="source-url">来源 URL（可选）</label>
        <input id="source-url" name="source_url" type="url" maxLength={2048} />
      </div>
      <fieldset className="source-mode field-wide">
        <legend>岗位来源（一次选择一种）</legend>
        {([
          ["text", "粘贴文本"],
          ["document", "上传文档"],
          ["images", "上传图片"],
        ] as const).map(([value, label]) => (
          <label key={value}>
            <input
              type="radio"
              name="source_mode"
              value={value}
              checked={sourceMode === value}
              onChange={() => changeMode(value)}
            />
            {label}
          </label>
        ))}
      </fieldset>
      {sourceMode === "text" ? (
        <div className="field field-wide">
          <label htmlFor="original-text">岗位原文</label>
          <textarea id="original-text" name="original_text" rows={9} maxLength={100000} placeholder="粘贴完整招聘信息，保留职责、要求和公司信息。" required />
        </div>
      ) : (
        <div className="field field-wide">
          <label htmlFor="job-files">{sourceMode === "images" ? "岗位图片" : "岗位文档"}</label>
          <input
            id="job-files"
            name="files"
            type="file"
            accept={sourceMode === "images" ? ".png,.jpg,.jpeg,.webp" : ".pdf,.md,.markdown,.docx"}
            multiple={sourceMode === "images"}
            required
            onChange={(event) => setSelectedFiles(Array.from(event.currentTarget.files ?? []))}
          />
          <p className="field-hint">
            {sourceMode === "images"
              ? "支持 PNG、JPEG、WebP；按选择顺序合并，最多 10 张"
              : "支持 PDF、Markdown、DOCX；最大 10 MiB"}
          </p>
          {selectedFiles.length > 1 ? (
            <ol className="selected-files" aria-label="图片处理顺序">
              {selectedFiles.map((file, index) => <li key={`${file.name}-${index}`}>{file.name}</li>)}
            </ol>
          ) : null}
        </div>
      )}
      <div className="form-actions field-wide">
        {error ? <p className="form-error" role="alert">{error}</p> : <span />}
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "正在提交…" : "提交并自动分析"}
        </button>
      </div>
    </form>
  );
}
