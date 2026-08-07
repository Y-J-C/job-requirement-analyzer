"use client";

import { useState, type FormEvent } from "react";

import {
  explicitnessLabels,
  requirementTypeLabels,
  type RequirementInput,
} from "./types";


type RequirementFormProps = {
  initialValue?: RequirementInput;
  mode?: "create" | "edit";
  onSubmit: (input: RequirementInput) => Promise<void>;
  onCancel?: () => void;
};


export function RequirementForm({
  initialValue,
  mode = "create",
  onSubmit,
  onCancel,
}: RequirementFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isEditing = mode === "edit";
  const labelPrefix = isEditing ? "编辑" : "";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const text = (name: string) => String(data.get(name) ?? "").trim();
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({
        normalized_name: text("normalized_name"),
        original_text: text("original_text"),
        requirement_type: text("requirement_type") as RequirementInput["requirement_type"],
        explicitness: text("explicitness") as RequirementInput["explicitness"],
      });
      if (!isEditing) form.reset();
    } catch {
      setError(isEditing ? "保存失败，请检查输入后重试。" : "新增失败，请检查输入后重试。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="requirement-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor={`${mode}-requirement-name`}>{labelPrefix}标准条件名称</label>
        <input
          id={`${mode}-requirement-name`}
          name="normalized_name"
          defaultValue={initialValue?.normalized_name}
          maxLength={200}
          required
        />
      </div>
      <div className="field">
        <label htmlFor={`${mode}-requirement-type`}>{labelPrefix}要求类型</label>
        <select
          id={`${mode}-requirement-type`}
          name="requirement_type"
          defaultValue={initialValue?.requirement_type ?? "core_competency"}
        >
          {Object.entries(requirementTypeLabels).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor={`${mode}-explicitness`}>{labelPrefix}明确程度</label>
        <select
          id={`${mode}-explicitness`}
          name="explicitness"
          defaultValue={initialValue?.explicitness ?? "explicit"}
        >
          {Object.entries(explicitnessLabels).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>
      <div className="field field-wide">
        <label htmlFor={`${mode}-original-text`}>{labelPrefix}原文依据</label>
        <textarea
          id={`${mode}-original-text`}
          name="original_text"
          defaultValue={initialValue?.original_text}
          rows={3}
          maxLength={2000}
          required
        />
      </div>
      <div className="form-actions field-wide">
        {error ? <p className="form-error" role="alert">{error}</p> : <span />}
        <div className="inline-actions">
          {isEditing ? <button type="button" className="secondary-button" onClick={onCancel}>取消编辑</button> : null}
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "正在保存…" : isEditing ? "保存修改" : "新增门槛"}
          </button>
        </div>
      </div>
    </form>
  );
}
