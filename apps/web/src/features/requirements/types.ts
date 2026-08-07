import type { JobPostingStatus } from "@/features/job-postings/types";


export type RequirementType =
  | "eligibility"
  | "core_competency"
  | "experience"
  | "preferred"
  | "uncertain";

export type RequirementExplicitness = "explicit" | "implicit" | "uncertain";

export type RequirementItem = {
  id: string;
  analysis_run_id: string;
  original_text: string;
  normalized_name: string;
  requirement_type: RequirementType;
  explicitness: RequirementExplicitness;
  confidence: number | null;
  user_confirmed: boolean;
  user_modified: boolean;
  created_at: string;
  updated_at: string;
};

export type RequirementInput = Pick<
  RequirementItem,
  "original_text" | "normalized_name" | "requirement_type" | "explicitness"
>;

export type RequirementListResponse = {
  items: RequirementItem[];
  total: number;
  job_status: JobPostingStatus;
};

export type AnalysisRunStatus = "pending" | "running" | "succeeded" | "failed" | "superseded";

export type AnalysisRun = {
  id: string;
  job_posting_id: string;
  version: number;
  status: AnalysisRunStatus;
  source: "manual" | "ai";
  model_provider: string | null;
  model_name: string | null;
  prompt_version: string | null;
  schema_version: string | null;
  error_code: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export const requirementTypeLabels: Record<RequirementType, string> = {
  eligibility: "资格门槛",
  core_competency: "核心能力",
  experience: "经历门槛",
  preferred: "加分条件",
  uncertain: "待确认",
};

export const explicitnessLabels: Record<RequirementExplicitness, string> = {
  explicit: "原文明示",
  implicit: "句式隐含",
  uncertain: "无法确定",
};
