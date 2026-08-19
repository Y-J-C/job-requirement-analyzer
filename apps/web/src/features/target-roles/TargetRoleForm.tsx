"use client";

import { useState, type FormEvent } from "react";

import { recruitmentStageLabels, type CreateTargetRoleInput } from "./types";


type TargetRoleFormProps = {
  onCreate: (input: CreateTargetRoleInput) => Promise<void>;
};


export function TargetRoleForm({ onCreate }: TargetRoleFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const name = String(formData.get("name") ?? "").trim();
    const description = String(formData.get("description") ?? "").trim();

    if (!name) {
      setError("请输入目标岗位方向名称。");
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      await onCreate({
        name,
        recruitment_stage: String(
          formData.get("recruitment_stage"),
        ) as CreateTargetRoleInput["recruitment_stage"],
        description: description || null,
      });
      form.reset();
    } catch {
      setError("创建失败，请检查 API 是否已启动后重试。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="role-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="role-name">方向名称</label>
        <input
          id="role-name"
          name="name"
          type="text"
          maxLength={100}
          placeholder="例如：数据分析实习生"
          required
        />
      </div>

      <div className="field">
        <label htmlFor="recruitment-stage">招聘阶段</label>
        <select id="recruitment-stage" name="recruitment_stage" defaultValue="daily_internship">
          {Object.entries(recruitmentStageLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="field field-wide">
        <details className="form-optional">
          <summary>添加说明</summary>
          <label htmlFor="role-description">说明</label>
          <textarea
            id="role-description"
            name="description"
            maxLength={2000}
            rows={3}
          />
        </details>
      </div>

      <div className="form-actions field-wide">
        {error ? <p className="form-error" role="alert">{error}</p> : <span />}
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "创建中…" : "创建方向"}
        </button>
      </div>
    </form>
  );
}
