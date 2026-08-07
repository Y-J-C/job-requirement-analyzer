import type { RecruitmentStage } from "@/features/target-roles/types";


export type JobPostingStatus =
  | "draft"
  | "queued"
  | "extracting"
  | "analyzing"
  | "review_required"
  | "confirmed"
  | "failed";

export type JobPosting = {
  id: string;
  active_analysis_run_id: string | null;
  target_role_id: string;
  company_name: string;
  job_title: string;
  recruitment_stage: RecruitmentStage;
  city: string | null;
  source_url: string | null;
  original_text: string;
  status: JobPostingStatus;
  collected_at: string;
  created_at: string;
  updated_at: string;
};

export type JobPostingListResponse = {
  items: JobPosting[];
  total: number;
};

export type CreateJobPostingInput = {
  company_name: string;
  job_title: string;
  recruitment_stage: RecruitmentStage;
  city: string | null;
  source_url: string | null;
  original_text: string;
};
